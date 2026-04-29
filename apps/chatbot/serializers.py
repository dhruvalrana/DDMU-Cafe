"""
Serializers for the POS Virtual Assistant chatbot.
"""

from rest_framework import serializers
from .models import ChatSession, ChatMessage, RecommendationLog


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'message_type', 'content', 'recommended_products', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions."""
    
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'group_size', 'dietary_preferences',
            'is_active', 'messages', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatInputSerializer(serializers.Serializer):
    """Serializer for chat input."""
    
    message = serializers.CharField(max_length=1000)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    group_size = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=100)
    dietary_preferences = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    category_id = serializers.UUIDField(required=False, allow_null=True)
    budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response."""
    
    session_id = serializers.UUIDField()
    message = serializers.CharField()
    recommendations = serializers.ListField(
        child=serializers.DictField()
    )
    follow_up_questions = serializers.ListField(
        child=serializers.CharField()
    )
    total_estimated_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )


class QuickActionSerializer(serializers.Serializer):
    """Serializer for quick action buttons."""
    
    action = serializers.ChoiceField(choices=[
        ('group_order', 'Order for Group'),
        ('combos', 'View Combos'),
        ('popular', 'Popular Items'),
        ('menu', 'Full Menu'),
        ('vegetarian', 'Vegetarian Options'),
        ('drinks', 'Drinks Menu'),
        ('desserts', 'Desserts'),
    ])
    group_size = serializers.IntegerField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
