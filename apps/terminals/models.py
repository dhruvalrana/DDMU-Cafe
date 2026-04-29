"""
POS Terminal and Session models.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel, EnableableModel


class POSTerminal(BaseModel, EnableableModel):
    """
    POS Terminal/Register configuration.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    
    # Location
    floor = models.ForeignKey(
        'floors.Floor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='terminals'
    )
    
    # Configuration
    default_customer_display = models.BooleanField(default=True)
    default_kitchen_display = models.BooleanField(default=True)
    receipt_header = models.TextField(blank=True)
    receipt_footer = models.TextField(blank=True)
    
    # Hardware
    receipt_printer_ip = models.GenericIPAddressField(null=True, blank=True)
    kitchen_printer_ip = models.GenericIPAddressField(null=True, blank=True)
    cash_drawer_enabled = models.BooleanField(default=True)
    
    # Access restrictions
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='allowed_terminals'
    )
    
    class Meta:
        db_table = 'pos_terminals'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def has_active_session(self):
        return self.sessions.filter(is_active=True).exists()
    
    @property
    def current_session(self):
        return self.sessions.filter(is_active=True).first()


class POSSession(BaseModel):
    """
    POS Session for tracking daily operations.
    """
    
    STATUS_CHOICES = [
        ('opening', 'Opening'),
        ('open', 'Open'),
        ('closing', 'Closing'),
        ('closed', 'Closed'),
    ]
    
    terminal = models.ForeignKey(
        POSTerminal,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pos_sessions'
    )
    
    # Session name/number
    name = models.CharField(max_length=100, blank=True)
    
    # Timing
    opening_time = models.DateTimeField(default=timezone.now)
    closing_time = models.DateTimeField(null=True, blank=True)
    
    # Cash management
    opening_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    closing_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    expected_closing_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    cash_difference = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_active = models.BooleanField(default=True)
    
    # Notes
    opening_notes = models.TextField(blank=True)
    closing_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pos_sessions'
        ordering = ['-opening_time']
        constraints = [
            models.UniqueConstraint(
                fields=['terminal'],
                condition=models.Q(is_active=True),
                name='unique_active_session_per_terminal'
            )
        ]
    
    def __str__(self):
        return f"{self.terminal.name} - {self.opening_time.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        if not self.name:
            # Generate session name
            date_str = self.opening_time.strftime('%Y%m%d')
            count = POSSession.objects.filter(
                terminal=self.terminal,
                opening_time__date=self.opening_time.date()
            ).count() + 1
            self.name = f"{self.terminal.code}/{date_str}/{count:02d}"
        super().save(*args, **kwargs)
    
    def close(self, closing_balance, notes=''):
        """Close the session with final balance."""
        from django.db.models import Sum
        
        # Calculate expected closing balance
        cash_payments = self.orders.filter(
            status='paid',
            is_deleted=False
        ).aggregate(
            total=Sum('payments__amount', filter=models.Q(payments__payment_method__method_type='cash'))
        )['total'] or Decimal('0.00')
        
        self.expected_closing_balance = self.opening_balance + cash_payments
        self.closing_balance = Decimal(str(closing_balance))
        self.cash_difference = self.closing_balance - self.expected_closing_balance
        self.closing_time = timezone.now()
        self.closing_notes = notes
        self.status = 'closed'
        self.is_active = False
        self.save()
    
    @property
    def total_sales(self):
        """Calculate total sales for this session."""
        from django.db.models import Sum
        return self.orders.filter(
            status='paid',
            is_deleted=False
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    @property
    def order_count(self):
        """Count of orders in this session."""
        return self.orders.filter(is_deleted=False).count()
    
    @property
    def cash_total(self):
        """Total cash payments in this session."""
        from django.db.models import Sum
        return self.orders.filter(
            status='paid',
            is_deleted=False
        ).aggregate(
            total=Sum('payments__amount', filter=models.Q(payments__payment_method__method_type='cash'))
        )['total'] or Decimal('0.00')


class CashMovement(BaseModel):
    """
    Track cash movements (in/out) during a session.
    """
    
    MOVEMENT_TYPES = [
        ('in', 'Cash In'),
        ('out', 'Cash Out'),
    ]
    
    session = models.ForeignKey(
        POSSession,
        on_delete=models.CASCADE,
        related_name='cash_movements'
    )
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cash_movements'
    )
    
    class Meta:
        db_table = 'pos_cash_movements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.movement_type}: {self.amount} - {self.reason}"
