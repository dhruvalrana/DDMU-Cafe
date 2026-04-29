"""
Product models for the POS system.
Includes categories, products, attributes, and variants.
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.core.models import BaseModel, EnableableModel


class Category(BaseModel, EnableableModel):
    """
    Product category for organizing menu items.
    Supports hierarchical categories.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    display_order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Hex color code')
    is_available_for_self_order = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'pos_categories'
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def product_count(self):
        return self.products.filter(is_active=True, is_deleted=False).count()


class ProductAttribute(BaseModel):
    """
    Attributes for product variants (e.g., Size, Pack, Flavor).
    """
    name = models.CharField(max_length=100)
    display_type = models.CharField(
        max_length=20,
        choices=[
            ('radio', 'Radio Buttons'),
            ('select', 'Dropdown'),
            ('color', 'Color Swatches'),
            ('buttons', 'Buttons'),
        ],
        default='buttons'
    )
    
    class Meta:
        db_table = 'pos_product_attributes'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ProductAttributeValue(BaseModel):
    """
    Values for product attributes (e.g., Small, Medium, Large for Size).
    """
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name='values'
    )
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    color_code = models.CharField(
        max_length=7,
        blank=True,
        help_text='Hex color for color-type attributes'
    )
    
    class Meta:
        db_table = 'pos_product_attribute_values'
        ordering = ['attribute', 'display_order', 'name']
        unique_together = [['attribute', 'name']]
    
    def __str__(self):
        return f"{self.attribute.name}: {self.name}"


class Product(BaseModel, EnableableModel):
    """
    Product/Menu item in the POS system.
    """
    
    UNIT_CHOICES = [
        ('unit', 'Unit'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('portion', 'Portion'),
        ('plate', 'Plate'),
        ('glass', 'Glass'),
        ('cup', 'Cup'),
    ]
    
    TAX_CHOICES = [
        (Decimal('0.00'), 'No Tax'),
        (Decimal('5.00'), '5% GST'),
        (Decimal('12.00'), '12% GST'),
        (Decimal('18.00'), '18% GST'),
        (Decimal('28.00'), '28% GST'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=200)
    internal_reference = models.CharField(max_length=50, blank=True, unique=True, null=True)
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    description = models.TextField(blank=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        choices=TAX_CHOICES,
        default=Decimal('5.00')
    )
    
    # Display
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='unit')
    display_order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default='#10B981', help_text='Hex color code')
    
    # Inventory
    track_inventory = models.BooleanField(default=False)
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    low_stock_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('10.00')
    )
    
    # Flags
    is_available_for_pos = models.BooleanField(default=True)
    is_available_for_self_order = models.BooleanField(default=True)
    is_combo = models.BooleanField(default=False)
    has_variants = models.BooleanField(default=False)
    
    # Kitchen
    preparation_time = models.PositiveIntegerField(
        default=10,
        help_text='Estimated preparation time in minutes'
    )
    kitchen_notes = models.TextField(blank=True, help_text='Special instructions for kitchen')
    
    # Attributes for variants
    attributes = models.ManyToManyField(
        ProductAttribute,
        blank=True,
        related_name='products'
    )
    
    class Meta:
        db_table = 'pos_products'
        ordering = ['category', 'display_order', 'name']
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_available_for_pos']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def price_with_tax(self):
        """Calculate price including tax."""
        tax_amount = self.price * (self.tax_rate / 100)
        return self.price + tax_amount
    
    @property
    def is_low_stock(self):
        """Check if stock is below threshold."""
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    def reduce_stock(self, quantity):
        """Reduce stock quantity."""
        if self.track_inventory:
            self.stock_quantity -= Decimal(str(quantity))
            self.save(update_fields=['stock_quantity'])
    
    def add_stock(self, quantity):
        """Add to stock quantity."""
        if self.track_inventory:
            self.stock_quantity += Decimal(str(quantity))
            self.save(update_fields=['stock_quantity'])


class ProductVariant(BaseModel, EnableableModel):
    """
    Product variant with specific attribute values and price adjustments.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    name = models.CharField(max_length=200, blank=True)
    sku = models.CharField(max_length=50, blank=True, unique=True, null=True)
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    
    # Pricing
    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Additional price on top of base product price'
    )
    
    # Attribute values for this variant
    attribute_values = models.ManyToManyField(
        ProductAttributeValue,
        related_name='variants'
    )
    
    # Inventory
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    class Meta:
        db_table = 'pos_product_variants'
        ordering = ['product', 'name']
    
    def __str__(self):
        return f"{self.product.name} - {self.variant_name}"
    
    @property
    def variant_name(self):
        """Generate variant name from attribute values."""
        if self.name:
            return self.name
        values = self.attribute_values.all()
        if values:
            return ', '.join([v.name for v in values])
        return 'Default'
    
    @property
    def full_price(self):
        """Calculate full price (base + extra)."""
        return self.product.price + self.extra_price
    
    @property
    def full_price_with_tax(self):
        """Calculate full price including tax."""
        base = self.full_price
        tax_amount = base * (self.product.tax_rate / 100)
        return base + tax_amount
    
    def save(self, *args, **kwargs):
        if not self.name:
            super().save(*args, **kwargs)
            self.name = self.variant_name
            super().save(update_fields=['name'])
        else:
            super().save(*args, **kwargs)


class ComboProduct(BaseModel):
    """
    Products included in a combo/meal deal.
    """
    combo = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='combo_items',
        limit_choices_to={'is_combo': True}
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_combos'
    )
    quantity = models.PositiveIntegerField(default=1)
    is_optional = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'pos_combo_products'
        unique_together = [['combo', 'product']]
    
    def __str__(self):
        return f"{self.combo.name} includes {self.quantity}x {self.product.name}"


class ProductModifier(BaseModel, EnableableModel):
    """
    Modifiers/add-ons that can be applied to products.
    (e.g., Extra cheese, No onions, Extra spicy)
    """
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name='modifiers'
    )
    is_default = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'pos_product_modifiers'
        ordering = ['name']
    
    def __str__(self):
        return self.name
