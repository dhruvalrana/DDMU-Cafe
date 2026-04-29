"""
WebSocket consumer for Customer Display.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CustomerDisplayConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for Customer Display.
    Receives real-time updates for current order.
    """
    
    async def connect(self):
        self.terminal_id = self.scope['url_route']['kwargs']['terminal_id']
        self.room_group_name = f'customer_{self.terminal_id}'
        
        # Customer display is public (no auth required)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current state
        await self.send_current_state()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages."""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
        elif message_type == 'refresh':
            await self.send_current_state()
    
    async def send_current_state(self):
        """Send current display state."""
        state = await self.get_display_state()
        await self.send(text_data=json.dumps({
            'type': 'state',
            **state
        }))
    
    @database_sync_to_async
    def get_display_state(self):
        """Get current display state for terminal."""
        from apps.terminals.models import POSSession
        from apps.orders.models import Order
        from .models import CustomerDisplayConfig
        from .serializers import CustomerOrderSerializer
        
        # Get active session
        try:
            session = POSSession.objects.get(
                terminal_id=self.terminal_id,
                is_active=True,
                status='open'
            )
        except POSSession.DoesNotExist:
            return {'state': 'idle', 'message': 'Terminal not active'}
        
        # Get current order
        current_order = Order.objects.filter(
            session=session,
            status__in=['draft', 'sent_to_kitchen', 'preparing', 'ready']
        ).order_by('-created_at').first()
        
        if current_order:
            return {
                'state': 'order' if current_order.status != 'ready' else 'complete',
                'order': CustomerOrderSerializer(current_order).data
            }
        
        # Idle state
        try:
            config = CustomerDisplayConfig.objects.get(terminal_id=self.terminal_id)
            return {'state': 'idle', 'message': config.idle_message}
        except CustomerDisplayConfig.DoesNotExist:
            return {'state': 'idle', 'message': 'Welcome!'}
    
    # Event handlers
    
    async def order_update(self, event):
        """Handle order update."""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'action': event.get('action'),
            'order': event.get('order'),
        }))
    
    async def line_added(self, event):
        """Handle line added to order."""
        await self.send(text_data=json.dumps({
            'type': 'line_added',
            'item': event.get('item'),
        }))
        # Refresh full state
        await self.send_current_state()
    
    async def payment_started(self, event):
        """Handle payment started."""
        await self.send(text_data=json.dumps({
            'type': 'payment_started',
            'total': event.get('total'),
        }))
    
    async def payment_complete(self, event):
        """Handle payment completed."""
        await self.send(text_data=json.dumps({
            'type': 'payment_complete',
            'message': event.get('message', 'Thank you!'),
        }))
    
    async def display_message(self, event):
        """Handle custom display message."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event.get('message'),
            'duration': event.get('duration', 5000),
        }))
