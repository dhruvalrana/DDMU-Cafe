"""
Kitchen Display System models.
"""

from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel


class KitchenOrder(BaseModel):
    """
    Kitchen order ticket - represents an order in the kitchen display.
    """
    
    STATUS_CHOICES = [
        ('to_cook', 'To Cook'),
        ('preparing', 'Preparing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='kitchen_order'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_cook')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Timing
    received_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Target time (based on preparation time of items)
    target_time = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pos_kitchen_orders'
        ordering = ['-priority', 'received_at']
    
    def __str__(self):
        return f"Kitchen: {self.order.order_number}"
    
    @property
    def duration_minutes(self):
        """Time since order was received."""
        if self.completed_at:
            delta = self.completed_at - self.received_at
        else:
            delta = timezone.now() - self.received_at
        return int(delta.total_seconds() / 60)
    
    @property
    def is_overdue(self):
        """Check if order is past target time."""
        if self.target_time and self.status != 'completed':
            return timezone.now() > self.target_time
        return False
    
    @property
    def items_count(self):
        """Count of items in this order."""
        return self.order.lines.filter(is_deleted=False).count()
    
    @property
    def prepared_count(self):
        """Count of prepared items."""
        return self.order.lines.filter(is_deleted=False, is_prepared=True).count()
    
    def start_preparing(self):
        """Mark order as being prepared."""
        self.status = 'preparing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
        
        # Update main order
        self.order.status = 'preparing'
        self.order.save(update_fields=['status'])
    
    def complete(self):
        """Mark order as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
        
        # Mark all items as prepared
        self.order.lines.update(is_prepared=True, prepared_at=timezone.now())
        
        # Update main order
        self.order.mark_ready()
    
    def cancel(self):
        """Cancel kitchen order."""
        self.status = 'cancelled'
        self.save(update_fields=['status'])
    
    def bump(self):
        """Bump to next status."""
        if self.status == 'to_cook':
            self.start_preparing()
        elif self.status == 'preparing':
            self.complete()


class KitchenItemStatus(BaseModel):
    """
    Individual item status in kitchen (for item-level tracking).
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('cooking', 'Cooking'),
        ('ready', 'Ready'),
    ]
    
    kitchen_order = models.ForeignKey(
        KitchenOrder,
        on_delete=models.CASCADE,
        related_name='item_statuses'
    )
    order_line = models.OneToOneField(
        'orders.OrderLine',
        on_delete=models.CASCADE,
        related_name='kitchen_status'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pos_kitchen_item_statuses'
    
    def __str__(self):
        return f"{self.order_line.product.name}: {self.status}"
    
    def start_cooking(self):
        """Start cooking this item."""
        self.status = 'cooking'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_ready(self):
        """Mark item as ready."""
        self.status = 'ready'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
        
        # Update order line
        self.order_line.is_prepared = True
        self.order_line.prepared_at = timezone.now()
        self.order_line.save(update_fields=['is_prepared', 'prepared_at'])
        
        # Check if all items are ready
        kitchen_order = self.kitchen_order
        all_ready = not kitchen_order.item_statuses.exclude(status='ready').exists()
        if all_ready:
            kitchen_order.complete()


class KitchenStation(BaseModel):
    """
    Kitchen station/section (e.g., Grill, Fryer, Drinks).
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Categories handled by this station
    categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        related_name='kitchen_stations'
    )
    
    class Meta:
        db_table = 'pos_kitchen_stations'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
