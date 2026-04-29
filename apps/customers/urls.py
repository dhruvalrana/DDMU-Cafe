"""
URL patterns for Customer Display.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerDisplayConfigViewSet, CustomerPromotionViewSet, CustomerDisplayView

app_name = 'customers'

router = DefaultRouter()
router.register(r'config', CustomerDisplayConfigViewSet, basename='display-config')
router.register(r'promotions', CustomerPromotionViewSet, basename='promotion')

urlpatterns = [
    path('', include(router.urls)),
    path('display/<uuid:terminal_id>/', CustomerDisplayView.as_view(), name='display-state'),
]
