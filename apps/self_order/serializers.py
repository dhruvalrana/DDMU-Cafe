"""
Serializers for Self-Order System.
"""

from rest_framework import serializers
from .models import (
    SelfOrderSession, SelfOrderCart, SelfOrderCartItem,
    SelfOrderCartItemModifier, SelfOrderQRCode
)
from apps.products.serializers import ProductPOSSerializer, ProductModifierSerializer


class SelfOrderCartItemModifierSerializer(serializers.ModelSerializer):
    """Serializer for cart item modifiers."""
    
    name = serializers.CharField(source='modifier.name', read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = SelfOrderCartItemModifier
        fields = ['id', 'modifier', 'name', 'price']
        read_only_fields = ['id']


class SelfOrderCartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    variant_name = serializers.CharField(source='variant.display_name', read_only=True, allow_null=True)
    modifiers = SelfOrderCartItemModifierSerializer(many=True, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = SelfOrderCartItem
        fields = [
            'id', 'product', 'product_name', 'product_image',
            'variant', 'variant_name', 'quantity', 'notes',
            'modifiers', 'unit_price', 'subtotal',
        ]
        read_only_fields = ['id']


class SelfOrderCartSerializer(serializers.ModelSerializer):
    """Serializer for cart."""
    
    items = SelfOrderCartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SelfOrderCart
        fields = ['id', 'notes', 'items', 'subtotal', 'item_count']
        read_only_fields = ['id']


class SelfOrderSessionSerializer(serializers.ModelSerializer):
    """Serializer for self-order session."""
    
    table_name = serializers.CharField(source='table.display_name', read_only=True, allow_null=True)
    cart = SelfOrderCartSerializer(read_only=True)
    
    class Meta:
        model = SelfOrderSession
        fields = [
            'id', 'session_type', 'token', 'table', 'table_name',
            'customer_name', 'customer_phone', 'is_active',
            'expires_at', 'cart',
        ]
        read_only_fields = ['id', 'token', 'expires_at']


class InitiateSessionSerializer(serializers.Serializer):
    """Serializer for initiating a self-order session."""
    
    qr_code = serializers.CharField(required=False)
    table_id = serializers.UUIDField(required=False)
    session_type = serializers.ChoiceField(
        choices=['table_qr', 'takeaway_qr', 'kiosk'],
        default='table_qr'
    )
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data.get('session_type') == 'table_qr':
            if not data.get('qr_code') and not data.get('table_id'):
                raise serializers.ValidationError(
                    "Either qr_code or table_id is required for table ordering."
                )
        return data


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding item to cart."""
    
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    modifier_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item."""
    
    quantity = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)


class SubmitOrderSerializer(serializers.Serializer):
    """Serializer for submitting order from cart."""
    
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    pay_now = serializers.BooleanField(default=False)


class SelfOrderQRCodeSerializer(serializers.ModelSerializer):
    """Serializer for QR codes."""
    
    table_name = serializers.CharField(source='table.display_name', read_only=True)
    floor_name = serializers.CharField(source='table.floor.name', read_only=True)
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = SelfOrderQRCode
        fields = [
            'id', 'table', 'table_name', 'floor_name', 'code',
            'is_active', 'scan_count', 'last_scanned_at', 'url',
        ]
        read_only_fields = ['id', 'code', 'scan_count', 'last_scanned_at']
    
    def get_url(self, obj):
        request = self.context.get('request')
        if request:
            from django.conf import settings
            base_url = getattr(settings, 'SELF_ORDER_URL', request.build_absolute_uri('/self-order/'))
            return f"{base_url}?code={obj.code}"
        return None
