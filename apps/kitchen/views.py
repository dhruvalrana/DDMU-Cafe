"""
Kitchen Display System views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from apps.core.permissions import IsKitchenUser, IsManagerOrAdmin
from .models import KitchenOrder, KitchenItemStatus, KitchenStation
from .serializers import (
    KitchenOrderSerializer,
    KitchenOrderListSerializer,
    KitchenItemStatusSerializer,
    KitchenStationSerializer,
    BumpOrderSerializer,
    UpdateItemStatusSerializer,
)


class KitchenOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Kitchen Orders.
    
    GET /api/v1/kitchen/
    GET /api/v1/kitchen/<id>/
    """
    queryset = KitchenOrder.objects.filter(is_deleted=False).select_related(
        'order', 'order__table'
    ).prefetch_related('order__lines', 'order__lines__product', 'item_statuses')
    permission_classes = [IsKitchenUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return KitchenOrderListSerializer
        return KitchenOrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by terminal
        terminal_id = self.request.query_params.get('terminal')
        if terminal_id:
            queryset = queryset.filter(order__session__terminal_id=terminal_id)
        
        # Default: show active orders
        show_completed = self.request.query_params.get('show_completed', 'false')
        if show_completed.lower() != 'true':
            queryset = queryset.exclude(status__in=['completed', 'cancelled'])
        
        return queryset.order_by('-priority', 'received_at')
    
    @action(detail=True, methods=['post'])
    def bump(self, request, pk=None):
        """Bump order to next status."""
        kitchen_order = self.get_object()
        serializer = BumpOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        if notes:
            kitchen_order.notes = f"{kitchen_order.notes}\n{notes}".strip()
            kitchen_order.save(update_fields=['notes'])
        
        kitchen_order.bump()
        
        # Send WebSocket notification
        self._notify_status_change(kitchen_order)
        
        return Response(KitchenOrderSerializer(kitchen_order).data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start preparing order."""
        kitchen_order = self.get_object()
        kitchen_order.start_preparing()
        self._notify_status_change(kitchen_order)
        return Response(KitchenOrderSerializer(kitchen_order).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark order as completed."""
        kitchen_order = self.get_object()
        kitchen_order.complete()
        self._notify_status_change(kitchen_order)
        return Response(KitchenOrderSerializer(kitchen_order).data)
    
    @action(detail=True, methods=['post'])
    def recall(self, request, pk=None):
        """Recall a completed order (undo complete)."""
        kitchen_order = self.get_object()
        if kitchen_order.status != 'completed':
            return Response(
                {'error': 'Can only recall completed orders.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        kitchen_order.status = 'preparing'
        kitchen_order.completed_at = None
        kitchen_order.save(update_fields=['status', 'completed_at'])
        
        # Update main order
        kitchen_order.order.status = 'preparing'
        kitchen_order.order.ready_at = None
        kitchen_order.order.save(update_fields=['status', 'ready_at'])
        
        self._notify_status_change(kitchen_order)
        return Response(KitchenOrderSerializer(kitchen_order).data)
    
    @action(detail=True, methods=['post'])
    def set_priority(self, request, pk=None):
        """Set order priority."""
        kitchen_order = self.get_object()
        priority = request.data.get('priority', 'normal')
        
        if priority not in ['low', 'normal', 'high', 'urgent']:
            return Response(
                {'error': 'Invalid priority value.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        kitchen_order.priority = priority
        kitchen_order.save(update_fields=['priority'])
        
        self._notify_status_change(kitchen_order)
        return Response(KitchenOrderSerializer(kitchen_order).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get kitchen statistics."""
        queryset = self.queryset.filter(
            received_at__date=timezone.now().date()
        )
        
        from django.db.models import Avg, Count
        from django.db.models.functions import Extract
        
        stats = queryset.aggregate(
            total_orders=Count('id'),
            to_cook=Count('id', filter=models.Q(status='to_cook')),
            preparing=Count('id', filter=models.Q(status='preparing')),
            completed=Count('id', filter=models.Q(status='completed')),
        )
        
        # Calculate average preparation time
        completed_orders = queryset.filter(
            status='completed',
            started_at__isnull=False,
            completed_at__isnull=False
        )
        
        avg_prep_time = None
        if completed_orders.exists():
            from django.db.models import F, ExpressionWrapper, DurationField
            durations = completed_orders.annotate(
                duration=ExpressionWrapper(
                    F('completed_at') - F('started_at'),
                    output_field=DurationField()
                )
            )
            total_seconds = sum([d.duration.total_seconds() for d in durations])
            avg_prep_time = int(total_seconds / completed_orders.count() / 60)  # minutes
        
        stats['avg_preparation_time_minutes'] = avg_prep_time
        
        return Response(stats)
    
    def _notify_status_change(self, kitchen_order):
        """Send WebSocket notification for status change."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        # Notify kitchen displays
        async_to_sync(channel_layer.group_send)(
            f'kitchen_{kitchen_order.order.session.terminal_id}',
            {
                'type': 'order_status_change',
                'order_id': str(kitchen_order.order.id),
                'kitchen_order_id': str(kitchen_order.id),
                'order_number': kitchen_order.order.order_number,
                'status': kitchen_order.status,
            }
        )
        
        # Notify POS terminal
        async_to_sync(channel_layer.group_send)(
            f'orders_{kitchen_order.order.session_id}',
            {
                'type': 'order_update',
                'action': 'kitchen_status_change',
                'order_id': str(kitchen_order.order.id),
                'order_number': kitchen_order.order.order_number,
                'status': kitchen_order.order.status,
                'kitchen_status': kitchen_order.status,
            }
        )


class KitchenItemStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for individual item status management.
    """
    queryset = KitchenItemStatus.objects.select_related(
        'kitchen_order', 'order_line', 'order_line__product'
    )
    serializer_class = KitchenItemStatusSerializer
    permission_classes = [IsKitchenUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        kitchen_order_id = self.kwargs.get('kitchen_order_pk')
        if kitchen_order_id:
            queryset = queryset.filter(kitchen_order_id=kitchen_order_id)
        return queryset
    
    @action(detail=True, methods=['post'])
    def start_cooking(self, request, **kwargs):
        """Start cooking this item."""
        item_status = self.get_object()
        item_status.start_cooking()
        return Response(KitchenItemStatusSerializer(item_status).data)
    
    @action(detail=True, methods=['post'])
    def mark_ready(self, request, **kwargs):
        """Mark item as ready."""
        item_status = self.get_object()
        item_status.mark_ready()
        return Response(KitchenItemStatusSerializer(item_status).data)


class KitchenStationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for kitchen stations.
    """
    queryset = KitchenStation.objects.prefetch_related('categories')
    serializer_class = KitchenStationSerializer
    permission_classes = [IsManagerOrAdmin]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsKitchenUser()]
        return super().get_permissions()


# Import for stats query
from django.db import models
