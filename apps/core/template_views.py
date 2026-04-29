"""
Template Views for Odoo Cafe POS
Server-side rendered views using Django templates
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from apps.authentication.models import User
from apps.products.models import Product, Category
from apps.orders.models import Order, OrderLine
from apps.floors.models import Floor, Table
from apps.payments.models import Payment, PaymentMethod
from apps.terminals.models import POSSession
from apps.core.models import SystemSettings


# ============================================
# Authentication Views
# ============================================

def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect('dashboard')
        else:
            return render(request, 'auth/login.html', {
                'error': 'Invalid email or password',
                'email': email
            })
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """Logout and redirect to login"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ============================================
# Dashboard
# ============================================

@login_required
def dashboard(request):
    """Main dashboard with stats"""
    today = timezone.now().date()
    
    # Today's stats
    today_orders = Order.objects.filter(created_at__date=today)
    stats = {
        'total_orders': today_orders.count(),
        'total_revenue': today_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'active_tables': Table.objects.filter(is_occupied=True).count(),
        'avg_order': today_orders.aggregate(Avg('total_amount'))['total_amount__avg'] or 0,
    }
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:5]
    
    # Top products
    top_products = Product.objects.filter(is_available_for_pos=True, is_active=True)[:5]
    
    return render(request, 'dashboard/index.html', {
        'stats': stats,
        'recent_orders': recent_orders,
        'top_products': top_products,
    })


# ============================================
# POS Terminal
# ============================================

@login_required
def pos_terminal(request):
    """POS Terminal view"""
    category_id = request.GET.get('category')
    table_id = request.GET.get('table')
    
    products = Product.objects.filter(is_available_for_pos=True, is_active=True)
    if category_id:
        products = products.filter(category_id=category_id)
    
    categories = Category.objects.all()
    tables = Table.objects.filter(is_occupied=False, is_active=True)
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    
    return render(request, 'pos/terminal.html', {
        'products': products,
        'categories': categories,
        'tables': tables,
        'payment_methods': payment_methods,
        'selected_table': table_id,
        'selected_category': category_id,
    })


@login_required
@require_POST
def pos_create_order(request):
    """Create order from POS"""
    try:
        data = json.loads(request.body)
        
        # Get or create active session
        session = POSSession.objects.filter(
            responsible_user=request.user,
            status='open',
            is_active=True
        ).first()
        
        if not session:
            # Create a simple session for web orders
            from apps.terminals.models import POSTerminal
            terminal = POSTerminal.objects.first()
            if terminal:
                session = POSSession.objects.create(
                    terminal=terminal,
                    responsible_user=request.user,
                    status='open',
                    is_active=True
                )
            else:
                return JsonResponse({
                    'success': False, 
                    'error': 'No POS terminal configured. Please set up a terminal first.'
                }, status=400)
        
        # Create order (start as draft)
        order = Order.objects.create(
            session=session,
            order_type=data.get('order_type', 'dine_in'),
            table_id=data.get('table_id') or None,
            status='draft',
            created_by=request.user,
        )
        
        # Add order lines
        subtotal = Decimal('0.00')
        for item in data.get('items', []):
            product = Product.objects.get(id=item['product_id'])
            line = OrderLine.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                unit_price=product.price,
            )
            subtotal += line.line_total
        
        # Calculate totals
        discount = Decimal(str(data.get('discount', 0)))
        tax = subtotal * Decimal('0.05')  # 5% tax
        order.subtotal = subtotal
        order.tax_amount = tax
        order.discount_amount = discount
        order.total_amount = subtotal + tax - discount
        order.save()
        
        # Create payment if provided
        payment_method_type = data.get('payment_method')  # 'cash', 'card', 'upi'
        payment_method_id = data.get('payment_method_id')
        
        if payment_method_type or payment_method_id:
            # Get payment method by type or ID
            if payment_method_id:
                payment_method = PaymentMethod.objects.get(id=payment_method_id)
            else:
                # Look up by method_type
                payment_method = PaymentMethod.objects.filter(
                    method_type=payment_method_type,
                    is_active=True
                ).first()
                
                if not payment_method:
                    # Try to find any payment method with matching name
                    payment_method = PaymentMethod.objects.filter(
                        name__icontains=payment_method_type,
                        is_active=True
                    ).first()
                
                if not payment_method:
                    # Create a default payment method for this type
                    payment_method = PaymentMethod.objects.create(
                        name=payment_method_type.title(),
                        method_type=payment_method_type,
                        is_active=True
                    )
            
            Payment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=order.total_amount,
                amount_received=data.get('amount_received', order.total_amount),
                status='completed',
                processed_by=request.user,
                processed_at=timezone.now(),
            )
            order.paid_at = timezone.now()
            order.save()
        
        # Send order to kitchen after payment is recorded
        # This creates the KitchenOrder and sets status to 'sent_to_kitchen'
        order.send_to_kitchen()
        
        # Mark all lines as sent to kitchen
        order.lines.update(is_sent_to_kitchen=True)
        
        # Update table status to occupied (customer is waiting for food)
        if order.table:
            order.table.is_occupied = True
            order.table.save()
        
        return JsonResponse({
            'success': True,
            'order_id': str(order.id),
            'order_number': order.order_number,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================
# Orders
# ============================================

@login_required
def order_list(request):
    """List all orders"""
    status_filter = request.GET.get('status')
    
    orders = Order.objects.order_by('-created_at')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    paginator = Paginator(orders, 12)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    return render(request, 'orders/list.html', {
        'orders': orders,
        'current_status': status_filter,
        'pos_url': 'pos_terminal',
    })


@login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/detail.html', {
        'order': order,
    })


@login_required
@require_POST
def order_update_status(request, order_id):
    """Update order status"""
    order = get_object_or_404(Order, id=order_id)
    status = request.POST.get('status')
    
    if status:
        order.status = status
        order.save()
        messages.success(request, f'Order #{order.order_number} updated to {status}')
    
    return redirect('order_detail', order_id=order_id)


@login_required
def order_payment(request, order_id):
    """Process payment for order"""
    order = get_object_or_404(Order, id=order_id)
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    
    if request.method == 'POST':
        method_id = request.POST.get('payment_method_id')
        method_type = request.POST.get('payment_method', 'cash')
        amount = order.total_amount
        received = float(request.POST.get('amount_received', amount))
        
        # Get or create payment method
        if method_id:
            payment_method = PaymentMethod.objects.get(id=method_id)
        else:
            payment_method = PaymentMethod.objects.filter(method_type=method_type).first()
            if not payment_method:
                payment_method = PaymentMethod.objects.create(
                    name=method_type.title(),
                    method_type=method_type,
                    is_active=True
                )
        
        Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount,
            amount_received=received,
            change_amount=max(0, received - float(amount)),
            status='completed',
            processed_by=request.user,
            processed_at=timezone.now(),
        )
        order.status = 'paid'
        order.paid_at = timezone.now()
        order.save()
        
        if order.table:
            order.table.is_occupied = False
            order.table.save()
        
        messages.success(request, f'Payment completed for Order #{order.order_number}')
        return redirect('order_detail', order_id=order_id)
    
    return render(request, 'orders/payment.html', {
        'order': order,
        'payment_methods': payment_methods,
    })


# ============================================
# Kitchen Display
# ============================================

@login_required
def kitchen_display(request):
    """Kitchen display system with pagination"""
    # Items per page for each column
    items_per_page = 6
    
    # Get page numbers for each column
    pending_page = request.GET.get('pending_page', 1)
    preparing_page = request.GET.get('preparing_page', 1)
    ready_page = request.GET.get('ready_page', 1)
    
    # Get orders by status
    pending_orders = Order.objects.filter(
        status='sent_to_kitchen'
    ).order_by('created_at')
    
    preparing_orders = Order.objects.filter(
        status='preparing'
    ).order_by('created_at')
    
    ready_orders = Order.objects.filter(
        status='ready'
    ).order_by('created_at')
    
    # Get counts before pagination
    pending_count = pending_orders.count()
    preparing_count = preparing_orders.count()
    ready_count = ready_orders.count()
    
    # Paginate each column
    pending_paginator = Paginator(pending_orders, items_per_page)
    preparing_paginator = Paginator(preparing_orders, items_per_page)
    ready_paginator = Paginator(ready_orders, items_per_page)
    
    pending_orders = pending_paginator.get_page(pending_page)
    preparing_orders = preparing_paginator.get_page(preparing_page)
    ready_orders = ready_paginator.get_page(ready_page)
    
    # Combine all orders for timers (we need all visible orders)
    all_visible_orders = list(pending_orders) + list(preparing_orders) + list(ready_orders)
    
    return render(request, 'kitchen/display.html', {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'all_orders': all_visible_orders,
        'pending_count': pending_count,
        'preparing_count': preparing_count,
        'ready_count': ready_count,
    })


@login_required
@require_POST
def kitchen_update_status(request, order_id):
    """Update order status from kitchen"""
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if new_status:
        # Update order status
        order.status = new_status
        
        # Handle timestamps based on status
        if new_status == 'preparing':
            # Also update KitchenOrder if exists
            if hasattr(order, 'kitchen_order'):
                order.kitchen_order.start_preparing()
        elif new_status == 'ready':
            order.ready_at = timezone.now()
            # Also update KitchenOrder if exists
            if hasattr(order, 'kitchen_order'):
                order.kitchen_order.status = 'completed'
                order.kitchen_order.completed_at = timezone.now()
                order.kitchen_order.save()
            # Mark all lines as prepared
            order.lines.update(is_prepared=True, prepared_at=timezone.now())
        elif new_status == 'served':
            order.served_at = timezone.now()
            order.served_by = request.user
            # Release table if dine-in
            if order.table:
                order.table.is_occupied = False
                order.table.save()
        
        order.save()
    
    return redirect('kitchen_display')


# ============================================
# Tables
# ============================================

@login_required
def table_list(request):
    """Table/floor plan view"""
    floor_id = request.GET.get('floor')
    
    floors = Floor.objects.all()
    current_floor = None
    
    if floor_id:
        current_floor = get_object_or_404(Floor, id=floor_id)
    elif floors.exists():
        current_floor = floors.first()
    
    tables = Table.objects.all()
    if current_floor:
        tables = tables.filter(floor=current_floor)
    
    available_count = tables.filter(is_occupied=False, is_active=True).count()
    occupied_count = tables.filter(is_occupied=True).count()
    reserved_count = 0  # No reserved status in this model
    
    return render(request, 'tables/list.html', {
        'floors': floors,
        'current_floor': current_floor,
        'tables': tables,
        'available_count': available_count,
        'occupied_count': occupied_count,
        'reserved_count': reserved_count,
        'add_table_url': '/admin/floors/table/add/',
    })


@login_required
@require_POST
def table_update_status(request, table_id):
    """Update table status"""
    try:
        data = json.loads(request.body)
        table = get_object_or_404(Table, id=table_id)
        status = data.get('status', 'available')
        table.is_occupied = (status == 'occupied')
        table.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================
# Products
# ============================================

@login_required
def product_list(request):
    """Product list view"""
    category_id = request.GET.get('category')
    
    products = Product.objects.all()
    if category_id:
        products = products.filter(category_id=category_id)
    
    categories = Category.objects.all()
    current_category = None
    if category_id:
        current_category = Category.objects.filter(id=category_id).first()
    
    paginator = Paginator(products, 20)
    page = request.GET.get('page', 1)
    products = paginator.get_page(page)
    
    return render(request, 'products/list.html', {
        'products': products,
        'categories': categories,
        'current_category': current_category,
        'add_url': '/admin/products/product/add/',
    })


@login_required
def product_add(request):
    """Add new product"""
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product = Product.objects.create(
            name=request.POST.get('name'),
            category_id=request.POST.get('category'),
            price=request.POST.get('price'),
            description=request.POST.get('description', ''),
            is_available_for_pos=request.POST.get('is_available') == 'on',
        )
        if 'image' in request.FILES:
            product.image = request.FILES['image']
            product.save()
        
        messages.success(request, f'Product "{product.name}" created!')
        return redirect('product_list')
    
    return render(request, 'products/form.html', {
        'page_title': 'Add Product',
        'categories': categories,
        'product': None,
    })


@login_required
def product_edit(request, product_id):
    """Edit product"""
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category')
        product.price = request.POST.get('price')
        product.description = request.POST.get('description', '')
        product.is_available_for_pos = request.POST.get('is_available') == 'on'
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        product.save()
        
        messages.success(request, f'Product "{product.name}" updated!')
        return redirect('product_list')
    
    return render(request, 'products/form.html', {
        'page_title': 'Edit Product',
        'categories': categories,
        'product': product,
    })


@login_required
@require_POST
def product_toggle(request, product_id):
    """Toggle product availability"""
    product = get_object_or_404(Product, id=product_id)
    product.is_available_for_pos = not product.is_available_for_pos
    product.save()
    
    status = 'available' if product.is_available_for_pos else 'unavailable'
    messages.success(request, f'Product "{product.name}" is now {status}')
    return redirect('product_list')


@login_required
@require_POST
def product_delete(request, product_id):
    """Delete product"""
    product = get_object_or_404(Product, id=product_id)
    name = product.name
    product.delete()
    messages.success(request, f'Product "{name}" deleted')
    return redirect('product_list')


# ============================================
# Customers (Placeholder - No Customer model)
# ============================================

@login_required
def customer_list(request):
    """Customer list view - placeholder"""
    return render(request, 'customers/list.html', {
        'customers': [],
        'add_url': '/admin/',
    })


@login_required
def customer_detail(request, customer_id):
    """Customer detail view - placeholder"""
    messages.warning(request, 'Customer feature not implemented yet')
    return redirect('customer_list')


@login_required
def customer_edit(request, customer_id):
    """Edit customer - placeholder"""
    messages.warning(request, 'Customer feature not implemented yet')
    return redirect('customer_list')


# ============================================
# Reports
# ============================================

@login_required
def reports(request):
    """Reports dashboard"""
    from datetime import datetime, timedelta
    
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Parse dates or use defaults
    today = timezone.now().date()
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today
    else:
        start_date = today
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today
    
    # Current period orders
    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Calculate previous period for comparison
    period_days = (end_date - start_date).days + 1
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=period_days - 1)
    
    prev_orders = Order.objects.filter(
        created_at__date__gte=prev_start_date,
        created_at__date__lte=prev_end_date
    )
    
    # Current period stats
    current_order_count = orders.count()
    current_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Previous period stats
    prev_order_count = prev_orders.count()
    prev_revenue = prev_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Calculate percentage changes
    def calc_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
    
    orders_change = calc_change(current_order_count, prev_order_count)
    revenue_change = calc_change(float(current_revenue), float(prev_revenue))
    
    # Stats
    stats = {
        'total_orders': current_order_count,
        'total_revenue': current_revenue,
        'avg_order': orders.aggregate(Avg('total_amount'))['total_amount__avg'] or 0,
        'items_sold': OrderLine.objects.filter(order__in=orders).aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'orders_change': orders_change,
        'revenue_change': revenue_change,
    }
    
    # Orders by status
    order_by_status = {}
    for status in ['draft', 'sent_to_kitchen', 'preparing', 'ready', 'paid', 'cancelled']:
        order_by_status[status] = orders.filter(status=status).count()
    
    # Orders by type with display names
    order_by_type = {}
    total_orders = orders.count() or 1
    order_type_display = {
        'dine_in': 'Dine In',
        'takeaway': 'Takeaway', 
        'delivery': 'Delivery'
    }
    for order_type in ['dine_in', 'takeaway', 'delivery']:
        count = orders.filter(order_type=order_type).count()
        order_by_type[order_type_display[order_type]] = {
            'count': count,
            'percentage': round(count / total_orders * 100, 1)
        }
    
    # Top products
    top_products = []
    product_sales = OrderLine.objects.filter(order__in=orders).values(
        'product__name', 'product__category__name'
    ).annotate(
        sold_count=Sum('quantity'),
        revenue=Sum('line_total')
    ).order_by('-sold_count')[:10]
    
    for item in product_sales:
        top_products.append({
            'name': item['product__name'],
            'category': item['product__category__name'] or 'Uncategorized',
            'sold_count': item['sold_count'],
            'revenue': item['revenue'],
        })
    
    # Payment methods
    payment_methods = {}
    payments = Payment.objects.filter(order__in=orders, status='completed')
    for method in payments.values('payment_method__name').annotate(
        count=Count('id'),
        amount=Sum('amount')
    ):
        payment_methods[method['payment_method__name'] or 'Other'] = {
            'count': method['count'],
            'amount': method['amount'],
        }
    
    # Format dates for template (YYYY-MM-DD format for HTML date input)
    return render(request, 'reports/index.html', {
        'stats': stats,
        'order_by_status': order_by_status,
        'order_by_type': order_by_type,
        'top_products': top_products,
        'payment_methods': payment_methods,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    })


# ============================================
# Settings
# ============================================

@login_required
def settings_view(request):
    """Settings page"""
    users = User.objects.all()[:10]
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        section = request.POST.get('section', '')
        
        if section == 'restaurant':
            settings.restaurant_name = request.POST.get('restaurant_name', settings.restaurant_name)
            settings.phone = request.POST.get('phone', '')
            settings.address = request.POST.get('address', '')
            settings.save()
            messages.success(request, 'Restaurant information saved successfully!')
        
        elif section == 'tax':
            try:
                settings.tax_rate = Decimal(request.POST.get('tax_rate', '5'))
            except:
                settings.tax_rate = Decimal('5.00')
            settings.tax_name = request.POST.get('tax_name', 'GST')
            settings.tax_number = request.POST.get('tax_number', '')
            settings.save()
            messages.success(request, 'Tax settings saved successfully!')
        
        elif section == 'receipt':
            settings.receipt_header = request.POST.get('receipt_header', '')
            settings.receipt_footer = request.POST.get('receipt_footer', 'Thank you for dining with us!')
            settings.print_auto = request.POST.get('print_auto') == 'on'
            settings.save()
            messages.success(request, 'Receipt settings saved successfully!')
        
        return redirect('settings')
    
    return render(request, 'settings/index.html', {
        'users': users,
        'settings': settings,
    })


# ============================================
# Virtual Assistant Chatbot
# ============================================

def chatbot_assistant(request):
    """Fullscreen chatbot assistant for self-ordering or team orders"""
    return render(request, 'chatbot/fullscreen.html')

