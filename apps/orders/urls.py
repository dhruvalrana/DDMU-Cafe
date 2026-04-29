"""
URL patterns for order management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import OrderViewSet, OrderLineViewSet

app_name = 'orders'

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='order')

# Nested router for order lines
orders_router = routers.NestedDefaultRouter(router, r'', lookup='order')
orders_router.register(r'lines', OrderLineViewSet, basename='order-line')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(orders_router.urls)),
]
