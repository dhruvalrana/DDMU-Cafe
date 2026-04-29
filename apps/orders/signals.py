"""
Django signals for order events.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order, OrderLine


@receiver(post_save, sender=Order)
def order_saved(sender, instance, created, **kwargs):
    """Handle order save events."""
    channel_layer = get_channel_layer()
    
    # Notify session channel
    async_to_sync(channel_layer.group_send)(
        f'orders_{instance.session_id}',
        {
            'type': 'order_update',
            'action': 'created' if created else 'updated',
            'order_id': str(instance.id),
            'order_number': instance.order_number,
            'status': instance.status,
            'table': str(instance.table_id) if instance.table_id else None,
        }
    )
    
    # Notify customer display if exists
    async_to_sync(channel_layer.group_send)(
        f'customer_{instance.id}',
        {
            'type': 'order_update',
            'order_id': str(instance.id),
            'order_number': instance.order_number,
            'status': instance.status,
            'total': str(instance.total_amount),
        }
    )
    
    # Notify kitchen if sent to kitchen
    if instance.status == 'sent_to_kitchen':
        async_to_sync(channel_layer.group_send)(
            f'kitchen_{instance.session.terminal_id}',
            {
                'type': 'new_order',
                'order_id': str(instance.id),
                'order_number': instance.order_number,
                'table': instance.table.display_name if instance.table else 'Takeaway',
            }
        )


@receiver(post_save, sender=OrderLine)
def order_line_saved(sender, instance, created, **kwargs):
    """Recalculate order totals when line is saved."""
    instance.order.calculate_totals()


@receiver(post_delete, sender=OrderLine)
def order_line_deleted(sender, instance, **kwargs):
    """Recalculate order totals when line is deleted."""
    try:
        instance.order.calculate_totals()
    except Order.DoesNotExist:
        pass
