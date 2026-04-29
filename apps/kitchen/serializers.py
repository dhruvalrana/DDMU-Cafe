"""
Serializers for Kitchen Display System.
"""

from rest_framework import serializers
from .models import KitchenOrder, KitchenItemStatus, KitchenStation
from apps.orders.models import Order, OrderLine


class KitchenOrderLineSerializer(serializers.ModelSerializer):
    """Serializer for order lines in kitchen display."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    modifiers = serializers.SerializerMethodField()
    item_status = serializers.CharField(source='kitchen_status.status', read_only=True, default='pending')
    
    class Meta:
        model = OrderLine
        fields = [
            'id', 'product', 'product_name', 'category_name', 'variant',
            'quantity', 'notes', 'is_prepared', 'modifiers', 'item_status',
        ]
    
    def get_modifiers(self, obj):
        return [
            {'name': m.modifier.name, 'price': str(m.price)}
            for m in obj.modifiers.all()
        ]


class KitchenOrderSerializer(serializers.ModelSerializer):
    """Serializer for kitchen orders."""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    table_name = serializers.CharField(source='order.table.display_name', read_only=True, allow_null=True)
    order_type = serializers.CharField(source='order.order_type', read_only=True)
    customer_name = serializers.CharField(source='order.customer_name', read_only=True)
    kitchen_notes = serializers.CharField(source='order.kitchen_notes', read_only=True)
    items = KitchenOrderLineSerializer(source='order.lines', many=True, read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    prepared_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = KitchenOrder
        fields = [
            'id', 'order', 'order_number', 'table_name', 'order_type',
            'customer_name', 'kitchen_notes', 'status', 'priority',
            'received_at', 'started_at', 'completed_at', 'target_time',
            'notes', 'items', 'duration_minutes', 'is_overdue',
            'items_count', 'prepared_count',
        ]
        read_only_fields = ['id', 'received_at']


class KitchenOrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for kitchen order list."""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    table_name = serializers.CharField(source='order.table.display_name', read_only=True, allow_null=True)
    order_type = serializers.CharField(source='order.order_type', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    prepared_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = KitchenOrder
        fields = [
            'id', 'order', 'order_number', 'table_name', 'order_type',
            'status', 'priority', 'received_at', 'duration_minutes',
            'is_overdue', 'items_count', 'prepared_count',
        ]


class KitchenItemStatusSerializer(serializers.ModelSerializer):
    """Serializer for individual item status."""
    
    product_name = serializers.CharField(source='order_line.product.name', read_only=True)
    quantity = serializers.DecimalField(source='order_line.quantity', max_digits=10, decimal_places=2, read_only=True)
    notes = serializers.CharField(source='order_line.notes', read_only=True)
    
    class Meta:
        model = KitchenItemStatus
        fields = [
            'id', 'kitchen_order', 'order_line', 'product_name',
            'quantity', 'notes', 'status', 'started_at', 'completed_at',
        ]
        read_only_fields = ['id', 'started_at', 'completed_at']


class KitchenStationSerializer(serializers.ModelSerializer):
    """Serializer for kitchen stations."""
    
    category_names = serializers.SerializerMethodField()
    
    class Meta:
        model = KitchenStation
        fields = [
            'id', 'name', 'code', 'description', 'display_order',
            'is_active', 'categories', 'category_names',
        ]
        read_only_fields = ['id']
    
    def get_category_names(self, obj):
        return [cat.name for cat in obj.categories.all()]


class BumpOrderSerializer(serializers.Serializer):
    """Serializer for bumping order to next status."""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class UpdateItemStatusSerializer(serializers.Serializer):
    """Serializer for updating individual item status."""
    
    status = serializers.ChoiceField(choices=['cooking', 'ready'])
