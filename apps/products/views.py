"""
Product management views and API endpoints.
"""

from django.db import models
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsPOSUser, IsManagerOrAdmin
from .models import (
    Category,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariant,
    ComboProduct,
    ProductModifier,
)
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    ProductPOSSerializer,
    ProductAttributeSerializer,
    ProductAttributeCreateSerializer,
    ProductAttributeValueSerializer,
    ProductVariantSerializer,
    ProductVariantCreateSerializer,
    ComboProductSerializer,
    ProductModifierSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD operations.
    
    GET /api/v1/products/categories/
    POST /api/v1/products/categories/
    GET /api/v1/products/categories/<id>/
    PUT /api/v1/products/categories/<id>/
    DELETE /api/v1/products/categories/<id>/
    """
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'display_order', 'created_at']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete category."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories as a tree structure."""
        root_categories = self.queryset.filter(parent__isnull=True, is_active=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product CRUD operations.
    
    GET /api/v1/products/
    POST /api/v1/products/
    GET /api/v1/products/<id>/
    PUT /api/v1/products/<id>/
    DELETE /api/v1/products/<id>/
    """
    queryset = Product.objects.filter(is_deleted=False).select_related('category')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active', 'is_available_for_pos', 'has_variants', 'is_combo']
    search_fields = ['name', 'description', 'internal_reference', 'barcode']
    ordering_fields = ['name', 'price', 'display_order', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'create':
            return ProductCreateSerializer
        elif self.action == 'pos_products':
            return ProductPOSSerializer
        return ProductDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete product."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a product."""
        product = self.get_object()
        product.enable()
        return Response({'status': 'Product enabled'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a product."""
        product = self.get_object()
        product.disable()
        return Response({'status': 'Product disabled'})
    
    @action(detail=False, methods=['get'])
    def pos_products(self, request):
        """
        Get products optimized for POS display.
        Only returns active, POS-available products.
        """
        queryset = self.queryset.filter(
            is_active=True,
            is_available_for_pos=True
        ).prefetch_related('variants', 'modifiers')
        
        # Optional category filter
        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        serializer = ProductPOSSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        """Look up product by barcode."""
        barcode = request.query_params.get('barcode')
        if not barcode:
            return Response(
                {'error': 'Barcode parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = self.queryset.get(barcode=barcode, is_active=True)
            serializer = ProductDetailSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            # Try finding variant by barcode
            try:
                variant = ProductVariant.objects.select_related('product').get(
                    barcode=barcode,
                    is_active=True
                )
                return Response({
                    'product': ProductDetailSerializer(variant.product).data,
                    'variant': ProductVariantSerializer(variant).data,
                })
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': 'Product not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock."""
        queryset = self.queryset.filter(
            track_inventory=True,
            stock_quantity__lte=models.F('low_stock_threshold')
        )
        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)


class ProductAttributeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductAttribute CRUD.
    
    GET /api/v1/products/attributes/
    POST /api/v1/products/attributes/
    """
    queryset = ProductAttribute.objects.filter(is_deleted=False)
    permission_classes = [IsManagerOrAdmin]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductAttributeCreateSerializer
        return ProductAttributeSerializer


class ProductAttributeValueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductAttributeValue CRUD.
    """
    queryset = ProductAttributeValue.objects.filter(is_deleted=False)
    serializer_class = ProductAttributeValueSerializer
    permission_classes = [IsManagerOrAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        attribute_id = self.kwargs.get('attribute_pk')
        if attribute_id:
            queryset = queryset.filter(attribute_id=attribute_id)
        return queryset


class ProductVariantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductVariant CRUD.
    
    GET /api/v1/products/<product_id>/variants/
    POST /api/v1/products/<product_id>/variants/
    """
    queryset = ProductVariant.objects.filter(is_deleted=False)
    permission_classes = [IsManagerOrAdmin]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductVariantCreateSerializer
        return ProductVariantSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.kwargs.get('product_pk')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset
    
    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_pk')
        serializer.save(product_id=product_id)


class ProductModifierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductModifier CRUD.
    """
    queryset = ProductModifier.objects.filter(is_deleted=False)
    serializer_class = ProductModifierSerializer
    permission_classes = [IsManagerOrAdmin]
    
    @action(detail=True, methods=['post'])
    def assign_products(self, request, pk=None):
        """Assign modifier to multiple products."""
        modifier = self.get_object()
        product_ids = request.data.get('product_ids', [])
        products = Product.objects.filter(id__in=product_ids)
        modifier.products.add(*products)
        return Response({'status': f'Modifier assigned to {len(products)} products'})


class ComboProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing combo product items.
    """
    queryset = ComboProduct.objects.filter(is_deleted=False)
    serializer_class = ComboProductSerializer
    permission_classes = [IsManagerOrAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        combo_id = self.kwargs.get('combo_pk')
        if combo_id:
            queryset = queryset.filter(combo_id=combo_id)
        return queryset
