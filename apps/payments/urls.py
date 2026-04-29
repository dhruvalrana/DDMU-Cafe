"""
URL patterns for payment management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentMethodViewSet,
    PaymentViewSet,
    GenerateUPIQRView,
    CheckUPIPaymentStatusView,
    ConfirmUPIPaymentView,
    ConfirmUPIPaymentWebhookView,
    PaymentRefundViewSet,
)

app_name = 'payments'

router = DefaultRouter()
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'refunds', PaymentRefundViewSet, basename='payment-refund')
router.register(r'', PaymentViewSet, basename='payment')

urlpatterns = [
    path('upi/generate-qr/', GenerateUPIQRView.as_view(), name='upi-generate-qr'),
    path('upi/check-status/', CheckUPIPaymentStatusView.as_view(), name='upi-check-status'),
    path('upi/confirm/', ConfirmUPIPaymentView.as_view(), name='upi-confirm'),
    path('upi/webhook/', ConfirmUPIPaymentWebhookView.as_view(), name='upi-webhook'),
    path('', include(router.urls)),
]
