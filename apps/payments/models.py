"""
Payment models for the POS system.
Includes payment methods, transactions, and UPI configuration.
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
from apps.core.models import BaseModel, EnableableModel


class PaymentMethod(BaseModel, EnableableModel):
    """
    Available payment methods in the POS system.
    """
    
    METHOD_TYPES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('wallet', 'Digital Wallet'),
        ('credit', 'Store Credit'),
        ('split', 'Split Payment'),
    ]
    
    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Icon name or path')
    display_order = models.PositiveIntegerField(default=0)
    
    # Configuration
    is_default = models.BooleanField(default=False)
    requires_verification = models.BooleanField(default=False)
    allows_change = models.BooleanField(default=True, help_text='Can give change (cash)')
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Terminal restrictions
    terminals = models.ManyToManyField(
        'terminals.POSTerminal',
        blank=True,
        related_name='payment_methods'
    )
    
    class Meta:
        db_table = 'pos_payment_methods'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_method_type_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method
        if self.is_default:
            PaymentMethod.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class UPIConfiguration(BaseModel):
    """
    UPI configuration for QR code generation.
    """
    payment_method = models.OneToOneField(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='upi_config',
        limit_choices_to={'method_type': 'upi'}
    )
    upi_id = models.CharField(max_length=100)
    merchant_name = models.CharField(max_length=100)
    merchant_code = models.CharField(max_length=20, blank=True)
    
    # QR Settings
    qr_box_size = models.PositiveIntegerField(default=10)
    qr_border = models.PositiveIntegerField(default=4)
    
    # Verification
    auto_verify = models.BooleanField(
        default=False,
        help_text='Automatically verify UPI payments (requires integration)'
    )
    verification_timeout = models.PositiveIntegerField(
        default=300,
        help_text='Timeout in seconds for payment verification'
    )
    
    class Meta:
        db_table = 'pos_upi_configurations'
    
    def __str__(self):
        return f"UPI: {self.upi_id}"


class CardConfiguration(BaseModel):
    """
    Card payment configuration (for external terminal integration).
    """
    payment_method = models.OneToOneField(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='card_config',
        limit_choices_to={'method_type': 'card'}
    )
    
    terminal_id = models.CharField(max_length=50, blank=True)
    merchant_id = models.CharField(max_length=50, blank=True)
    
    # Supported cards
    accept_visa = models.BooleanField(default=True)
    accept_mastercard = models.BooleanField(default=True)
    accept_amex = models.BooleanField(default=True)
    accept_rupay = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'pos_card_configurations'
    
    def __str__(self):
        return f"Card Config: {self.terminal_id}"


class Payment(BaseModel):
    """
    Individual payment record for an order.
    An order can have multiple payments (split payment).
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    change_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    
    # Card details (masked)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    
    # UPI details
    upi_transaction_id = models.CharField(max_length=100, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_payments'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pos_payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} ({self.status})"
    
    def complete(self):
        """Mark payment as completed."""
        from django.utils import timezone
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])
    
    def fail(self, reason=''):
        """Mark payment as failed."""
        self.status = 'failed'
        self.notes = reason
        self.save(update_fields=['status', 'notes'])
    
    def refund(self):
        """Mark payment as refunded."""
        from django.utils import timezone
        self.status = 'refunded'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])


class PaymentRefund(BaseModel):
    """
    Refund record for a payment.
    """
    
    REFUND_REASONS = [
        ('customer_request', 'Customer Request'),
        ('order_cancelled', 'Order Cancelled'),
        ('product_issue', 'Product Issue'),
        ('wrong_order', 'Wrong Order'),
        ('other', 'Other'),
    ]
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REFUND_REASONS)
    notes = models.TextField(blank=True)
    
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_refunds'
    )
    refund_transaction_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'pos_payment_refunds'
    
    def __str__(self):
        return f"Refund {self.id} - {self.amount}"
