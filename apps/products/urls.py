"""
URL patterns for product management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductAttributeViewSet,
    ProductAttributeValueViewSet,
    ProductVariantViewSet,
    ProductModifierViewSet,
    ComboProductViewSet,
)

app_name = 'products'

# Main router
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'', ProductViewSet, basename='product')
router.register(r'attributes', ProductAttributeViewSet, basename='attribute')
router.register(r'modifiers', ProductModifierViewSet, basename='modifier')

# Nested routers for variants
products_router = routers.NestedDefaultRouter(router, r'', lookup='product')
products_router.register(r'variants', ProductVariantViewSet, basename='product-variant')
products_router.register(r'combos', ComboProductViewSet, basename='product-combo')

# Nested router for attribute values
attributes_router = routers.NestedDefaultRouter(router, r'attributes', lookup='attribute')
attributes_router.register(r'values', ProductAttributeValueViewSet, basename='attribute-value')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(products_router.urls)),
    path('', include(attributes_router.urls)),
]
