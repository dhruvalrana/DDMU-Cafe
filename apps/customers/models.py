"""
Customer Display models.
"""

from django.db import models
from apps.core.models import BaseModel


class CustomerDisplayConfig(BaseModel):
    """
    Configuration for customer-facing display.
    """
    terminal = models.OneToOneField(
        'terminals.POSTerminal',
        on_delete=models.CASCADE,
        related_name='customer_display'
    )
    
    # Display settings
    is_enabled = models.BooleanField(default=True)
    show_logo = models.BooleanField(default=True)
    show_order_items = models.BooleanField(default=True)
    show_tax = models.BooleanField(default=True)
    show_promotions = models.BooleanField(default=True)
    
    # Idle screen
    idle_message = models.CharField(max_length=200, default='Welcome!')
    idle_image = models.ImageField(upload_to='customer_display/', null=True, blank=True)
    
    # Theming
    background_color = models.CharField(max_length=7, default='#FFFFFF')
    primary_color = models.CharField(max_length=7, default='#4CAF50')
    text_color = models.CharField(max_length=7, default='#333333')
    
    class Meta:
        db_table = 'pos_customer_display_config'
    
    def __str__(self):
        return f"Display: {self.terminal.name}"


class CustomerPromotion(BaseModel):
    """
    Promotional content for customer display.
    """
    DISPLAY_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('text', 'Text'),
    ]
    
    title = models.CharField(max_length=200)
    display_type = models.CharField(max_length=20, choices=DISPLAY_TYPE_CHOICES, default='image')
    content = models.TextField(blank=True, help_text='Text content or URL')
    image = models.ImageField(upload_to='promotions/', null=True, blank=True)
    
    # Display settings
    display_duration = models.PositiveIntegerField(default=10, help_text='Duration in seconds')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Scheduling
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pos_customer_promotions'
        ordering = ['display_order']
    
    def __str__(self):
        return self.title
