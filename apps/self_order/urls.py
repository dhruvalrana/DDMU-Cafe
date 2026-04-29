"""
URL patterns for Self-Order System.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SelfOrderSessionViewSet,
    SelfOrderQRCodeViewSet,
    InitiateSessionView,
    MenuView,
    CartView,
    CartItemView,
    ClearCartView,
    SubmitOrderView,
    OrderStatusView,
)

app_name = 'self_order'

router = DefaultRouter()
router.register(r'sessions', SelfOrderSessionViewSet, basename='session')
router.register(r'qr-codes', SelfOrderQRCodeViewSet, basename='qr-code')

urlpatterns = [
    # Admin endpoints
    path('', include(router.urls)),
    
    # Public self-order endpoints
    path('initiate/', InitiateSessionView.as_view(), name='initiate'),
    path('menu/', MenuView.as_view(), name='menu'),
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/item/<uuid:item_id>/', CartItemView.as_view(), name='cart-item'),
    path('cart/clear/', ClearCartView.as_view(), name='cart-clear'),
    path('submit/', SubmitOrderView.as_view(), name='submit'),
    path('status/<uuid:order_id>/', OrderStatusView.as_view(), name='order-status'),
]
