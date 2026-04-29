"""
Self-Order System views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.core.permissions import IsManagerOrAdmin
from .models import (
    SelfOrderSession, SelfOrderCart, SelfOrderCartItem,
    SelfOrderCartItemModifier, SelfOrderQRCode
)
from .serializers import (
    SelfOrderSessionSerializer,
    SelfOrderCartSerializer,
    SelfOrderCartItemSerializer,
    InitiateSessionSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    SubmitOrderSerializer,
    SelfOrderQRCodeSerializer,
)


class SelfOrderSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for self-order sessions (read-only for managers).
    """
    queryset = SelfOrderSession.objects.select_related('table', 'terminal')
    serializer_class = SelfOrderSessionSerializer
    permission_classes = [IsManagerOrAdmin]


class SelfOrderQRCodeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing QR codes.
    """
    queryset = SelfOrderQRCode.objects.select_related('table', 'table__floor')
    serializer_class = SelfOrderQRCodeSerializer
    permission_classes = [IsManagerOrAdmin]
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate QR code."""
        qr_code = self.get_object()
        import secrets
        qr_code.code = secrets.token_urlsafe(24)
        qr_code.save(update_fields=['code'])
        return Response(SelfOrderQRCodeSerializer(qr_code, context={'request': request}).data)
    
    @action(detail=True, methods=['get'])
    def image(self, request, pk=None):
        """Get QR code image."""
        qr_code = self.get_object()
        
        import qrcode
        import io
        from django.http import HttpResponse
        from django.conf import settings
        
        base_url = getattr(settings, 'SELF_ORDER_URL', request.build_absolute_uri('/self-order/'))
        url = f"{base_url}?code={qr_code.code}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return HttpResponse(buffer, content_type='image/png')


class SelfOrderAPIView(APIView):
    """
    Public API for self-ordering.
    Token-based authentication via query parameter or header.
    """
    permission_classes = [AllowAny]
    
    def get_session(self, request):
        """Get session from token."""
        token = request.query_params.get('token') or request.headers.get('X-Self-Order-Token')
        if not token:
            return None
        try:
            session = SelfOrderSession.objects.get(token=token)
            if session.is_valid:
                return session
        except SelfOrderSession.DoesNotExist:
            pass
        return None


class InitiateSessionView(SelfOrderAPIView):
    """
    Initiate a new self-order session.
    
    POST /api/v1/self-order/initiate/
    """
    
    def post(self, request):
        serializer = InitiateSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Find table from QR code or ID
        table = None
        if data.get('qr_code'):
            try:
                qr_code = SelfOrderQRCode.objects.get(
                    code=data['qr_code'],
                    is_active=True
                )
                table = qr_code.table
                qr_code.record_scan()
            except SelfOrderQRCode.DoesNotExist:
                return Response(
                    {'error': 'Invalid QR code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif data.get('table_id'):
            from apps.floors.models import Table
            table = get_object_or_404(Table, id=data['table_id'])
        
        # Get active POS session for the terminal
        from apps.terminals.models import POSSession
        pos_session = POSSession.objects.filter(
            is_active=True,
            status='open',
            terminal__is_active=True
        ).first()
        
        if not pos_session:
            return Response(
                {'error': 'No active POS session available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create self-order session
        session = SelfOrderSession.objects.create(
            session_type=data.get('session_type', 'table_qr'),
            table=table,
            terminal=pos_session.terminal,
            pos_session=pos_session,
            customer_name=data.get('customer_name', ''),
            customer_phone=data.get('customer_phone', ''),
        )
        
        # Create cart
        SelfOrderCart.objects.create(session=session)
        
        return Response(
            SelfOrderSessionSerializer(session).data,
            status=status.HTTP_201_CREATED
        )


class MenuView(SelfOrderAPIView):
    """
    Get menu for self-ordering.
    
    GET /api/v1/self-order/menu/
    """
    
    def get(self, request):
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        from apps.products.models import Category, Product
        from apps.products.serializers import CategorySerializer, ProductPOSSerializer
        
        # Get active categories and products
        categories = Category.objects.filter(
            is_active=True,
            is_available_for_self_order=True
        ).order_by('display_order')
        
        products = Product.objects.filter(
            is_active=True,
            is_available_for_self_order=True,
            is_deleted=False
        ).select_related('category').prefetch_related('variants')
        
        return Response({
            'categories': CategorySerializer(categories, many=True).data,
            'products': ProductPOSSerializer(products, many=True).data,
        })


class CartView(SelfOrderAPIView):
    """
    Cart operations.
    
    GET /api/v1/self-order/cart/
    POST /api/v1/self-order/cart/add/
    PUT /api/v1/self-order/cart/item/<id>/
    DELETE /api/v1/self-order/cart/item/<id>/
    DELETE /api/v1/self-order/cart/clear/
    """
    
    def get(self, request):
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        cart = session.cart
        return Response(SelfOrderCartSerializer(cart).data)
    
    def post(self, request):
        """Add item to cart."""
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        from apps.products.models import Product, ProductVariant, ProductModifier
        
        # Get product
        try:
            product = Product.objects.get(
                id=data['product_id'],
                is_active=True,
                is_deleted=False
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get variant if specified
        variant = None
        if data.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(
                    id=data['variant_id'],
                    product=product
                )
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': 'Variant not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create cart item
        cart_item = SelfOrderCartItem.objects.create(
            cart=session.cart,
            product=product,
            variant=variant,
            quantity=data.get('quantity', 1),
            notes=data.get('notes', ''),
        )
        
        # Add modifiers
        for modifier_id in data.get('modifier_ids', []):
            try:
                modifier = ProductModifier.objects.get(id=modifier_id)
                SelfOrderCartItemModifier.objects.create(
                    cart_item=cart_item,
                    modifier=modifier
                )
            except ProductModifier.DoesNotExist:
                pass
        
        return Response(
            SelfOrderCartSerializer(session.cart).data,
            status=status.HTTP_201_CREATED
        )


class CartItemView(SelfOrderAPIView):
    """
    Cart item operations.
    """
    
    def put(self, request, item_id):
        """Update cart item."""
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            cart_item = SelfOrderCartItem.objects.get(
                id=item_id,
                cart=session.cart
            )
        except SelfOrderCartItem.DoesNotExist:
            return Response(
                {'error': 'Item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        if data['quantity'] == 0:
            cart_item.delete()
        else:
            cart_item.quantity = data['quantity']
            if 'notes' in data:
                cart_item.notes = data['notes']
            cart_item.save()
        
        return Response(SelfOrderCartSerializer(session.cart).data)
    
    def delete(self, request, item_id):
        """Remove item from cart."""
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            cart_item = SelfOrderCartItem.objects.get(
                id=item_id,
                cart=session.cart
            )
            cart_item.delete()
        except SelfOrderCartItem.DoesNotExist:
            pass
        
        return Response(SelfOrderCartSerializer(session.cart).data)


class ClearCartView(SelfOrderAPIView):
    """
    Clear all items from cart.
    """
    
    def delete(self, request):
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        session.cart.clear()
        return Response({'message': 'Cart cleared'})


class SubmitOrderView(SelfOrderAPIView):
    """
    Submit order from cart.
    
    POST /api/v1/self-order/submit/
    """
    
    def post(self, request):
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        cart = session.cart
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SubmitOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Create order
        from apps.orders.models import Order, OrderLine, OrderLineModifier
        from apps.core.utils import generate_order_number
        
        order = Order.objects.create(
            session=session.pos_session,
            table=session.table,
            order_type='self_order',
            order_number=generate_order_number(),
            customer_name=data.get('customer_name') or session.customer_name,
            customer_phone=data.get('customer_phone') or session.customer_phone,
            kitchen_notes=data.get('notes', ''),
            status='sent_to_kitchen',
        )
        
        # Create order lines from cart
        for cart_item in cart.items.all():
            order_line = OrderLine.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price + (cart_item.variant.extra_price if cart_item.variant else 0),
                notes=cart_item.notes,
            )
            
            # Add modifiers
            for cart_modifier in cart_item.modifiers.all():
                OrderLineModifier.objects.create(
                    order_line=order_line,
                    modifier=cart_modifier.modifier,
                    price=cart_modifier.modifier.price,
                )
        
        # Calculate totals
        order.calculate_totals()
        
        # Create kitchen order
        from apps.kitchen.models import KitchenOrder
        KitchenOrder.objects.create(order=order, priority='normal')
        
        # Clear cart
        cart.clear()
        
        # Send WebSocket notification
        self._notify_new_order(order)
        
        from apps.orders.serializers import OrderSerializer
        return Response({
            'message': 'Order submitted successfully',
            'order': OrderSerializer(order).data,
        }, status=status.HTTP_201_CREATED)
    
    def _notify_new_order(self, order):
        """Send WebSocket notification for new order."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        # Notify kitchen
        async_to_sync(channel_layer.group_send)(
            f'kitchen_{order.session.terminal_id}',
            {
                'type': 'new_order',
                'order_id': str(order.id),
                'order_number': order.order_number,
                'table': order.table.display_name if order.table else None,
            }
        )
        
        # Notify POS
        async_to_sync(channel_layer.group_send)(
            f'orders_{order.session_id}',
            {
                'type': 'order_update',
                'action': 'new_self_order',
                'order_id': str(order.id),
                'order_number': order.order_number,
            }
        )


class OrderStatusView(SelfOrderAPIView):
    """
    Check order status.
    
    GET /api/v1/self-order/status/<order_id>/
    """
    
    def get(self, request, order_id):
        session = self.get_session(request)
        if not session:
            return Response(
                {'error': 'Invalid or expired session'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        from apps.orders.models import Order
        
        try:
            order = Order.objects.get(
                id=order_id,
                session=session.pos_session
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total': str(order.total),
            'created_at': order.created_at,
        })
