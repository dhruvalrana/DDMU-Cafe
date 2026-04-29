from django.contrib import admin
from .models import KitchenOrder, KitchenItemStatus, KitchenStation


class KitchenItemStatusInline(admin.TabularInline):
    model = KitchenItemStatus
    extra = 0
    readonly_fields = ['started_at', 'completed_at']


@admin.register(KitchenOrder)
class KitchenOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'status', 'priority', 'received_at',
        'started_at', 'completed_at', 'duration_minutes'
    ]
    list_filter = ['status', 'priority', 'received_at']
    search_fields = ['order__order_number']
    readonly_fields = ['received_at', 'duration_minutes', 'is_overdue']
    inlines = [KitchenItemStatusInline]


@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'display_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    filter_horizontal = ['categories']
