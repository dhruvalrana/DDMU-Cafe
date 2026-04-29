from django.contrib import admin
from .models import Order, OrderLine, OrderLineModifier, OrderDiscount


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ['line_total', 'tax_amount', 'created_at']


class OrderDiscountInline(admin.TabularInline):
    model = OrderDiscount
    extra = 0
    readonly_fields = ['applied_amount', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'table', 'status', 'order_type',
        'total_amount', 'created_by', 'created_at'
    ]
    list_filter = ['status', 'order_type', 'session', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_phone']
    readonly_fields = [
        'order_number', 'subtotal', 'tax_amount', 'total_amount',
        'sent_to_kitchen_at', 'ready_at', 'served_at', 'paid_at',
        'cancelled_at', 'created_at', 'updated_at',
    ]
    inlines = [OrderLineInline, OrderDiscountInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'session', 'table', 'order_type', 'status')
        }),
        ('Customer', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'guests_count')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'discount_percent', 'tip_amount', 'total_amount')
        }),
        ('Notes', {
            'fields': ('notes', 'kitchen_notes')
        }),
        ('Tracking', {
            'fields': ('created_by', 'served_by', 'sent_to_kitchen_at', 'ready_at', 'served_at', 'paid_at', 'cancelled_at')
        }),
    )


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'unit_price', 'line_total', 'is_prepared']
    list_filter = ['is_sent_to_kitchen', 'is_prepared', 'order__status']
    search_fields = ['order__order_number', 'product__name']
    readonly_fields = ['line_total', 'tax_amount', 'created_at']
