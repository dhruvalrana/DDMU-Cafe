"""
URL patterns for Kitchen Display System.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import KitchenOrderViewSet, KitchenItemStatusViewSet, KitchenStationViewSet

app_name = 'kitchen'

router = DefaultRouter()
router.register(r'orders', KitchenOrderViewSet, basename='kitchen-order')
router.register(r'stations', KitchenStationViewSet, basename='kitchen-station')

# Nested router for item statuses
orders_router = routers.NestedDefaultRouter(router, r'orders', lookup='kitchen_order')
orders_router.register(r'items', KitchenItemStatusViewSet, basename='kitchen-item')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(orders_router.urls)),
]
