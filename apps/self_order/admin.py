from django.contrib import admin
from .models import (
    SelfOrderSession, SelfOrderCart, SelfOrderCartItem,
    SelfOrderQRCode
)


class SelfOrderCartItemInline(admin.TabularInline):
    model = SelfOrderCartItem
    extra = 0


class SelfOrderCartInline(admin.StackedInline):
    model = SelfOrderCart
    extra = 0


@admin.register(SelfOrderSession)
class SelfOrderSessionAdmin(admin.ModelAdmin):
    list_display = [
        'token_short', 'session_type', 'table', 'terminal',
        'customer_name', 'is_active', 'expires_at'
    ]
    list_filter = ['session_type', 'is_active']
    search_fields = ['token', 'customer_name', 'customer_phone']
    readonly_fields = ['token', 'expires_at']
    inlines = [SelfOrderCartInline]
    
    def token_short(self, obj):
        return f"{obj.token[:8]}..."
    token_short.short_description = 'Token'


@admin.register(SelfOrderQRCode)
class SelfOrderQRCodeAdmin(admin.ModelAdmin):
    list_display = ['table', 'code', 'is_active', 'scan_count', 'last_scanned_at']
    list_filter = ['is_active']
    search_fields = ['table__name', 'code']
    readonly_fields = ['code', 'scan_count', 'last_scanned_at']
