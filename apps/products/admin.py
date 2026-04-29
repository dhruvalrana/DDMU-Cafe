from django.contrib import admin
from .models import (
    Category,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariant,
    ComboProduct,
    ProductModifier,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'tax_rate', 'is_active', 'is_available_for_pos']
    list_filter = ['category', 'is_active', 'is_available_for_pos', 'has_variants', 'is_combo']
    search_fields = ['name', 'description', 'internal_reference', 'barcode']
    ordering = ['category', 'display_order', 'name']
    inlines = [ProductVariantInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'internal_reference', 'barcode', 'category', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'cost_price', 'tax_rate')
        }),
        ('Display', {
            'fields': ('image', 'unit', 'display_order', 'color')
        }),
        ('Inventory', {
            'fields': ('track_inventory', 'stock_quantity', 'low_stock_threshold')
        }),
        ('Availability', {
            'fields': ('is_active', 'is_available_for_pos', 'is_available_for_self_order', 'is_combo', 'has_variants')
        }),
        ('Kitchen', {
            'fields': ('preparation_time', 'kitchen_notes')
        }),
    )


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_type', 'created_at']


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ['attribute', 'name', 'display_order']
    list_filter = ['attribute']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'extra_price', 'is_active']
    list_filter = ['product', 'is_active']


@admin.register(ProductModifier)
class ProductModifierAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'is_default']
    list_filter = ['is_active']


@admin.register(ComboProduct)
class ComboProductAdmin(admin.ModelAdmin):
    list_display = ['combo', 'product', 'quantity', 'is_optional']
    list_filter = ['combo']
