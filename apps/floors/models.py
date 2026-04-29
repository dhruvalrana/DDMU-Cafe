"""
Floor and Table models for restaurant layout management.
"""

from django.db import models
from apps.core.models import BaseModel, EnableableModel


class Floor(BaseModel, EnableableModel):
    """
    Restaurant floor/area (e.g., Main Hall, Terrace, Private Room).
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # Layout configuration (for graphical floor plan)
    background_image = models.ImageField(upload_to='floors/', null=True, blank=True)
    background_color = models.CharField(max_length=7, default='#F3F4F6')
    
    class Meta:
        db_table = 'pos_floors'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def table_count(self):
        return self.tables.filter(is_active=True, is_deleted=False).count()
    
    @property
    def available_tables(self):
        """Get count of available (unoccupied) tables."""
        return self.tables.filter(
            is_active=True,
            is_deleted=False,
            is_occupied=False
        ).count()


class Table(BaseModel, EnableableModel):
    """
    Restaurant table with seating capacity and status.
    """
    
    SHAPE_CHOICES = [
        ('square', 'Square'),
        ('round', 'Round'),
        ('rectangle', 'Rectangle'),
        ('oval', 'Oval'),
    ]
    
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name='tables'
    )
    table_number = models.CharField(max_length=20)
    name = models.CharField(max_length=100, blank=True)
    seats = models.PositiveIntegerField(default=4)
    min_seats = models.PositiveIntegerField(default=1)
    
    # Layout position (for graphical floor plan)
    position_x = models.PositiveIntegerField(default=0)
    position_y = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=100)
    height = models.PositiveIntegerField(default=100)
    shape = models.CharField(max_length=20, choices=SHAPE_CHOICES, default='square')
    color = models.CharField(max_length=7, default='#10B981')
    
    # Status
    is_occupied = models.BooleanField(default=False)
    current_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_table'
    )
    
    # Optional appointment/reservation resource
    appointment_resource_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='External appointment system resource ID'
    )
    
    class Meta:
        db_table = 'pos_tables'
        unique_together = [['floor', 'table_number']]
        ordering = ['floor', 'table_number']
    
    def __str__(self):
        return f"{self.floor.name} - Table {self.table_number}"
    
    @property
    def display_name(self):
        return self.name if self.name else f"Table {self.table_number}"
    
    def occupy(self, order):
        """Mark table as occupied with an order."""
        self.is_occupied = True
        self.current_order = order
        self.save(update_fields=['is_occupied', 'current_order'])
    
    def release(self):
        """Release table after order is completed."""
        self.is_occupied = False
        self.current_order = None
        self.save(update_fields=['is_occupied', 'current_order'])


class TableReservation(BaseModel):
    """
    Table reservation for future booking.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('seated', 'Seated'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    
    # Customer info
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True)
    party_size = models.PositiveIntegerField(default=2)
    
    # Reservation details
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=120)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    # Linked order
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservation'
    )
    
    class Meta:
        db_table = 'pos_table_reservations'
        ordering = ['reservation_date', 'reservation_time']
    
    def __str__(self):
        return f"{self.customer_name} - {self.table} at {self.reservation_time}"
    
    def confirm(self):
        """Confirm the reservation."""
        self.status = 'confirmed'
        self.save(update_fields=['status'])
    
    def cancel(self):
        """Cancel the reservation."""
        self.status = 'cancelled'
        self.save(update_fields=['status'])
    
    def seat(self, order=None):
        """Mark customer as seated."""
        self.status = 'seated'
        if order:
            self.order = order
        self.save(update_fields=['status', 'order'])
        self.table.occupy(order)
