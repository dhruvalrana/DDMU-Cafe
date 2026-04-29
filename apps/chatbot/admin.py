"""
Admin configuration for the chatbot app.
"""

from django.contrib import admin
from .models import ChatSession, ChatMessage, RecommendationLog


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'group_size', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'created_at']
    search_fields = ['content']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'product', 'reason', 'was_ordered', 'created_at']
    list_filter = ['was_ordered', 'created_at']
    search_fields = ['product__name', 'reason']
    readonly_fields = ['created_at', 'updated_at']
