"""
Order management views and API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.http import HttpResponse

from apps.core.permissions import IsPOSUser, IsManagerOrAdmin
from apps.core.exceptions import OrderNotEditableError
from apps.core.utils import generate_bill_pdf
from .models import Order, OrderLine, OrderDiscount
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderLineSerializer,
    OrderLineCreateSerializer,
    OrderDiscountSerializer,
    ApplyDiscountSerializer,
    OrderStatusUpdateSerializer,
)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order CRUD operations.
    
    GET /api/v1/orders/
    POST /api/v1/orders/
    GET /api/v1/orders/<id>/
    PUT /api/v1/orders/<id>/
    DELETE /api/v1/orders/<id>/
    """
    queryset = Order.objects.filter(is_deleted=False).select_related(
        'session', 'table', 'created_by', 'served_by'
    ).prefetch_related('lines', 'payments', 'discounts')
    permission_classes = [IsPOSUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['session', 'table', 'status', 'order_type']
    search_fields = ['order_number', 'customer_name', 'customer_phone']
    ordering_fields = ['created_at', 'total_amount', 'order_number']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(created_at__date=date)
        
        # Filter by created_by
        user_id = self.request.query_params.get('created_by')
        if user_id:
            queryset = queryset.filter(created_by_id=user_id)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete order (only if allowed)."""
        order = self.get_object()
        if not order.can_be_cancelled:
            return Response(
                {'error': 'This order cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.cancel('Deleted by user')
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def send_to_kitchen(self, request, pk=None):
        """Send order to kitchen."""
        order = self.get_object()
        
        if order.status != 'draft':
            return Response(
                {'error': 'Order has already been sent to kitchen.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.lines.count() == 0:
            return Response(
                {'error': 'Cannot send empty order to kitchen.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.send_to_kitchen()
        
        # Mark all lines as sent
        order.lines.update(is_sent_to_kitchen=True)
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        """Mark order as ready for serving."""
        order = self.get_object()
        order.mark_ready()
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def mark_served(self, request, pk=None):
        """Mark order as served."""
        order = self.get_object()
        order.mark_served(served_by=request.user)
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel the order."""
        order = self.get_object()
        
        if not order.can_be_cancelled:
            return Response(
                {'error': 'This order cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        order.cancel(reason)
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def add_line(self, request, pk=None):
        """Add a line item to the order."""
        order = self.get_object()
        
        if not order.is_editable:
            raise OrderNotEditableError()
        
        serializer = OrderLineCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(order=order)
        
        order.calculate_totals()
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def apply_discount(self, request, pk=None):
        """Apply discount to order."""
        order = self.get_object()
        
        if not request.user.can_apply_discounts:
            return Response(
                {'error': 'You do not have permission to apply discounts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ApplyDiscountSerializer(
            data=request.data,
            context={'request': request, 'order': order}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def remove_discount(self, request, pk=None):
        """Remove all discounts from order."""
        order = self.get_object()
        
        if not request.user.can_apply_discounts:
            return Response(
                {'error': 'You do not have permission to modify discounts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order.discounts.all().delete()
        order.discount_amount = 0
        order.discount_percent = 0
        order.calculate_totals()
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def add_tip(self, request, pk=None):
        """Add tip to order."""
        order = self.get_object()
        tip_amount = request.data.get('tip_amount', 0)
        
        order.tip_amount = tip_amount
        order.calculate_totals()
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active (unpaid) orders."""
        queryset = self.queryset.exclude(
            status__in=['paid', 'cancelled', 'refunded']
        )
        
        session_id = request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_table(self, request):
        """Get order by table."""
        table_id = request.query_params.get('table')
        if not table_id:
            return Response(
                {'error': 'Table ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order = self.queryset.filter(
            table_id=table_id,
            status__in=['draft', 'sent_to_kitchen', 'preparing', 'ready', 'served']
        ).first()
        
        if not order:
            return Response(
                {'error': 'No active order for this table.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(OrderDetailSerializer(order).data)
    
    @action(detail=True, methods=['get'])
    def generate_bill(self, request, pk=None):
        """Generate and download bill/receipt for the order."""
        order = self.get_object()
        
        # Check if order has been paid
        if order.status != 'paid':
            return Response(
                {'error': 'Bill can only be generated for paid orders.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pdf_content = generate_bill_pdf(order)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="bill_{order.order_number}.pdf"'
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to generate bill: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def view_bill(self, request, pk=None):
        """View bill/receipt for the order in browser."""
        order = self.get_object()
        
        try:
            pdf_content = generate_bill_pdf(order)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="bill_{order.order_number}.pdf"'
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to generate bill: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderLineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for order line operations.
    """
    queryset = OrderLine.objects.filter(is_deleted=False)
    permission_classes = [IsPOSUser]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return OrderLineCreateSerializer
        return OrderLineSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        order_id = self.kwargs.get('order_pk')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset
    
    def perform_create(self, serializer):
        order_id = self.kwargs.get('order_pk')
        order = Order.objects.get(id=order_id)
        
        if not order.is_editable:
            raise OrderNotEditableError()
        
        serializer.save(order=order)
    
    def destroy(self, request, *args, **kwargs):
        line = self.get_object()
        
        if not line.order.is_editable:
            raise OrderNotEditableError()
        
        line.soft_delete()
        line.order.calculate_totals()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def update_quantity(self, request, **kwargs):
        """Update line quantity."""
        line = self.get_object()
        
        if not line.order.is_editable:
            raise OrderNotEditableError()
        
        quantity = request.data.get('quantity')
        if quantity is None or float(quantity) <= 0:
            return Response(
                {'error': 'Valid quantity is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        line.update_quantity(quantity)
        return Response(OrderLineSerializer(line).data)
