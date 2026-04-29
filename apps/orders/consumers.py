"""
WebSocket consumer for order updates.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class OrderUpdatesConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time order updates.
    Used by POS terminals to receive order status changes.
    """
    
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'orders_{self.session_id}'
        
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
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def order_update(self, event):
        """Send order update to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'action': event.get('action'),
            'order_id': event.get('order_id'),
            'order_number': event.get('order_number'),
            'status': event.get('status'),
            'table': event.get('table'),
        }))
    
    async def order_paid(self, event):
        """Send order paid notification."""
        await self.send(text_data=json.dumps({
            'type': 'order_paid',
            'order_id': event.get('order_id'),
            'order_number': event.get('order_number'),
            'amount': event.get('amount'),
        }))
    
    async def table_status(self, event):
        """Send table status update."""
        await self.send(text_data=json.dumps({
            'type': 'table_status',
            'table_id': event.get('table_id'),
            'is_occupied': event.get('is_occupied'),
            'order_id': event.get('order_id'),
        }))
