"""
Self-Order System models.
"""

import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.core.models import BaseModel


class SelfOrderSession(BaseModel):
    """
    Session for self-ordering (QR code based or kiosk).
    """
    SESSION_TYPE_CHOICES = [
        ('table_qr', 'Table QR Code'),
        ('takeaway_qr', 'Takeaway QR Code'),
        ('kiosk', 'Kiosk'),
    ]
    
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    token = models.CharField(max_length=64, unique=True)
    
    # Linked entities
    table = models.ForeignKey(
        'floors.Table',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='self_order_sessions'
    )
    terminal = models.ForeignKey(
        'terminals.POSTerminal',
        on_delete=models.CASCADE,
        related_name='self_order_sessions'
    )
    pos_session = models.ForeignKey(
        'terminals.POSSession',
        on_delete=models.CASCADE,
        related_name='self_order_sessions'
    )
    
    # Customer info (optional)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Session state
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'pos_self_order_sessions'
    
    def __str__(self):
        return f"Self-Order: {self.token[:8]}..."
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            # 2 hour default expiry
            self.expires_at = timezone.now() + timedelta(hours=2)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at
    
    def extend(self, hours=1):
        """Extend session expiry."""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expires_at'])
    
    def close(self):
        """Close the session."""
        self.is_active = False
        self.save(update_fields=['is_active'])


class SelfOrderCart(BaseModel):
    """
    Cart for self-ordering session.
    """
    session = models.OneToOneField(
        SelfOrderSession,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pos_self_order_carts'
    
    def __str__(self):
        return f"Cart: {self.session.token[:8]}..."
    
    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())
    
    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()


class SelfOrderCartItem(BaseModel):
    """
    Item in self-order cart.
    """
    cart = models.ForeignKey(
        SelfOrderCart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pos_self_order_cart_items'
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    @property
    def unit_price(self):
        price = self.product.price
        if self.variant:
            price += self.variant.extra_price
        # Add modifier prices
        price += sum(m.price for m in self.modifiers.all())
        return price
    
    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class SelfOrderCartItemModifier(BaseModel):
    """
    Modifier applied to self-order cart item.
    """
    cart_item = models.ForeignKey(
        SelfOrderCartItem,
        on_delete=models.CASCADE,
        related_name='modifiers'
    )
    modifier = models.ForeignKey(
        'products.ProductModifier',
        on_delete=models.CASCADE
    )
    
    @property
    def price(self):
        return self.modifier.price
    
    class Meta:
        db_table = 'pos_self_order_cart_item_modifiers'


class SelfOrderQRCode(BaseModel):
    """
    Permanent QR codes for tables.
    """
    table = models.OneToOneField(
        'floors.Table',
        on_delete=models.CASCADE,
        related_name='qr_code'
    )
    code = models.CharField(max_length=32, unique=True)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    scan_count = models.PositiveIntegerField(default=0)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pos_self_order_qr_codes'
    
    def __str__(self):
        return f"QR: {self.table.display_name}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)
    
    def record_scan(self):
        """Record a scan."""
        self.scan_count += 1
        self.last_scanned_at = timezone.now()
        self.save(update_fields=['scan_count', 'last_scanned_at'])
