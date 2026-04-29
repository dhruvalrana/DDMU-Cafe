"""
Serializers for product management.
"""

from rest_framework import serializers
from .models import (
    Category,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariant,
    ComboProduct,
    ProductModifier,
)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    
    product_count = serializers.IntegerField(read_only=True)
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'image', 'parent',
            'display_order', 'color', 'is_active', 'product_count',
            'subcategories', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_subcategories(self, obj):
        subcats = obj.subcategories.filter(is_active=True, is_deleted=False)
        return CategorySerializer(subcats, many=True, read_only=True).data


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    """Serializer for ProductAttributeValue."""
    
    class Meta:
        model = ProductAttributeValue
        fields = ['id', 'name', 'display_order', 'color_code']
        read_only_fields = ['id']


class ProductAttributeSerializer(serializers.ModelSerializer):
    """Serializer for ProductAttribute with values."""
    
    values = ProductAttributeValueSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductAttribute
        fields = ['id', 'name', 'display_type', 'values', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductAttributeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ProductAttribute with values."""
    
    values = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ProductAttribute
        fields = ['id', 'name', 'display_type', 'values']
    
    def create(self, validated_data):
        values_data = validated_data.pop('values', [])
        attribute = ProductAttribute.objects.create(**validated_data)
        
        for idx, value_data in enumerate(values_data):
            ProductAttributeValue.objects.create(
                attribute=attribute,
                name=value_data.get('name'),
                display_order=value_data.get('display_order', idx),
                color_code=value_data.get('color_code', '')
            )
        
        return attribute


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for ProductVariant."""
    
    attribute_values = ProductAttributeValueSerializer(many=True, read_only=True)
    full_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    full_price_with_tax = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'name', 'sku', 'barcode', 'extra_price',
            'attribute_values', 'stock_quantity', 'is_active',
            'full_price', 'full_price_with_tax', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ProductVariantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ProductVariant."""
    
    attribute_value_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ProductVariant
        fields = [
            'product', 'name', 'sku', 'barcode', 'extra_price',
            'attribute_value_ids', 'stock_quantity', 'is_active',
        ]
    
    def create(self, validated_data):
        attribute_value_ids = validated_data.pop('attribute_value_ids', [])
        variant = ProductVariant.objects.create(**validated_data)
        
        if attribute_value_ids:
            attribute_values = ProductAttributeValue.objects.filter(id__in=attribute_value_ids)
            variant.attribute_values.set(attribute_values)
        
        return variant


class ProductModifierSerializer(serializers.ModelSerializer):
    """Serializer for ProductModifier."""
    
    class Meta:
        model = ProductModifier
        fields = ['id', 'name', 'price', 'is_default', 'is_active']
        read_only_fields = ['id']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for Product listing (minimal data)."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_with_tax = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'internal_reference', 'barcode', 'category',
            'category_name', 'price', 'price_with_tax', 'tax_rate',
            'image', 'unit', 'is_active', 'is_available_for_pos',
            'is_available_for_self_order', 'has_variants', 'is_combo',
            'display_order', 'color',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for Product detail view."""
    
    category = CategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False)
    variants = ProductVariantSerializer(many=True, read_only=True)
    modifiers = ProductModifierSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    price_with_tax = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'internal_reference', 'barcode', 'category',
            'category_id', 'description', 'price', 'cost_price', 'tax_rate',
            'price_with_tax', 'image', 'unit', 'display_order', 'color',
            'track_inventory', 'stock_quantity', 'low_stock_threshold',
            'is_low_stock', 'is_active', 'is_available_for_pos',
            'is_available_for_self_order', 'is_combo', 'has_variants',
            'preparation_time', 'kitchen_notes', 'attributes', 'variants',
            'modifiers', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id:
            instance.category_id = category_id
        return super().update(instance, validated_data)


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Product."""
    
    category_id = serializers.UUIDField(required=False, allow_null=True)
    attribute_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'internal_reference', 'barcode', 'category_id',
            'description', 'price', 'cost_price', 'tax_rate', 'image',
            'unit', 'display_order', 'color', 'track_inventory',
            'stock_quantity', 'low_stock_threshold', 'is_active',
            'is_available_for_pos', 'is_available_for_self_order',
            'is_combo', 'has_variants', 'preparation_time', 'kitchen_notes',
            'attribute_ids',
        ]
    
    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        attribute_ids = validated_data.pop('attribute_ids', [])
        
        if category_id:
            validated_data['category_id'] = category_id
        
        product = Product.objects.create(**validated_data)
        
        if attribute_ids:
            attributes = ProductAttribute.objects.filter(id__in=attribute_ids)
            product.attributes.set(attributes)
        
        return product


class ComboProductSerializer(serializers.ModelSerializer):
    """Serializer for ComboProduct."""
    
    product_detail = ProductListSerializer(source='product', read_only=True)
    
    class Meta:
        model = ComboProduct
        fields = ['id', 'combo', 'product', 'product_detail', 'quantity', 'is_optional']
        read_only_fields = ['id']


class ProductPOSSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for POS display.
    Contains only the fields needed for the POS interface.
    """
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    modifiers = ProductModifierSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category', 'category_name',
            'category_color', 'price', 'tax_rate', 'image', 'color',
            'has_variants', 'variants', 'modifiers', 'preparation_time',
        ]
