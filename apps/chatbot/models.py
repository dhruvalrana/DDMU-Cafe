"""
Models for the POS Virtual Assistant chatbot.
Stores conversation history and user preferences.
"""

from django.db import models
from django.conf import settings
from apps.core.models import BaseModel


class ChatSession(BaseModel):
    """
    Stores chat sessions between users and the virtual assistant.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=100, blank=True)
    group_size = models.PositiveIntegerField(null=True, blank=True)
    dietary_preferences = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'pos_chat_sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Chat Session {self.id} - {self.created_at}"


class ChatMessage(BaseModel):
    """
    Individual messages in a chat session.
    """
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    recommended_products = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'pos_chat_messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."


class RecommendationLog(BaseModel):
    """
    Log of product recommendations made by the assistant.
    Used for analytics and improving recommendations.
    """
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='recommendations',
        null=True,
        blank=True
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    reason = models.CharField(max_length=255)
    was_ordered = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'pos_recommendation_logs'
        ordering = ['-created_at']
