"""
Serializers for floor and table management.
"""

from rest_framework import serializers
from .models import Floor, Table, TableReservation


class TableSerializer(serializers.ModelSerializer):
    """Serializer for Table model."""
    
    display_name = serializers.CharField(read_only=True)
    floor_name = serializers.CharField(source='floor.name', read_only=True)
    current_order_number = serializers.CharField(
        source='current_order.order_number',
        read_only=True
    )
    
    class Meta:
        model = Table
        fields = [
            'id', 'floor', 'floor_name', 'table_number', 'name', 'display_name',
            'seats', 'min_seats', 'position_x', 'position_y', 'width', 'height',
            'shape', 'color', 'is_active', 'is_occupied', 'current_order',
            'current_order_number', 'appointment_resource_id', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_occupied', 'current_order']


class TableCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tables."""
    
    class Meta:
        model = Table
        fields = [
            'floor', 'table_number', 'name', 'seats', 'min_seats',
            'position_x', 'position_y', 'width', 'height', 'shape', 'color',
            'is_active', 'appointment_resource_id',
        ]
    
    def validate(self, attrs):
        floor = attrs.get('floor')
        table_number = attrs.get('table_number')
        
        # Check for duplicate table number on same floor
        if Table.objects.filter(
            floor=floor,
            table_number=table_number,
            is_deleted=False
        ).exists():
            raise serializers.ValidationError({
                'table_number': f'Table {table_number} already exists on this floor.'
            })
        
        return attrs


class FloorSerializer(serializers.ModelSerializer):
    """Serializer for Floor model."""
    
    table_count = serializers.IntegerField(read_only=True)
    available_tables = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Floor
        fields = [
            'id', 'name', 'description', 'display_order',
            'background_image', 'background_color', 'is_active',
            'table_count', 'available_tables', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FloorWithTablesSerializer(FloorSerializer):
    """Serializer for Floor with nested tables."""
    
    tables = TableSerializer(many=True, read_only=True)
    
    class Meta(FloorSerializer.Meta):
        fields = FloorSerializer.Meta.fields + ['tables']


class TableReservationSerializer(serializers.ModelSerializer):
    """Serializer for table reservations."""
    
    table_display = serializers.CharField(source='table.__str__', read_only=True)
    
    class Meta:
        model = TableReservation
        fields = [
            'id', 'table', 'table_display', 'customer_name', 'customer_phone',
            'customer_email', 'party_size', 'reservation_date', 'reservation_time',
            'duration_minutes', 'status', 'notes', 'order', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'order']
    
    def validate(self, attrs):
        table = attrs.get('table')
        reservation_date = attrs.get('reservation_date')
        reservation_time = attrs.get('reservation_time')
        duration = attrs.get('duration_minutes', 120)
        
        # Check for overlapping reservations
        from datetime import datetime, timedelta
        
        start_time = datetime.combine(reservation_date, reservation_time)
        end_time = start_time + timedelta(minutes=duration)
        
        overlapping = TableReservation.objects.filter(
            table=table,
            reservation_date=reservation_date,
            status__in=['pending', 'confirmed'],
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        for reservation in overlapping:
            res_start = datetime.combine(
                reservation.reservation_date,
                reservation.reservation_time
            )
            res_end = res_start + timedelta(minutes=reservation.duration_minutes)
            
            if start_time < res_end and end_time > res_start:
                raise serializers.ValidationError({
                    'reservation_time': 'This time slot overlaps with an existing reservation.'
                })
        
        return attrs


class TableStatusSerializer(serializers.Serializer):
    """Serializer for table status display (POS floor view)."""
    
    id = serializers.UUIDField()
    table_number = serializers.CharField()
    display_name = serializers.CharField()
    seats = serializers.IntegerField()
    is_occupied = serializers.BooleanField()
    position_x = serializers.IntegerField()
    position_y = serializers.IntegerField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    shape = serializers.CharField()
    color = serializers.CharField()
    
    # Order info if occupied
    order_id = serializers.UUIDField(source='current_order.id', allow_null=True)
    order_number = serializers.CharField(source='current_order.order_number', allow_null=True)
    order_total = serializers.DecimalField(
        source='current_order.total_amount',
        max_digits=10,
        decimal_places=2,
        allow_null=True
    )
    order_duration = serializers.SerializerMethodField()
    
    def get_order_duration(self, obj):
        if obj.current_order:
            from django.utils import timezone
            duration = timezone.now() - obj.current_order.created_at
            return int(duration.total_seconds() / 60)  # Minutes
        return None
