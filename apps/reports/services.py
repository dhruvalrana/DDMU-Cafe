"""
Report generation services.
"""

from decimal import Decimal
from datetime import date, datetime, timedelta
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncHour, ExtractHour
from django.utils import timezone

from apps.orders.models import Order, OrderLine
from apps.payments.models import Payment
from apps.terminals.models import POSSession, CashMovement
from apps.floors.models import Table
from apps.products.models import Product, Category


class ReportService:
    """Service for generating reports."""
    
    @staticmethod
    def get_daily_sales(start_date: date, end_date: date, terminal_id=None, user_id=None):
        """Get daily sales summary."""
        queryset = Order.objects.filter(
            status='paid',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False,
        )
        
        if terminal_id:
            queryset = queryset.filter(session__terminal_id=terminal_id)
        if user_id:
            queryset = queryset.filter(session__responsible_user_id=user_id)
        
        daily_data = queryset.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total_sales=Sum('total_amount'),
            total_orders=Count('id'),
            total_tax=Sum('tax_amount'),
            total_discount=Sum('discount_amount'),
        ).order_by('date')
        
        result = []
        for day in daily_data:
            avg_order = day['total_sales'] / day['total_orders'] if day['total_orders'] else Decimal('0')
            result.append({
                'date': day['date'],
                'total_sales': day['total_sales'] or Decimal('0'),
                'total_orders': day['total_orders'],
                'average_order_value': avg_order,
                'total_tax': day['total_tax'] or Decimal('0'),
                'total_discount': day['total_discount'] or Decimal('0'),
            })
        
        return result
    
    @staticmethod
    def get_hourly_sales(target_date: date, terminal_id=None):
        """Get hourly sales breakdown for a specific date."""
        queryset = Order.objects.filter(
            status='paid',
            created_at__date=target_date,
            is_deleted=False,
        )
        
        if terminal_id:
            queryset = queryset.filter(session__terminal_id=terminal_id)
        
        hourly_data = queryset.annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            total_sales=Sum('total_amount'),
            order_count=Count('id'),
        ).order_by('hour')
        
        # Fill in all hours
        result = []
        hour_data = {h['hour']: h for h in hourly_data}
        for hour in range(24):
            data = hour_data.get(hour, {})
            result.append({
                'hour': hour,
                'total_sales': data.get('total_sales', Decimal('0')),
                'order_count': data.get('order_count', 0),
            })
        
        return result
    
    @staticmethod
    def get_payment_method_breakdown(start_date: date, end_date: date, terminal_id=None):
        """Get payment method breakdown."""
        queryset = Payment.objects.filter(
            status='completed',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False,
        )
        
        if terminal_id:
            queryset = queryset.filter(order__session__terminal_id=terminal_id)
        
        payment_data = queryset.values(
            'payment_method__payment_type',
            'payment_method__name',
        ).annotate(
            total_amount=Sum('amount'),
            transaction_count=Count('id'),
        ).order_by('-total_amount')
        
        total = sum(p['total_amount'] or 0 for p in payment_data)
        
        result = []
        for payment in payment_data:
            percentage = (payment['total_amount'] / total * 100) if total else 0
            result.append({
                'payment_method': payment['payment_method__payment_type'],
                'payment_method_name': payment['payment_method__name'],
                'total_amount': payment['total_amount'] or Decimal('0'),
                'transaction_count': payment['transaction_count'],
                'percentage': round(Decimal(percentage), 2),
            })
        
        return result
    
    @staticmethod
    def get_product_sales(start_date: date, end_date: date, limit=20, terminal_id=None):
        """Get top selling products."""
        queryset = OrderLine.objects.filter(
            order__status='paid',
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            is_deleted=False,
        )
        
        if terminal_id:
            queryset = queryset.filter(order__session__terminal_id=terminal_id)
        
        product_data = queryset.values(
            'product_id',
            'product__name',
            'product__category__name',
        ).annotate(
            quantity_sold=Sum('quantity'),
            total_sales=Sum('subtotal'),
        ).order_by('-total_sales')[:limit]
        
        total_sales = sum(p['total_sales'] or 0 for p in product_data)
        
        result = []
        for product in product_data:
            percentage = (product['total_sales'] / total_sales * 100) if total_sales else 0
            result.append({
                'product_id': product['product_id'],
                'product_name': product['product__name'],
                'category_name': product['product__category__name'] or 'Uncategorized',
                'quantity_sold': product['quantity_sold'],
                'total_sales': product['total_sales'] or Decimal('0'),
                'percentage': round(Decimal(percentage), 2),
            })
        
        return result
    
    @staticmethod
    def get_category_sales(start_date: date, end_date: date, terminal_id=None):
        """Get sales by category."""
        queryset = OrderLine.objects.filter(
            order__status='paid',
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            is_deleted=False,
        )
        
        if terminal_id:
            queryset = queryset.filter(order__session__terminal_id=terminal_id)
        
        category_data = queryset.values(
            'product__category_id',
            'product__category__name',
        ).annotate(
            total_sales=Sum('subtotal'),
            item_count=Count('id'),
        ).order_by('-total_sales')
        
        total = sum(c['total_sales'] or 0 for c in category_data)
        
        result = []
        for category in category_data:
            percentage = (category['total_sales'] / total * 100) if total else 0
            result.append({
                'category_id': category['product__category_id'],
                'category_name': category['product__category__name'] or 'Uncategorized',
                'total_sales': category['total_sales'] or Decimal('0'),
                'item_count': category['item_count'],
                'percentage': round(Decimal(percentage), 2),
            })
        
        return result
    
    @staticmethod
    def get_staff_performance(start_date: date, end_date: date):
        """Get staff performance report."""
        sessions = POSSession.objects.filter(
            opening_time__date__gte=start_date,
            opening_time__date__lte=end_date,
        ).select_related('responsible_user')
        
        user_data = {}
        for session in sessions:
            user_id = session.responsible_user_id
            if user_id not in user_data:
                user_data[user_id] = {
                    'user_id': user_id,
                    'user_name': session.responsible_user.get_full_name() or session.responsible_user.username,
                    'total_sales': Decimal('0'),
                    'order_count': 0,
                    'total_hours': Decimal('0'),
                }
            
            # Calculate hours worked
            if session.closing_time:
                hours = (session.closing_time - session.opening_time).total_seconds() / 3600
            elif session.is_active:
                hours = (timezone.now() - session.opening_time).total_seconds() / 3600
            else:
                hours = 0
            
            user_data[user_id]['total_hours'] += Decimal(str(hours))
            
            # Get orders for this session
            orders = Order.objects.filter(session=session, status='paid', is_deleted=False)
            order_totals = orders.aggregate(total=Sum('total_amount'), count=Count('id'))
            
            user_data[user_id]['total_sales'] += order_totals['total'] or Decimal('0')
            user_data[user_id]['order_count'] += order_totals['count'] or 0
        
        result = []
        for data in user_data.values():
            avg_order = data['total_sales'] / data['order_count'] if data['order_count'] else Decimal('0')
            result.append({
                'user_id': data['user_id'],
                'user_name': data['user_name'],
                'total_sales': data['total_sales'],
                'order_count': data['order_count'],
                'average_order_value': avg_order,
                'total_hours_worked': round(data['total_hours'], 2),
            })
        
        return sorted(result, key=lambda x: x['total_sales'], reverse=True)
    
    @staticmethod
    def get_session_summaries(start_date: date, end_date: date, terminal_id=None):
        """Get session summaries."""
        queryset = POSSession.objects.filter(
            opening_time__date__gte=start_date,
            opening_time__date__lte=end_date,
        ).select_related('terminal', 'responsible_user')
        
        if terminal_id:
            queryset = queryset.filter(terminal_id=terminal_id)
        
        result = []
        for session in queryset.order_by('-opening_time'):
            # Get orders
            orders = Order.objects.filter(session=session, status='paid', is_deleted=False)
            order_totals = orders.aggregate(total=Sum('total_amount'), count=Count('id'))
            
            # Get cash movements
            movements = CashMovement.objects.filter(session=session)
            cash_in = movements.filter(
                movement_type__in=['cash_in', 'opening']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            cash_out = movements.filter(
                movement_type__in=['cash_out', 'closing']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Calculate expected cash
            cash_payments = Payment.objects.filter(
                order__session=session,
                payment_method__payment_type='cash',
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            expected_cash = session.opening_balance + cash_payments + cash_in - cash_out
            difference = None
            if session.closing_balance:
                difference = session.closing_balance - expected_cash
            
            result.append({
                'session_id': session.id,
                'terminal_name': session.terminal.name,
                'user_name': session.responsible_user.get_full_name() or session.responsible_user.username,
                'opened_at': session.opening_time,
                'closed_at': session.closing_time,
                'opening_balance': session.opening_balance,
                'closing_balance': session.closing_balance,
                'total_sales': order_totals['total'] or Decimal('0'),
                'order_count': order_totals['count'] or 0,
                'cash_in': cash_in,
                'cash_out': cash_out,
                'expected_cash': expected_cash,
                'difference': difference,
            })
        
        return result
    
    @staticmethod
    def get_dashboard_data():
        """Get dashboard summary data."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Today's data
        today_orders = Order.objects.filter(
            status='paid',
            created_at__date=today,
            is_deleted=False,
        )
        today_totals = today_orders.aggregate(
            total=Sum('total_amount'),
            count=Count('id'),
        )
        today_sales = today_totals['total'] or Decimal('0')
        today_count = today_totals['count'] or 0
        today_avg = today_sales / today_count if today_count else Decimal('0')
        
        # Yesterday's data
        yesterday_orders = Order.objects.filter(
            status='paid',
            created_at__date=yesterday,
            is_deleted=False,
        )
        yesterday_sales = yesterday_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Change percentage
        if yesterday_sales:
            change = ((today_sales - yesterday_sales) / yesterday_sales * 100)
        else:
            change = Decimal('100') if today_sales else Decimal('0')
        
        # Current state
        active_sessions = POSSession.objects.filter(is_active=True, status='open').count()
        open_orders = Order.objects.filter(
            status__in=['draft', 'sent_to_kitchen', 'preparing', 'ready'],
            is_deleted=False,
        ).count()
        tables = Table.objects.filter(is_deleted=False)
        tables_occupied = tables.filter(is_occupied=True).count()
        tables_total = tables.count()
        
        # Top products
        top_products = ReportService.get_product_sales(today, today, limit=5)
        
        # Hourly sales
        hourly_sales = ReportService.get_hourly_sales(today)
        
        return {
            'today_sales': today_sales,
            'today_orders': today_count,
            'today_average_order': today_avg,
            'yesterday_sales': yesterday_sales,
            'sales_change_percent': round(change, 2),
            'active_sessions': active_sessions,
            'open_orders': open_orders,
            'tables_occupied': tables_occupied,
            'tables_total': tables_total,
            'top_products': top_products,
            'hourly_sales': hourly_sales,
        }
