"""
POS Terminal and Session views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Avg
from decimal import Decimal

from apps.core.permissions import IsPOSUser, IsManagerOrAdmin
from apps.core.exceptions import SessionNotActiveError, SessionAlreadyOpenError
from .models import POSTerminal, POSSession, CashMovement
from .serializers import (
    POSTerminalSerializer,
    POSTerminalCreateSerializer,
    POSSessionSerializer,
    POSSessionDetailSerializer,
    CashMovementSerializer,
    OpenSessionSerializer,
    CloseSessionSerializer,
)


class POSTerminalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for POSTerminal CRUD.
    
    GET /api/v1/terminals/
    POST /api/v1/terminals/
    GET /api/v1/terminals/<id>/
    PUT /api/v1/terminals/<id>/
    DELETE /api/v1/terminals/<id>/
    """
    queryset = POSTerminal.objects.filter(is_deleted=False).select_related('floor')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return POSTerminalCreateSerializer
        return POSTerminalSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.has_active_session:
            return Response(
                {'error': 'Cannot delete terminal with active session.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def current_session(self, request, pk=None):
        """Get current active session for terminal."""
        terminal = self.get_object()
        session = terminal.current_session
        
        if not session:
            return Response(
                {'error': 'No active session'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = POSSessionDetailSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def session_history(self, request, pk=None):
        """Get session history for terminal."""
        terminal = self.get_object()
        sessions = terminal.sessions.filter(is_deleted=False).order_by('-opening_time')[:50]
        serializer = POSSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class POSSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for POS Session management.
    
    GET /api/v1/terminals/sessions/
    POST /api/v1/terminals/sessions/open/
    POST /api/v1/terminals/sessions/<id>/close/
    """
    queryset = POSSession.objects.select_related(
        'terminal', 'responsible_user'
    ).filter(is_deleted=False)
    permission_classes = [IsPOSUser]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return POSSessionDetailSerializer
        return POSSessionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by terminal
        terminal_id = self.request.query_params.get('terminal')
        if terminal_id:
            queryset = queryset.filter(terminal_id=terminal_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter active only
        active_only = self.request.query_params.get('active')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def open(self, request):
        """Open a new POS session."""
        serializer = OpenSessionSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        
        return Response(
            POSSessionDetailSerializer(session).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a POS session."""
        session = self.get_object()
        
        serializer = CloseSessionSerializer(
            data=request.data,
            context={'request': request, 'session': session}
        )
        serializer.is_valid(raise_exception=True)
        
        session.close(
            closing_balance=serializer.validated_data['closing_balance'],
            notes=serializer.validated_data.get('closing_notes', '')
        )
        
        return Response(POSSessionDetailSerializer(session).data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get detailed session summary."""
        session = self.get_object()
        
        # Calculate payment breakdown
        from apps.payments.models import Payment
        payment_breakdown = Payment.objects.filter(
            order__session=session,
            status='completed'
        ).values('payment_method__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Get top products
        from apps.orders.models import OrderLine
        top_products = OrderLine.objects.filter(
            order__session=session,
            order__is_deleted=False
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('line_total')
        ).order_by('-total_revenue')[:10]
        
        # Calculate duration
        duration_hours = Decimal('0.00')
        if session.closing_time:
            duration = session.closing_time - session.opening_time
            duration_hours = Decimal(str(duration.total_seconds() / 3600)).quantize(Decimal('0.01'))
        
        # Calculate average order value
        avg_order_value = Decimal('0.00')
        if session.order_count > 0:
            avg_order_value = session.total_sales / session.order_count
        
        summary_data = {
            'session_id': str(session.id),
            'session_name': session.name,
            'terminal_name': session.terminal.name,
            'responsible_user': session.responsible_user.get_full_name(),
            'opening_time': session.opening_time,
            'closing_time': session.closing_time,
            'duration_hours': duration_hours,
            'opening_balance': session.opening_balance,
            'closing_balance': session.closing_balance or Decimal('0.00'),
            'expected_closing_balance': session.expected_closing_balance or Decimal('0.00'),
            'cash_difference': session.cash_difference or Decimal('0.00'),
            'total_sales': session.total_sales,
            'order_count': session.order_count,
            'average_order_value': avg_order_value,
            'payment_breakdown': list(payment_breakdown),
            'top_products': list(top_products),
        }
        
        return Response(summary_data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active sessions."""
        sessions = self.queryset.filter(is_active=True)
        serializer = POSSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class CashMovementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for cash movements within a session.
    """
    queryset = CashMovement.objects.select_related('session', 'performed_by')
    serializer_class = CashMovementSerializer
    permission_classes = [IsPOSUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        session_id = self.kwargs.get('session_pk') or self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset
    
    def perform_create(self, serializer):
        session_id = self.kwargs.get('session_pk') or self.request.data.get('session')
        session = get_object_or_404(POSSession, id=session_id, is_active=True)
        serializer.save(
            session=session,
            performed_by=self.request.user
        )
