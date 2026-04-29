"""
Customer Display views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db import models
from django.utils import timezone

from apps.core.permissions import IsManagerOrAdmin
from .models import CustomerDisplayConfig, CustomerPromotion
from .serializers import (
    CustomerDisplayConfigSerializer,
    CustomerPromotionSerializer,
    CustomerOrderSerializer,
    CustomerDisplayStateSerializer,
)


class CustomerDisplayConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for customer display configuration.
    """
    queryset = CustomerDisplayConfig.objects.select_related('terminal')
    serializer_class = CustomerDisplayConfigSerializer
    permission_classes = [IsManagerOrAdmin]


class CustomerPromotionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing promotions.
    """
    queryset = CustomerPromotion.objects.all()
    serializer_class = CustomerPromotionSerializer
    permission_classes = [IsManagerOrAdmin]
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active promotions for display."""
        now = timezone.now()
        promotions = self.queryset.filter(
            is_active=True
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).order_by('display_order')
        
        serializer = CustomerPromotionSerializer(promotions, many=True)
        return Response(serializer.data)


class CustomerDisplayView(APIView):
    """
    Customer-facing display endpoint.
    Provides real-time order information for display screens.
    """
    permission_classes = [AllowAny]  # Public endpoint for display screens
    
    def get(self, request, terminal_id):
        """Get current display state for a terminal."""
        from apps.terminals.models import POSSession
        from apps.orders.models import Order
        
        # Get active session for terminal
        try:
            session = POSSession.objects.get(
                terminal_id=terminal_id,
                is_active=True,
                status='open'
            )
        except POSSession.DoesNotExist:
            return Response({
                'state': 'idle',
                'message': 'Terminal not active',
            })
        
        # Get current active order
        current_order = Order.objects.filter(
            session=session,
            status__in=['draft', 'sent_to_kitchen', 'preparing', 'ready']
        ).order_by('-created_at').first()
        
        if current_order:
            if current_order.status == 'draft':
                state = 'order'
            elif current_order.status in ['sent_to_kitchen', 'preparing']:
                state = 'order'
            elif current_order.status == 'ready':
                state = 'complete'
            else:
                state = 'order'
            
            return Response({
                'state': state,
                'order': CustomerOrderSerializer(current_order).data,
            })
        
        # No active order - show idle
        try:
            config = CustomerDisplayConfig.objects.get(terminal_id=terminal_id)
            return Response({
                'state': 'idle',
                'message': config.idle_message,
            })
        except CustomerDisplayConfig.DoesNotExist:
            return Response({
                'state': 'idle',
                'message': 'Welcome!',
            })


# Import for QuerySet
from django.db import models
