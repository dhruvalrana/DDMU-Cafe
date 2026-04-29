"""
Order models for the POS system.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel
from apps.core.utils import generate_order_number


class Order(BaseModel):
    """
    Main Order model for restaurant POS.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent_to_kitchen', 'Sent to Kitchen'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
        ('self_order', 'Self Order'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Session and terminal
    session = models.ForeignKey(
        'terminals.POSSession',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Table (for dine-in)
    table = models.ForeignKey(
        'floors.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    
    # Order details
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='dine_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Customer info
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    guests_count = models.PositiveIntegerField(default=1)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Notes
    notes = models.TextField(blank=True)
    kitchen_notes = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_orders'
    )
    served_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='served_orders'
    )
    
    # Timestamps
    sent_to_kitchen_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Self-order token (for token-based ordering)
    self_order_token = models.CharField(max_length=64, blank=True, unique=True, null=True)
    
    class Meta:
        db_table = 'pos_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['session', 'status']),
            models.Index(fields=['table', 'status']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Recalculate order totals from lines."""
        lines = self.lines.filter(is_deleted=False)
        
        self.subtotal = sum(line.line_total for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        
        # Apply discount
        if self.discount_percent > 0:
            self.discount_amount = self.subtotal * (self.discount_percent / 100)
        
        self.total_amount = (
            self.subtotal + 
            self.tax_amount - 
            self.discount_amount + 
            self.tip_amount
        )
        
        self.save(update_fields=[
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount'
        ])
    
    def send_to_kitchen(self):
        """Send order to kitchen."""
        self.status = 'sent_to_kitchen'
        self.sent_to_kitchen_at = timezone.now()
        self.save(update_fields=['status', 'sent_to_kitchen_at'])
        
        # Create kitchen order
        from apps.kitchen.models import KitchenOrder
        kitchen_order, created = KitchenOrder.objects.get_or_create(
            order=self,
            defaults={'status': 'to_cook'}
        )
        if not created:
            kitchen_order.status = 'to_cook'
            kitchen_order.save(update_fields=['status'])
    
    def mark_ready(self):
        """Mark order as ready for serving."""
        self.status = 'ready'
        self.ready_at = timezone.now()
        self.save(update_fields=['status', 'ready_at'])
    
    def mark_served(self, served_by=None):
        """Mark order as served."""
        self.status = 'served'
        self.served_at = timezone.now()
        if served_by:
            self.served_by = served_by
        self.save(update_fields=['status', 'served_at', 'served_by'])
    
    def cancel(self, reason=''):
        """Cancel the order."""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.save(update_fields=['status', 'cancelled_at', 'notes'])
        
        # Release table
        if self.table:
            self.table.release()
    
    @property
    def is_editable(self):
        """Check if order can be edited."""
        return self.status in ['draft']
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled."""
        return self.status in ['draft', 'sent_to_kitchen', 'preparing']
    
    @property
    def amount_paid(self):
        """Calculate total amount paid."""
        return self.payments.filter(
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_amount - self.amount_paid


class OrderLine(BaseModel):
    """
    Individual line item in an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='order_lines'
    )
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_lines'
    )
    
    # Quantity
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    
    # Pricing (captured at time of order)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Calculated amounts
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Discount on this line
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Notes
    notes = models.TextField(blank=True, help_text='Special instructions')
    
    # Kitchen tracking
    is_sent_to_kitchen = models.BooleanField(default=False)
    is_prepared = models.BooleanField(default=False)
    prepared_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pos_order_lines'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Calculate line totals
        self.line_total = (self.quantity * self.unit_price) - self.discount_amount
        self.tax_amount = self.line_total * (self.tax_rate / 100)
        super().save(*args, **kwargs)
    
    def update_quantity(self, new_quantity):
        """Update quantity and recalculate."""
        self.quantity = Decimal(str(new_quantity))
        self.save()
        self.order.calculate_totals()


class OrderLineModifier(BaseModel):
    """
    Modifiers applied to an order line.
    """
    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        related_name='modifiers'
    )
    modifier = models.ForeignKey(
        'products.ProductModifier',
        on_delete=models.PROTECT,
        related_name='order_line_modifiers'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'pos_order_line_modifiers'
    
    def __str__(self):
        return f"{self.order_line} + {self.modifier.name}"


class OrderDiscount(BaseModel):
    """
    Discounts applied to an order.
    """
    
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='discounts'
    )
    name = models.CharField(max_length=100)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    applied_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='applied_discounts'
    )
    reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pos_order_discounts'
    
    def __str__(self):
        return f"{self.name}: {self.applied_amount}"
