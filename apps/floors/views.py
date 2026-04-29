"""
Floor and table management views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.permissions import IsPOSUser, IsManagerOrAdmin
from .models import Floor, Table, TableReservation
from .serializers import (
    FloorSerializer,
    FloorWithTablesSerializer,
    TableSerializer,
    TableCreateSerializer,
    TableReservationSerializer,
    TableStatusSerializer,
)


class FloorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Floor CRUD operations.
    
    GET /api/v1/floors/
    POST /api/v1/floors/
    GET /api/v1/floors/<id>/
    PUT /api/v1/floors/<id>/
    DELETE /api/v1/floors/<id>/
    """
    queryset = Floor.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'with_tables':
            return FloorWithTablesSerializer
        return FloorSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def with_tables(self, request):
        """Get all floors with their tables."""
        queryset = self.queryset.filter(is_active=True).prefetch_related('tables')
        serializer = FloorWithTablesSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get floor status with table occupancy."""
        floor = self.get_object()
        tables = floor.tables.filter(
            is_active=True,
            is_deleted=False
        ).select_related('current_order')
        
        return Response({
            'floor': FloorSerializer(floor).data,
            'tables': TableStatusSerializer(tables, many=True).data,
            'summary': {
                'total_tables': tables.count(),
                'occupied': tables.filter(is_occupied=True).count(),
                'available': tables.filter(is_occupied=False).count(),
            }
        })


class TableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Table CRUD operations.
    
    GET /api/v1/floors/tables/
    POST /api/v1/floors/tables/
    GET /api/v1/floors/tables/<id>/
    PUT /api/v1/floors/tables/<id>/
    DELETE /api/v1/floors/tables/<id>/
    """
    queryset = Table.objects.filter(is_deleted=False).select_related('floor', 'current_order')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['floor', 'is_active', 'is_occupied']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TableCreateSerializer
        return TableSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_occupied:
            return Response(
                {'error': 'Cannot delete an occupied table.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release a table (mark as available)."""
        table = self.get_object()
        table.release()
        return Response({'status': 'Table released'})
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available tables."""
        floor_id = request.query_params.get('floor')
        min_seats = request.query_params.get('min_seats', 1)
        
        queryset = self.queryset.filter(
            is_active=True,
            is_occupied=False,
            seats__gte=min_seats
        )
        
        if floor_id:
            queryset = queryset.filter(floor_id=floor_id)
        
        serializer = TableSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def order_history(self, request, pk=None):
        """Get order history for a table."""
        table = self.get_object()
        from apps.orders.models import Order
        from apps.orders.serializers import OrderListSerializer
        
        orders = Order.objects.filter(
            table=table,
            is_deleted=False
        ).order_by('-created_at')[:20]
        
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)


class TableReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for table reservations.
    """
    queryset = TableReservation.objects.filter(is_deleted=False).select_related('table')
    serializer_class = TableReservationSerializer
    permission_classes = [IsPOSUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['table', 'status', 'reservation_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(reservation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(reservation_date__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a reservation."""
        reservation = self.get_object()
        reservation.confirm()
        return Response(TableReservationSerializer(reservation).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a reservation."""
        reservation = self.get_object()
        reservation.cancel()
        return Response(TableReservationSerializer(reservation).data)
    
    @action(detail=True, methods=['post'])
    def seat(self, request, pk=None):
        """Seat the customer (start their visit)."""
        reservation = self.get_object()
        
        # Create order for this reservation
        from apps.orders.models import Order
        from apps.terminals.models import POSSession
        
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'error': 'Session ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = POSSession.objects.get(id=session_id, is_active=True)
        except POSSession.DoesNotExist:
            return Response(
                {'error': 'Invalid or inactive session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order = Order.objects.create(
            session=session,
            table=reservation.table,
            created_by=request.user,
            customer_name=reservation.customer_name,
            customer_phone=reservation.customer_phone,
            guests_count=reservation.party_size,
        )
        
        reservation.seat(order)
        
        return Response({
            'reservation': TableReservationSerializer(reservation).data,
            'order_id': str(order.id),
        })
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's reservations."""
        from django.utils import timezone
        today = timezone.now().date()
        
        queryset = self.queryset.filter(
            reservation_date=today
        ).order_by('reservation_time')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
