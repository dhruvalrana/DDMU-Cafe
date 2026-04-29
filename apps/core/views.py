"""
Core views for health check and API root.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import connection


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        
        return Response({
            'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
            'database': db_status,
            'version': '1.0.0',
        }, status=status.HTTP_200_OK if db_status == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE)


class APIRootView(APIView):
    """
    API Root - Lists all available endpoints.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'name': 'Odoo Cafe POS API',
            'version': 'v1',
            'endpoints': {
                'auth': {
                    'signup': '/api/v1/auth/signup/',
                    'login': '/api/v1/auth/login/',
                    'refresh': '/api/v1/auth/token/refresh/',
                    'logout': '/api/v1/auth/logout/',
                    'me': '/api/v1/auth/me/',
                },
                'products': '/api/v1/products/',
                'categories': '/api/v1/products/categories/',
                'payments': '/api/v1/payments/',
                'payment_methods': '/api/v1/payments/methods/',
                'floors': '/api/v1/floors/',
                'tables': '/api/v1/floors/tables/',
                'terminals': '/api/v1/terminals/',
                'sessions': '/api/v1/terminals/sessions/',
                'orders': '/api/v1/orders/',
                'kitchen': '/api/v1/kitchen/',
                'reports': '/api/v1/reports/',
                'self_order': '/api/v1/self-order/',
            },
            'websockets': {
                'kitchen': '/ws/kitchen/<terminal_id>/',
                'customer': '/ws/customer/<order_id>/',
                'orders': '/ws/orders/<session_id>/',
            }
        })
