"""
Payment views and API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models

from apps.core.permissions import IsPOSUser, IsManagerOrAdmin
from apps.core.exceptions import PaymentMethodDisabledError, InsufficientPaymentError
from apps.core.utils import generate_upi_qr
from .models import PaymentMethod, Payment, PaymentRefund, UPIConfiguration
from .serializers import (
    PaymentMethodSerializer,
    PaymentMethodCreateSerializer,
    PaymentSerializer,
    PaymentCreateSerializer,
    UPIQRSerializer,
    PaymentRefundSerializer,
    ConfirmUPIPaymentSerializer,
)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PaymentMethod CRUD.
    
    GET /api/v1/payments/methods/
    POST /api/v1/payments/methods/
    GET /api/v1/payments/methods/<id>/
    PUT /api/v1/payments/methods/<id>/
    DELETE /api/v1/payments/methods/<id>/
    """
    queryset = PaymentMethod.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentMethodCreateSerializer
        return PaymentMethodSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def enabled(self, request):
        """Get only enabled payment methods."""
        queryset = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a payment method."""
        payment_method = self.get_object()
        payment_method.enable()
        return Response({'status': 'Payment method enabled'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a payment method."""
        payment_method = self.get_object()
        payment_method.disable()
        return Response({'status': 'Payment method disabled'})
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a payment method as default."""
        payment_method = self.get_object()
        PaymentMethod.objects.filter(is_default=True).update(is_default=False)
        payment_method.is_default = True
        payment_method.save(update_fields=['is_default'])
        return Response({'status': 'Payment method set as default'})


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment operations.
    
    GET /api/v1/payments/
    POST /api/v1/payments/
    GET /api/v1/payments/<id>/
    """
    queryset = Payment.objects.select_related('payment_method', 'order', 'processed_by')
    serializer_class = PaymentSerializer
    permission_classes = [IsPOSUser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a payment and return bill generation info if order is fully paid."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        
        response_data = PaymentSerializer(payment).data
        
        # Add bill generation URL if order is fully paid
        if payment.order.status == 'paid':
            from django.urls import reverse
            response_data['bill_url'] = reverse('orders:order-generate-bill', kwargs={'pk': payment.order.id})
            response_data['order_status'] = 'paid'
            response_data['message'] = 'Payment successful. Order is fully paid.'
        
        headers = self.get_success_headers(response_data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by order
        order_id = self.request.query_params.get('order')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark payment as completed."""
        payment = self.get_object()
        payment.complete()
        
        # Check if order is fully paid
        self._check_order_payment_status(payment.order)
        
        return Response(PaymentSerializer(payment).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending payment."""
        payment = self.get_object()
        if payment.status != 'pending':
            return Response(
                {'error': 'Can only cancel pending payments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        payment.status = 'cancelled'
        payment.save(update_fields=['status'])
        return Response(PaymentSerializer(payment).data)
    
    def _check_order_payment_status(self, order):
        """Check if order is fully paid and update status."""
        total_paid = order.payments.filter(
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        if total_paid >= order.total_amount:
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at'])


class GenerateUPIQRView(APIView):
    """
    Generate UPI QR code for payment.
    
    POST /api/v1/payments/upi/generate-qr/
    """
    permission_classes = [IsPOSUser]
    
    def post(self, request):
        serializer = UPIQRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get UPI configuration
        try:
            upi_method = PaymentMethod.objects.get(method_type='upi', is_active=True)
            upi_config = upi_method.upi_config
            upi_id = upi_config.upi_id
            merchant_name = upi_config.merchant_name
        except (PaymentMethod.DoesNotExist, UPIConfiguration.DoesNotExist):
            upi_id = serializer.validated_data.get('upi_id')
            merchant_name = serializer.validated_data.get('merchant_name')
            if not upi_id:
                return Response(
                    {'error': 'UPI payment method not configured'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Store payment reference in cache for status checking
        payment_ref = serializer.validated_data.get('payment_ref')
        if payment_ref:
            from django.core.cache import cache
            cache.set(f'upi_payment_{payment_ref}', {
                'amount': float(serializer.validated_data['amount']),
                'status': 'pending',
                'created_at': timezone.now().isoformat(),
            }, timeout=1800)  # 30 minutes timeout
        
        qr_data = generate_upi_qr(
            amount=serializer.validated_data['amount'],
            upi_id=upi_id,
            merchant_name=merchant_name,
            order_id=serializer.validated_data.get('order_id'),
        )
        
        if payment_ref:
            qr_data['payment_ref'] = payment_ref
        
        return Response(qr_data)


class CheckUPIPaymentStatusView(APIView):
    """
    Check UPI payment status by reference.
    
    GET /api/v1/payments/upi/check-status/?ref=<payment_ref>
    """
    permission_classes = [IsPOSUser]
    
    def get(self, request):
        payment_ref = request.query_params.get('ref')
        
        if not payment_ref:
            return Response(
                {'error': 'Payment reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.core.cache import cache
        payment_data = cache.get(f'upi_payment_{payment_ref}')
        
        if not payment_data:
            return Response({
                'status': 'not_found',
                'message': 'Payment reference not found or expired'
            })
        
        return Response({
            'status': payment_data.get('status', 'pending'),
            'transaction_id': payment_data.get('transaction_id'),
            'amount': payment_data.get('amount'),
        })


class ConfirmUPIPaymentWebhookView(APIView):
    """
    Webhook endpoint for UPI payment confirmation from payment gateway.
    This can be called by external payment notification services.
    
    POST /api/v1/payments/upi/webhook/
    """
    permission_classes = []  # No authentication for webhooks
    
    def post(self, request):
        payment_ref = request.data.get('payment_ref')
        transaction_id = request.data.get('transaction_id')
        status_code = request.data.get('status', 'success')
        
        if not payment_ref:
            return Response({'error': 'Payment reference required'}, status=400)
        
        from django.core.cache import cache
        payment_data = cache.get(f'upi_payment_{payment_ref}')
        
        if payment_data:
            payment_data['status'] = 'completed' if status_code == 'success' else 'failed'
            payment_data['transaction_id'] = transaction_id
            cache.set(f'upi_payment_{payment_ref}', payment_data, timeout=1800)
            
            return Response({'status': 'ok'})
        
        return Response({'error': 'Payment not found'}, status=404)


class ConfirmUPIPaymentView(APIView):
    """
    Confirm UPI payment after QR scan.
    
    POST /api/v1/payments/upi/confirm/
    """
    permission_classes = [IsPOSUser]
    
    def post(self, request):
        serializer = ConfirmUPIPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.orders.models import Order
        
        order = get_object_or_404(Order, id=serializer.validated_data['order_id'])
        upi_method = get_object_or_404(PaymentMethod, method_type='upi', is_active=True)
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            payment_method=upi_method,
            amount=order.total_amount,
            amount_received=order.total_amount,
            status='completed',
            upi_transaction_id=serializer.validated_data['upi_transaction_id'],
            processed_by=request.user,
            processed_at=timezone.now(),
        )
        
        # Update order status
        order.status = 'paid'
        order.paid_at = timezone.now()
        order.save(update_fields=['status', 'paid_at'])
        
        # Send WebSocket notification
        self._notify_payment_completed(order)
        
        return Response({
            'status': 'success',
            'payment': PaymentSerializer(payment).data,
        })
    
    def _notify_payment_completed(self, order):
        """Send WebSocket notification for payment completion."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'customer_{order.id}',
            {
                'type': 'payment_status',
                'status': 'paid',
                'order_id': str(order.id),
            }
        )


class PaymentRefundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payment refunds.
    """
    queryset = PaymentRefund.objects.select_related('payment', 'processed_by')
    serializer_class = PaymentRefundSerializer
    permission_classes = [IsManagerOrAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        payment_id = self.request.query_params.get('payment')
        if payment_id:
            queryset = queryset.filter(payment_id=payment_id)
        
        return queryset
