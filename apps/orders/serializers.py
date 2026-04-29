"""
Serializers for order management.
"""

from rest_framework import serializers
from decimal import Decimal
from .models import Order, OrderLine, OrderLineModifier, OrderDiscount
from apps.products.serializers import ProductListSerializer, ProductVariantSerializer


class OrderLineModifierSerializer(serializers.ModelSerializer):
    """Serializer for order line modifiers."""
    
    modifier_name = serializers.CharField(source='modifier.name', read_only=True)
    
    class Meta:
        model = OrderLineModifier
        fields = ['id', 'modifier', 'modifier_name', 'price']
        read_only_fields = ['id']


class OrderLineSerializer(serializers.ModelSerializer):
    """Serializer for order lines."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.variant_name', read_only=True, allow_null=True)
    modifiers = OrderLineModifierSerializer(many=True, read_only=True)
    
    class Meta:
        model = OrderLine
        fields = [
            'id', 'product', 'product_name', 'variant', 'variant_name',
            'quantity', 'unit_price', 'tax_rate', 'line_total', 'tax_amount',
            'discount_amount', 'notes', 'is_sent_to_kitchen', 'is_prepared',
            'modifiers', 'created_at',
        ]
        read_only_fields = ['id', 'line_total', 'tax_amount', 'created_at']


class OrderLineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order lines."""
    
    modifier_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = OrderLine
        fields = [
            'product', 'variant', 'quantity', 'notes', 'modifier_ids',
        ]
    
    def validate(self, attrs):
        product = attrs.get('product')
        variant = attrs.get('variant')
        
        if not product.is_active:
            raise serializers.ValidationError({
                'product': 'This product is not available.'
            })
        
        if variant and variant.product != product:
            raise serializers.ValidationError({
                'variant': 'Variant does not belong to this product.'
            })
        
        return attrs
    
    def create(self, validated_data):
        modifier_ids = validated_data.pop('modifier_ids', [])
        product = validated_data['product']
        variant = validated_data.get('variant')
        
        # Set pricing from product/variant
        if variant:
            validated_data['unit_price'] = variant.full_price
        else:
            validated_data['unit_price'] = product.price
        
        validated_data['tax_rate'] = product.tax_rate
        
        order_line = OrderLine.objects.create(**validated_data)
        
        # Add modifiers
        if modifier_ids:
            from apps.products.models import ProductModifier
            for modifier_id in modifier_ids:
                try:
                    modifier = ProductModifier.objects.get(id=modifier_id)
                    OrderLineModifier.objects.create(
                        order_line=order_line,
                        modifier=modifier,
                        price=modifier.price
                    )
                except ProductModifier.DoesNotExist:
                    pass
        
        return order_line


class OrderDiscountSerializer(serializers.ModelSerializer):
    """Serializer for order discounts."""
    
    applied_by_name = serializers.CharField(source='applied_by.get_full_name', read_only=True)
    
    class Meta:
        model = OrderDiscount
        fields = [
            'id', 'name', 'discount_type', 'value', 'applied_amount',
            'applied_by', 'applied_by_name', 'reason', 'created_at',
        ]
        read_only_fields = ['id', 'applied_amount', 'applied_by', 'created_at']


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list view."""
    
    table_name = serializers.CharField(source='table.display_name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'table', 'table_name', 'order_type',
            'status', 'customer_name', 'guests_count', 'total_amount',
            'amount_paid', 'balance_due', 'created_by_name', 'created_at',
            'item_count',
        ]
    
    def get_item_count(self, obj):
        return obj.lines.filter(is_deleted=False).count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail view."""
    
    table_name = serializers.CharField(source='table.display_name', read_only=True, allow_null=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    served_by_name = serializers.CharField(source='served_by.get_full_name', read_only=True, allow_null=True)
    lines = OrderLineSerializer(many=True, read_only=True)
    discounts = OrderDiscountSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_editable = serializers.BooleanField(read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'session', 'session_name', 'table', 'table_name',
            'order_type', 'status', 'customer_name', 'customer_phone',
            'customer_email', 'guests_count', 'subtotal', 'tax_amount',
            'discount_amount', 'discount_percent', 'tip_amount', 'total_amount',
            'amount_paid', 'balance_due', 'notes', 'kitchen_notes',
            'created_by', 'created_by_name', 'served_by', 'served_by_name',
            'sent_to_kitchen_at', 'ready_at', 'served_at', 'paid_at',
            'cancelled_at', 'lines', 'discounts', 'is_editable', 'can_be_cancelled',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'tax_amount', 'total_amount',
            'sent_to_kitchen_at', 'ready_at', 'served_at', 'paid_at',
            'cancelled_at', 'created_at', 'updated_at',
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders."""
    
    lines = OrderLineCreateSerializer(many=True, required=False)
    
    class Meta:
        model = Order
        fields = [
            'session', 'table', 'order_type', 'customer_name', 'customer_phone',
            'customer_email', 'guests_count', 'notes', 'kitchen_notes', 'lines',
        ]
    
    def validate(self, attrs):
        session = attrs.get('session')
        table = attrs.get('table')
        
        if not session.is_active:
            raise serializers.ValidationError({
                'session': 'Session is not active.'
            })
        
        # Check if table has an active order (for dine-in)
        if table and table.is_occupied:
            existing_order = table.current_order
            if existing_order and existing_order.status not in ['paid', 'cancelled']:
                raise serializers.ValidationError({
                    'table': f'Table already has an active order: {existing_order.order_number}'
                })
        
        return attrs
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        validated_data['created_by'] = self.context['request'].user
        
        order = Order.objects.create(**validated_data)
        
        # Create order lines
        for line_data in lines_data:
            line_data['order'] = order
            serializer = OrderLineCreateSerializer(data=line_data)
            if serializer.is_valid():
                serializer.save(order=order)
        
        # Occupy table
        if order.table:
            order.table.occupy(order)
        
        # Calculate totals
        order.calculate_totals()
        
        return order


class ApplyDiscountSerializer(serializers.Serializer):
    """Serializer for applying discount to order."""
    
    discount_type = serializers.ChoiceField(choices=['percent', 'fixed'])
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    name = serializers.CharField(max_length=100, default='Manual Discount')
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        order = self.context['order']
        
        if attrs['discount_type'] == 'percent':
            if attrs['value'] > user.max_discount_percent:
                raise serializers.ValidationError({
                    'value': f'Maximum discount you can apply is {user.max_discount_percent}%'
                })
        
        return attrs
    
    def create(self, validated_data):
        order = self.context['order']
        
        if validated_data['discount_type'] == 'percent':
            applied_amount = order.subtotal * (validated_data['value'] / 100)
            order.discount_percent = validated_data['value']
        else:
            applied_amount = validated_data['value']
        
        order.discount_amount = applied_amount
        order.calculate_totals()
        
        discount = OrderDiscount.objects.create(
            order=order,
            name=validated_data['name'],
            discount_type=validated_data['discount_type'],
            value=validated_data['value'],
            applied_amount=applied_amount,
            applied_by=self.context['request'].user,
            reason=validated_data.get('reason', ''),
        )
        
        return discount


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status."""
    
    status = serializers.ChoiceField(choices=[
        'sent_to_kitchen', 'preparing', 'ready', 'served', 'paid', 'cancelled'
    ])
    reason = serializers.CharField(required=False, allow_blank=True)
