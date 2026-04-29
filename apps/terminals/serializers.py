"""
Serializers for POS terminal and session management.
"""

from rest_framework import serializers
from .models import POSTerminal, POSSession, CashMovement


class POSTerminalSerializer(serializers.ModelSerializer):
    """Serializer for POSTerminal."""
    
    floor_name = serializers.CharField(source='floor.name', read_only=True)
    has_active_session = serializers.BooleanField(read_only=True)
    current_session_id = serializers.UUIDField(
        source='current_session.id',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = POSTerminal
        fields = [
            'id', 'name', 'code', 'description', 'floor', 'floor_name',
            'is_active', 'default_customer_display', 'default_kitchen_display',
            'receipt_header', 'receipt_footer', 'receipt_printer_ip',
            'kitchen_printer_ip', 'cash_drawer_enabled',
            'has_active_session', 'current_session_id', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class POSTerminalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating POSTerminal."""
    
    class Meta:
        model = POSTerminal
        fields = [
            'name', 'code', 'description', 'floor', 'is_active',
            'default_customer_display', 'default_kitchen_display',
            'receipt_header', 'receipt_footer', 'receipt_printer_ip',
            'kitchen_printer_ip', 'cash_drawer_enabled',
        ]
    
    def validate_code(self, value):
        if POSTerminal.objects.filter(code=value, is_deleted=False).exists():
            raise serializers.ValidationError('Terminal with this code already exists.')
        return value


class CashMovementSerializer(serializers.ModelSerializer):
    """Serializer for CashMovement."""
    
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = CashMovement
        fields = [
            'id', 'session', 'movement_type', 'amount', 'reason', 'notes',
            'performed_by', 'performed_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'performed_by', 'created_at']


class POSSessionSerializer(serializers.ModelSerializer):
    """Serializer for POSSession."""
    
    terminal_name = serializers.CharField(source='terminal.name', read_only=True)
    responsible_user_name = serializers.CharField(
        source='responsible_user.get_full_name',
        read_only=True
    )
    total_sales = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    order_count = serializers.IntegerField(read_only=True)
    cash_total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = POSSession
        fields = [
            'id', 'terminal', 'terminal_name', 'responsible_user',
            'responsible_user_name', 'name', 'opening_time', 'closing_time',
            'opening_balance', 'closing_balance', 'expected_closing_balance',
            'cash_difference', 'status', 'is_active', 'opening_notes',
            'closing_notes', 'total_sales', 'order_count', 'cash_total',
            'created_at',
        ]
        read_only_fields = [
            'id', 'name', 'expected_closing_balance', 'cash_difference',
            'closing_time', 'created_at',
        ]


class POSSessionDetailSerializer(POSSessionSerializer):
    """Detailed session serializer with cash movements."""
    
    cash_movements = CashMovementSerializer(many=True, read_only=True)
    
    class Meta(POSSessionSerializer.Meta):
        fields = POSSessionSerializer.Meta.fields + ['cash_movements']


class OpenSessionSerializer(serializers.Serializer):
    """Serializer for opening a new session."""
    
    terminal_id = serializers.UUIDField()
    opening_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    opening_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_terminal_id(self, value):
        try:
            terminal = POSTerminal.objects.get(id=value, is_active=True, is_deleted=False)
        except POSTerminal.DoesNotExist:
            raise serializers.ValidationError('Terminal not found or inactive.')
        
        if terminal.has_active_session:
            raise serializers.ValidationError('Terminal already has an active session.')
        
        return value
    
    def create(self, validated_data):
        session = POSSession.objects.create(
            terminal_id=validated_data['terminal_id'],
            responsible_user=self.context['request'].user,
            opening_balance=validated_data['opening_balance'],
            opening_notes=validated_data.get('opening_notes', ''),
        )
        return session


class CloseSessionSerializer(serializers.Serializer):
    """Serializer for closing a session."""
    
    closing_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    closing_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        session = self.context.get('session')
        if not session:
            raise serializers.ValidationError('Session not found.')
        
        if not session.is_active:
            raise serializers.ValidationError('Session is already closed.')
        
        # Check for unpaid orders
        unpaid_orders = session.orders.filter(
            status='sent_to_kitchen',
            is_deleted=False
        ).count()
        
        if unpaid_orders > 0:
            raise serializers.ValidationError(
                f'Cannot close session with {unpaid_orders} unpaid order(s).'
            )
        
        return attrs


class SessionSummarySerializer(serializers.Serializer):
    """Serializer for session summary/report."""
    
    session_id = serializers.UUIDField()
    session_name = serializers.CharField()
    terminal_name = serializers.CharField()
    responsible_user = serializers.CharField()
    
    opening_time = serializers.DateTimeField()
    closing_time = serializers.DateTimeField()
    duration_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    opening_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    closing_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    expected_closing_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    cash_difference = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    total_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_count = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    payment_breakdown = serializers.DictField()
    top_products = serializers.ListField()
