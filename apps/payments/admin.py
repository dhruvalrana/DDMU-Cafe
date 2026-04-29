from django.contrib import admin
from .models import PaymentMethod, UPIConfiguration, CardConfiguration, Payment, PaymentRefund


class UPIConfigurationInline(admin.StackedInline):
    model = UPIConfiguration
    extra = 0


class CardConfigurationInline(admin.StackedInline):
    model = CardConfiguration
    extra = 0


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'method_type', 'is_active', 'is_default', 'display_order']
    list_filter = ['method_type', 'is_active', 'is_default']
    search_fields = ['name']
    ordering = ['display_order']
    inlines = [UPIConfigurationInline, CardConfigurationInline]


class PaymentRefundInline(admin.TabularInline):
    model = PaymentRefund
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'payment_method', 'amount', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__order_number', 'transaction_id', 'upi_transaction_id']
    readonly_fields = ['created_at', 'processed_at']
    inlines = [PaymentRefundInline]


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'amount', 'reason', 'created_at']
    list_filter = ['reason', 'created_at']
    readonly_fields = ['created_at']
