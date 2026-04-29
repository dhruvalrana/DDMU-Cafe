"""
Report views.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from datetime import date, timedelta

from apps.core.permissions import IsManagerOrAdmin
from apps.core.utils import get_date_range
from .services import ReportService
from .exports import PDFExporter, ExcelExporter
from .serializers import (
    DateRangeSerializer,
    DailySalesSerializer,
    HourlySalesSerializer,
    PaymentMethodBreakdownSerializer,
    ProductSalesSerializer,
    CategorySalesSerializer,
    StaffPerformanceSerializer,
    SessionSummarySerializer,
    DashboardSerializer,
    ExportFormatSerializer,
)


class DashboardView(APIView):
    """
    Dashboard summary data.
    
    GET /api/v1/reports/dashboard/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        data = ReportService.get_dashboard_data()
        serializer = DashboardSerializer(data)
        return Response(serializer.data)


class DailySalesView(APIView):
    """
    Daily sales report.
    
    GET /api/v1/reports/daily-sales/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        params = DateRangeSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        
        start_date, end_date = get_date_range(
            params.validated_data.get('start_date'),
            params.validated_data.get('end_date'),
            'month'
        )
        
        data = ReportService.get_daily_sales(
            start_date,
            end_date,
            terminal_id=params.validated_data.get('terminal_id'),
            user_id=params.validated_data.get('user_id'),
        )
        
        serializer = DailySalesSerializer(data, many=True)
        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'data': serializer.data,
        })


class HourlySalesView(APIView):
    """
    Hourly sales breakdown.
    
    GET /api/v1/reports/hourly-sales/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        target_date = request.query_params.get('date')
        if target_date:
            target_date = date.fromisoformat(target_date)
        else:
            target_date = date.today()
        
        terminal_id = request.query_params.get('terminal_id')
        
        data = ReportService.get_hourly_sales(target_date, terminal_id)
        serializer = HourlySalesSerializer(data, many=True)
        
        return Response({
            'date': target_date,
            'data': serializer.data,
        })


class PaymentMethodsView(APIView):
    """
    Payment method breakdown.
    
    GET /api/v1/reports/payment-methods/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        params = DateRangeSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        
        start_date, end_date = get_date_range(
            params.validated_data.get('start_date'),
            params.validated_data.get('end_date'),
            'month'
        )
        
        data = ReportService.get_payment_method_breakdown(
            start_date,
            end_date,
            terminal_id=params.validated_data.get('terminal_id'),
        )
        
        serializer = PaymentMethodBreakdownSerializer(data, many=True)
        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'data': serializer.data,
        })


class ProductSalesView(APIView):
    """
    Product sales report.
    
    GET /api/v1/reports/product-sales/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        params = DateRangeSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        
        start_date, end_date = get_date_range(
            params.validated_data.get('start_date'),
            params.validated_data.get('end_date'),
            'month'
        )
        
        limit = int(request.query_params.get('limit', 50))
        
        data = ReportService.get_product_sales(
            start_date,
            end_date,
            limit=limit,
            terminal_id=params.validated_data.get('terminal_id'),
        )
        
        serializer = ProductSalesSerializer(data, many=True)
        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'data': serializer.data,
        })


class CategorySalesView(APIView):
    """
    Category sales report.
    
    GET /api/v1/reports/category-sales/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        params = DateRangeSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        
        start_date, end_date = get_date_range(
            params.validated_data.get('start_date'),
            params.validated_data.get('end_date'),
            'month'
        )
        
        data = ReportService.get_category_sales(
            start_date,
            end_date,
            terminal_id=params.validated_data.get('terminal_id'),
        )
        
        serializer = CategorySalesSerializer(data, many=True)
        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'data': serializer.data,
        })


class StaffPerformanceView(APIView):
    """
    Staff performance report.
    
    GET /api/v1/reports/staff-performance/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        params = DateRangeSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        
        start_date, end_date = get_date_range(
            params.validated_data.get('start_date'),
            params.validated_data.get('end_date'),
            'month'
        )
        
        data = ReportService.get_staff_performance(start_date, end_date)
        serializer = StaffPerformanceSerializer(data, many=True)
        
        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'data': serializer.data,
        })


class SessionSummaryView(APIView):
    """
    POS session summary.
    
    GET /api/v1/reports/sessions/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def get(self, request):
        params = DateRangeSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        
        start_date, end_date = get_date_range(
            params.validated_data.get('start_date'),
            params.validated_data.get('end_date'),
            'week'
        )
        
        data = ReportService.get_session_summaries(
            start_date,
            end_date,
            terminal_id=params.validated_data.get('terminal_id'),
        )
        
        serializer = SessionSummarySerializer(data, many=True)
        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'data': serializer.data,
        })


class ExportReportView(APIView):
    """
    Export report to PDF/Excel.
    
    POST /api/v1/reports/export/
    """
    permission_classes = [IsManagerOrAdmin]
    
    def post(self, request):
        serializer = ExportFormatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        export_format = data['format']
        report_type = data['report_type']
        start_date = data['start_date']
        end_date = data['end_date']
        
        # Get report data
        if report_type == 'daily_sales':
            report_data = ReportService.get_daily_sales(start_date, end_date)
        elif report_type == 'product_sales':
            report_data = ReportService.get_product_sales(start_date, end_date)
        elif report_type == 'category_sales':
            report_data = ReportService.get_category_sales(start_date, end_date)
        elif report_type == 'payment_methods':
            report_data = ReportService.get_payment_method_breakdown(start_date, end_date)
        elif report_type == 'staff_performance':
            report_data = ReportService.get_staff_performance(start_date, end_date)
        elif report_type == 'session_summary':
            report_data = ReportService.get_session_summaries(start_date, end_date)
        else:
            return Response(
                {'error': 'Invalid report type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Export based on format
        if export_format == 'pdf':
            content = self._export_pdf(report_type, report_data, start_date, end_date)
            content_type = 'application/pdf'
            extension = 'pdf'
        elif export_format == 'xlsx':
            content = self._export_excel(report_type, report_data, start_date, end_date)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extension = 'xlsx'
        else:  # csv
            content = self._export_csv(report_type, report_data)
            content_type = 'text/csv'
            extension = 'csv'
        
        filename = f"{report_type}_{start_date}_{end_date}.{extension}"
        
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    def _export_pdf(self, report_type, data, start_date, end_date):
        """Export to PDF."""
        exporters = {
            'daily_sales': PDFExporter.export_daily_sales,
            'product_sales': PDFExporter.export_product_sales,
            'session_summary': PDFExporter.export_session_summary,
        }
        exporter = exporters.get(report_type)
        if exporter:
            return exporter(data, start_date, end_date)
        return b''
    
    def _export_excel(self, report_type, data, start_date, end_date):
        """Export to Excel."""
        exporters = {
            'daily_sales': ExcelExporter.export_daily_sales,
            'product_sales': ExcelExporter.export_product_sales,
            'category_sales': ExcelExporter.export_category_sales,
            'payment_methods': ExcelExporter.export_payment_methods,
            'staff_performance': ExcelExporter.export_staff_performance,
            'session_summary': ExcelExporter.export_session_summary,
        }
        exporter = exporters.get(report_type)
        if exporter:
            return exporter(data, start_date, end_date)
        return b''
    
    def _export_csv(self, report_type, data):
        """Export to CSV."""
        import csv
        import io
        
        if not data:
            return ''
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue().encode('utf-8')
