"""
Core utility functions and helpers.
"""

import qrcode
import io
import base64
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import random
import string


def generate_order_number():
    """
    Generate a unique order number.
    Format: ORD-YYMMDD-XXXXXX
    """
    prefix = settings.POS_SETTINGS.get('ORDER_NUMBER_PREFIX', 'ORD')
    date_part = timezone.now().strftime('%y%m%d')
    length = settings.POS_SETTINGS.get('ORDER_NUMBER_LENGTH', 6)
    random_part = ''.join(random.choices(string.digits, k=length))
    return f"{prefix}-{date_part}-{random_part}"


def generate_upi_qr(amount, upi_id=None, merchant_name=None, order_id=None):
    """
    Generate UPI QR code for payment.
    
    Args:
        amount: Payment amount
        upi_id: UPI ID (defaults to settings)
        merchant_name: Merchant name (defaults to settings)
        order_id: Order ID for reference
    
    Returns:
        Base64 encoded QR code image
    """
    if upi_id is None:
        upi_id = settings.UPI_SETTINGS.get('DEFAULT_UPI_ID')
    if merchant_name is None:
        merchant_name = settings.UPI_SETTINGS.get('MERCHANT_NAME')
    
    # UPI deep link format
    upi_string = f"upi://pay?pa={upi_id}&pn={merchant_name}&am={amount}&cu=INR"
    if order_id:
        upi_string += f"&tn=Order-{order_id}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=settings.UPI_SETTINGS.get('QR_BOX_SIZE', 10),
        border=settings.UPI_SETTINGS.get('QR_BORDER', 4),
    )
    qr.add_data(upi_string)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        'qr_image': f"data:image/png;base64,{img_base64}",
        'upi_string': upi_string,
        'amount': str(amount),
        'merchant_name': merchant_name,
    }


def generate_token(length=32):
    """Generate a random token for self-ordering."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def calculate_tax(amount, tax_rate=None):
    """
    Calculate tax amount.
    
    Args:
        amount: Base amount
        tax_rate: Tax percentage (defaults to settings)
    
    Returns:
        Tax amount
    """
    if tax_rate is None:
        tax_rate = settings.POS_SETTINGS.get('DEFAULT_TAX_RATE', 0)
    return round(amount * (tax_rate / 100), 2)


def format_currency(amount):
    """Format amount with currency symbol."""
    symbol = settings.POS_SETTINGS.get('CURRENCY_SYMBOL', '₹')
    return f"{symbol}{amount:.2f}"


def get_date_range(period):
    """
    Get date range based on period string.
    
    Args:
        period: 'today', 'week', 'month', 'year', or custom
    
    Returns:
        Tuple of (start_date, end_date)
    """
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == 'today':
        return today, now
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, now
    elif period == 'month':
        start = today.replace(day=1)
        return start, now
    elif period == 'year':
        start = today.replace(month=1, day=1)
        return start, now
    else:
        # Default to today
        return today, now


def round_to_currency(amount):
    """Round amount to 2 decimal places."""
    return round(float(amount), 2)


def generate_bill_pdf(order):
    """
    Generate a bill/receipt PDF for an order.
    
    Args:
        order: Order instance
    
    Returns:
        bytes: PDF content
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=24,
        spaceAfter=12,
    )
    elements.append(Paragraph("BILL / RECEIPT", title_style))
    
    # Restaurant info
    restaurant_info = f"""
        <para align=center>
        <b>{settings.POS_SETTINGS.get('RESTAURANT_NAME', 'Restaurant Name')}</b><br/>
        {settings.POS_SETTINGS.get('RESTAURANT_ADDRESS', 'Address')}<br/>
        Phone: {settings.POS_SETTINGS.get('RESTAURANT_PHONE', 'Phone')}<br/>
        </para>
    """
    elements.append(Paragraph(restaurant_info, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Order details
    order_info_style = ParagraphStyle('OrderInfo', parent=styles['Normal'], fontSize=10)
    order_details = f"""
        <b>Order #:</b> {order.order_number}<br/>
        <b>Date:</b> {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Table:</b> {order.table.name if order.table else 'N/A'}<br/>
        <b>Server:</b> {order.created_by.get_full_name() if order.created_by else 'N/A'}<br/>
        <b>Guests:</b> {order.guests_count}
    """
    elements.append(Paragraph(order_details, order_info_style))
    elements.append(Spacer(1, 20))
    
    # Items table
    table_data = [['Item', 'Qty', 'Price', 'Total']]
    for line in order.lines.filter(is_deleted=False):
        table_data.append([
            line.product.name[:30],
            f"{line.quantity:.0f}",
            format_currency(line.unit_price),
            format_currency(line.line_total),
        ])
    
    items_table = Table(table_data, colWidths=[3.5*inch, 0.8*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # Totals
    totals_style = ParagraphStyle('Totals', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=11)
    totals = f"""
        Subtotal: {format_currency(order.subtotal)}<br/>
        Tax: {format_currency(order.tax_amount)}<br/>
        Discount: {format_currency(order.discount_amount)}<br/>
        Tip: {format_currency(order.tip_amount)}<br/>
        <b>TOTAL: {format_currency(order.total_amount)}</b><br/>
    """
    elements.append(Paragraph(totals, totals_style))
    elements.append(Spacer(1, 20))
    
    # Payment details
    if order.payments.filter(status='completed').exists():
        payment_info = "<b>Payment Details:</b><br/>"
        for payment in order.payments.filter(status='completed'):
            payment_info += f"{payment.payment_method.name}: {format_currency(payment.amount)}<br/>"
            if payment.change_amount > 0:
                payment_info += f"Change: {format_currency(payment.change_amount)}<br/>"
        elements.append(Paragraph(payment_info, order_info_style))
        elements.append(Spacer(1, 20))
    
    # Footer
    footer = "<para align=center>Thank you for your visit!<br/>Please visit again.</para>"
    elements.append(Paragraph(footer, styles['Normal']))
    
    doc.build(elements)
    return buffer.getvalue()
