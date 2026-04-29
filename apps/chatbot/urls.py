"""
URL patterns for the POS Virtual Assistant chatbot.
"""

from django.urls import path
from .views import (
    ChatbotView,
    QuickActionView,
    ChatHistoryView,
    CategoryMenuView,
)

app_name = 'chatbot'

urlpatterns = [
    # Main chatbot endpoint
    path('', ChatbotView.as_view(), name='chat'),
    
    # Quick actions
    path('quick-action/', QuickActionView.as_view(), name='quick-action'),
    
    # Chat history
    path('history/<uuid:session_id>/', ChatHistoryView.as_view(), name='history'),
    
    # Category menu for chatbot
    path('menu/', CategoryMenuView.as_view(), name='menu'),
    path('menu/<uuid:category_id>/', CategoryMenuView.as_view(), name='menu-category'),
]
