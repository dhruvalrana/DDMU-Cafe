"""
Serializers for Reports.
"""

from rest_framework import serializers
from decimal import Decimal


class DateRangeSerializer(serializers.Serializer):
    """Common date range parameters."""
    
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    session_id = serializers.UUIDField(required=False)
    terminal_id = serializers.UUIDField(required=False)
    user_id = serializers.IntegerField(required=False)


class DailySalesSerializer(serializers.Serializer):
    """Daily sales summary."""
    
    date = serializers.DateField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_tax = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_discount = serializers.DecimalField(max_digits=10, decimal_places=2)


class HourlySalesSerializer(serializers.Serializer):
    """Hourly sales breakdown."""
    
    hour = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    order_count = serializers.IntegerField()


class PaymentMethodBreakdownSerializer(serializers.Serializer):
    """Payment method breakdown."""
    
    payment_method = serializers.CharField()
    payment_method_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class ProductSalesSerializer(serializers.Serializer):
    """Product sales report."""
    
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    category_name = serializers.CharField()
    quantity_sold = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class CategorySalesSerializer(serializers.Serializer):
    """Category sales report."""
    
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    item_count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class StaffPerformanceSerializer(serializers.Serializer):
    """Staff performance report."""
    
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    order_count = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_hours_worked = serializers.DecimalField(max_digits=6, decimal_places=2)


class SessionSummarySerializer(serializers.Serializer):
    """POS session summary."""
    
    session_id = serializers.UUIDField()
    terminal_name = serializers.CharField()
    user_name = serializers.CharField()
    opened_at = serializers.DateTimeField()
    closed_at = serializers.DateTimeField(allow_null=True)
    opening_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    closing_balance = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    order_count = serializers.IntegerField()
    cash_in = serializers.DecimalField(max_digits=10, decimal_places=2)
    cash_out = serializers.DecimalField(max_digits=10, decimal_places=2)
    expected_cash = serializers.DecimalField(max_digits=10, decimal_places=2)
    difference = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)


class DashboardSerializer(serializers.Serializer):
    """Dashboard summary data."""
    
    # Today's summary
    today_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_orders = serializers.IntegerField()
    today_average_order = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Comparison with yesterday
    yesterday_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    sales_change_percent = serializers.DecimalField(max_digits=6, decimal_places=2)
    
    # Current state
    active_sessions = serializers.IntegerField()
    open_orders = serializers.IntegerField()
    tables_occupied = serializers.IntegerField()
    tables_total = serializers.IntegerField()
    
    # Top products today
    top_products = ProductSalesSerializer(many=True)
    
    # Hourly breakdown
    hourly_sales = HourlySalesSerializer(many=True)


class ExportFormatSerializer(serializers.Serializer):
    """Export format options."""
    
    format = serializers.ChoiceField(choices=['pdf', 'xlsx', 'csv'])
    report_type = serializers.ChoiceField(choices=[
        'daily_sales', 'product_sales', 'category_sales',
        'payment_methods', 'staff_performance', 'session_summary',
    ])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    session_id = serializers.UUIDField(required=False)
    terminal_id = serializers.UUIDField(required=False)
