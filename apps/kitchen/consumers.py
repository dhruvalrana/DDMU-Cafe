"""
WebSocket consumer for Kitchen Display System.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class KitchenDisplayConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for Kitchen Display System.
    Handles real-time updates for kitchen orders.
    """
    
    async def connect(self):
        self.terminal_id = self.scope['url_route']['kwargs']['terminal_id']
        self.room_group_name = f'kitchen_{self.terminal_id}'
        
        # Check authentication
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current orders on connect
        await self.send_current_orders()
    
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
            await self.send_current_orders()
        elif message_type == 'bump':
            await self.handle_bump(data)
    
    async def send_current_orders(self):
        """Send all current kitchen orders."""
        orders = await self.get_kitchen_orders()
        await self.send(text_data=json.dumps({
            'type': 'orders_list',
            'orders': orders,
        }))
    
    @database_sync_to_async
    def get_kitchen_orders(self):
        """Get all active kitchen orders for this terminal."""
        from .models import KitchenOrder
        from .serializers import KitchenOrderSerializer
        
        orders = KitchenOrder.objects.filter(
            order__session__terminal_id=self.terminal_id,
            is_deleted=False
        ).exclude(
            status__in=['completed', 'cancelled']
        ).select_related(
            'order', 'order__table'
        ).prefetch_related(
            'order__lines', 'order__lines__product'
        ).order_by('-priority', 'received_at')
        
        serializer = KitchenOrderSerializer(orders, many=True)
        return serializer.data
    
    @database_sync_to_async
    def handle_bump(self, data):
        """Handle bump action from WebSocket."""
        from .models import KitchenOrder
        
        order_id = data.get('kitchen_order_id')
        try:
            kitchen_order = KitchenOrder.objects.get(id=order_id)
            kitchen_order.bump()
        except KitchenOrder.DoesNotExist:
            pass
    
    # Event handlers for group messages
    
    async def new_order(self, event):
        """Handle new order event."""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_id': event.get('order_id'),
            'order_number': event.get('order_number'),
            'table': event.get('table'),
        }))
        
        # Also send refreshed order list
        await self.send_current_orders()
    
    async def order_status_change(self, event):
        """Handle order status change event."""
        await self.send(text_data=json.dumps({
            'type': 'order_status_change',
            'order_id': event.get('order_id'),
            'kitchen_order_id': event.get('kitchen_order_id'),
            'order_number': event.get('order_number'),
            'status': event.get('status'),
        }))
    
    async def order_cancelled(self, event):
        """Handle order cancelled event."""
        await self.send(text_data=json.dumps({
            'type': 'order_cancelled',
            'order_id': event.get('order_id'),
            'order_number': event.get('order_number'),
        }))
