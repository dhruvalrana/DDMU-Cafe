"""
WebSocket URL routing configuration.
"""

from django.urls import re_path
from apps.kitchen.consumers import KitchenDisplayConsumer
from apps.customers.consumers import CustomerDisplayConsumer
from apps.orders.consumers import OrderUpdatesConsumer

websocket_urlpatterns = [
    # Kitchen Display WebSocket
    re_path(r'ws/kitchen/(?P<terminal_id>[0-9a-f-]+)/$', KitchenDisplayConsumer.as_asgi()),
    
    # Customer Display WebSocket (by terminal ID)
    re_path(r'ws/customer/(?P<terminal_id>[0-9a-f-]+)/$', CustomerDisplayConsumer.as_asgi()),
    
    # General Order Updates WebSocket (for POS terminals - by session ID)
    re_path(r'ws/orders/(?P<session_id>[0-9a-f-]+)/$', OrderUpdatesConsumer.as_asgi()),
]
