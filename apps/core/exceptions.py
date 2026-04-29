"""
Custom exception handlers and exception classes.
"""

from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'success': False,
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
                'status_code': response.status_code,
            }
        }
        response.data = custom_response_data

    return response


class POSException(APIException):
    """Base exception for POS-specific errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A POS error occurred.'
    default_code = 'pos_error'


class SessionNotActiveError(POSException):
    """Raised when trying to perform operations without an active session."""
    default_detail = 'No active POS session found. Please open a session first.'
    default_code = 'session_not_active'


class SessionAlreadyOpenError(POSException):
    """Raised when trying to open a session when one is already active."""
    default_detail = 'A session is already open for this terminal.'
    default_code = 'session_already_open'


class OrderNotEditableError(POSException):
    """Raised when trying to edit an order that is not in draft status."""
    default_detail = 'This order cannot be modified in its current status.'
    default_code = 'order_not_editable'


class PaymentMethodDisabledError(POSException):
    """Raised when trying to use a disabled payment method."""
    default_detail = 'This payment method is currently disabled.'
    default_code = 'payment_method_disabled'


class InsufficientPaymentError(POSException):
    """Raised when payment amount is less than order total."""
    default_detail = 'Payment amount is insufficient.'
    default_code = 'insufficient_payment'


class TableOccupiedError(POSException):
    """Raised when trying to create an order on an occupied table."""
    default_detail = 'This table already has an active order.'
    default_code = 'table_occupied'


class InvalidTokenError(POSException):
    """Raised when self-order token is invalid or expired."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid or expired order token.'
    default_code = 'invalid_token'


class ProductUnavailableError(POSException):
    """Raised when trying to add an unavailable product."""
    default_detail = 'This product is currently unavailable.'
    default_code = 'product_unavailable'
