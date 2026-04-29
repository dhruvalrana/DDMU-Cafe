from django.contrib import admin
from .models import POSTerminal, POSSession, CashMovement


class POSSessionInline(admin.TabularInline):
    model = POSSession
    extra = 0
    readonly_fields = ['opening_time', 'closing_time']
    fields = ['name', 'responsible_user', 'opening_time', 'closing_time', 'status', 'is_active']


@admin.register(POSTerminal)
class POSTerminalAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'floor', 'is_active', 'has_active_session']
    list_filter = ['is_active', 'floor']
    search_fields = ['name', 'code']
    inlines = [POSSessionInline]


class CashMovementInline(admin.TabularInline):
    model = CashMovement
    extra = 0
    readonly_fields = ['created_at']


@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'terminal', 'responsible_user', 'opening_time',
        'status', 'is_active', 'total_sales'
    ]
    list_filter = ['status', 'is_active', 'terminal', 'opening_time']
    search_fields = ['name', 'terminal__name', 'responsible_user__email']
    readonly_fields = [
        'name', 'expected_closing_balance', 'cash_difference', 'created_at'
    ]
    inlines = [CashMovementInline]


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ['session', 'movement_type', 'amount', 'reason', 'performed_by', 'created_at']
    list_filter = ['movement_type', 'session', 'created_at']
    readonly_fields = ['created_at']
