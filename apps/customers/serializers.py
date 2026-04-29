"""
Serializers for Customer Display.
"""

from rest_framework import serializers
from .models import CustomerDisplayConfig, CustomerPromotion
from apps.orders.models import Order, OrderLine


class CustomerOrderLineSerializer(serializers.ModelSerializer):
    """Serializer for order lines on customer display."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    modifiers = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderLine
        fields = [
            'id', 'product_name', 'display_name', 'quantity',
            'unit_price', 'subtotal', 'modifiers',
        ]
    
    def get_display_name(self, obj):
        name = obj.product.name
        if obj.variant:
            name += f" ({obj.variant.display_name})"
        return name
    
    def get_modifiers(self, obj):
        return [m.modifier.name for m in obj.modifiers.all()]


class CustomerOrderSerializer(serializers.ModelSerializer):
    """Serializer for order on customer display (limited info)."""
    
    items = CustomerOrderLineSerializer(source='lines', many=True, read_only=True)
    items_count = serializers.IntegerField(source='lines.count', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'subtotal',
            'tax_amount', 'total_amount', 'items', 'items_count',
        ]


class CustomerDisplayConfigSerializer(serializers.ModelSerializer):
    """Serializer for customer display configuration."""
    
    terminal_name = serializers.CharField(source='terminal.name', read_only=True)
    
    class Meta:
        model = CustomerDisplayConfig
        fields = [
            'id', 'terminal', 'terminal_name', 'is_enabled',
            'show_logo', 'show_order_items', 'show_tax', 'show_promotions',
            'idle_message', 'idle_image', 'background_color',
            'primary_color', 'text_color',
        ]
        read_only_fields = ['id']


class CustomerPromotionSerializer(serializers.ModelSerializer):
    """Serializer for customer promotions."""
    
    class Meta:
        model = CustomerPromotion
        fields = [
            'id', 'title', 'display_type', 'content', 'image',
            'display_duration', 'display_order', 'is_active',
            'start_date', 'end_date',
        ]
        read_only_fields = ['id']


class CustomerDisplayStateSerializer(serializers.Serializer):
    """Serializer for current customer display state."""
    
    state = serializers.ChoiceField(
        choices=['idle', 'order', 'payment', 'complete']
    )
    order = CustomerOrderSerializer(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True)
    payment_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
