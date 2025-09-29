from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Driver, Vehicle, Shipper, Load, Trip, RouteWaypoint,
    ELDLogSheet, DutyStatusPeriod, HOSCycleTracking,
    FuelStop, RestBreak
)


class UserSerializer(serializers.ModelSerializer):
    """User model serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer with password handling and optional driver creation"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    # Optional driver fields
    driver_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    initials = serializers.CharField(max_length=5, required=False, allow_blank=True)
    home_operating_center = serializers.CharField(max_length=100, required=False, allow_blank=True)
    license_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    license_state = serializers.CharField(max_length=2, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password', 'password_confirm',
            'driver_number', 'initials', 'home_operating_center', 'license_number', 'license_state'
        ]

    def validate(self, attrs):
        """Validate password confirmation and driver fields"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")

        # Check email uniqueness
        email = attrs.get('email')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists")

        # If any driver field is provided, validate driver number uniqueness
        driver_fields = ['driver_number', 'initials', 'home_operating_center', 'license_number', 'license_state']
        if any(attrs.get(field) for field in driver_fields):
            driver_number = attrs.get('driver_number')
            if not driver_number:
                raise serializers.ValidationError("Driver number is required when creating driver profile")

            # Check if driver number already exists
            from .models import Driver
            if Driver.objects.filter(driver_number=driver_number).exists():
                raise serializers.ValidationError("Driver number already exists")

        return attrs

    def create(self, validated_data):
        """Create user with encrypted password and optional driver profile"""
        # Remove non-user fields
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        # Extract driver fields
        driver_fields = {}
        for field in ['driver_number', 'initials', 'home_operating_center', 'license_number', 'license_state']:
            if field in validated_data and validated_data[field]:
                driver_fields[field] = validated_data.pop(field)

        # Create user
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        # Create driver profile if driver fields provided
        if driver_fields:
            from .models import Driver
            Driver.objects.create(user=user, **driver_fields)

        return user
class DriverSerializer(serializers.ModelSerializer):
    """
    Driver serializer.
    """
    user = UserSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = [
            'id', 'user', 'driver_number', 'initials', 'signature',
            'home_operating_center', 'license_number', 'license_state',
            'full_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else ""


class DriverCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating drivers with user data.
    """
    user_data = UserSerializer(write_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'driver_number', 'initials', 'signature', 'home_operating_center',
            'license_number', 'license_state', 'user_data'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        user_data = validated_data.pop('user_data')
        user = User.objects.create_user(**user_data)
        driver = Driver.objects.create(user=user, **validated_data)
        return driver


class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for Vehicle model (trucks and trailers)"""

    class Meta:
        model = Vehicle
        fields = [
            'id', 'vehicle_number', 'vehicle_type', 'make', 'model',
            'year', 'vin', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ShipperSerializer(serializers.ModelSerializer):
    """Serializer for Shipper/Company information"""

    class Meta:
        model = Shipper
        fields = [
            'id', 'name', 'address', 'city', 'state', 'zip_code',
            'contact_phone', 'contact_email'
        ]
        read_only_fields = ['id']


class LoadSerializer(serializers.ModelSerializer):
    """Serializer for Load information with shipper details"""
    shipper = ShipperSerializer(read_only=True)
    shipper_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Load
        fields = [
            'id', 'load_id', 'shipper', 'shipper_id', 'commodity',
            'weight', 'pieces', 'special_instructions', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RouteWaypointSerializer(serializers.ModelSerializer):
    """Serializer for route waypoints and stops"""

    class Meta:
        model = RouteWaypoint
        fields = [
            'id', 'sequence', 'location_name', 'latitude', 'longitude',
            'estimated_arrival', 'actual_arrival', 'waypoint_type'
        ]
        read_only_fields = ['id']


class FuelStopSerializer(serializers.ModelSerializer):
    """Serializer for fuel stops"""

    class Meta:
        model = FuelStop
        fields = [
            'id', 'location', 'latitude', 'longitude', 'estimated_time',
            'actual_time', 'miles_from_start', 'fuel_needed', 'completed'
        ]
        read_only_fields = ['id']


class RestBreakSerializer(serializers.ModelSerializer):
    """Serializer for mandatory rest breaks"""

    class Meta:
        model = RestBreak
        fields = [
            'id', 'break_type', 'location', 'latitude', 'longitude',
            'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
            'completed', 'notes'
        ]
        read_only_fields = ['id']


class TripSerializer(serializers.ModelSerializer):
    """
    Trip serializer with all related data.
    """
    driver = DriverSerializer(read_only=True)
    driver_id = serializers.IntegerField(write_only=True)
    truck = VehicleSerializer(read_only=True)
    truck_id = serializers.IntegerField(write_only=True)
    trailer = VehicleSerializer(read_only=True)
    trailer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    load = LoadSerializer(read_only=True)
    load_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    waypoints = RouteWaypointSerializer(many=True, read_only=True)
    fuel_stops = FuelStopSerializer(many=True, read_only=True)
    rest_breaks = RestBreakSerializer(many=True, read_only=True)
    estimated_duration_hours = serializers.SerializerMethodField()
    estimated_fuel_stops_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id', 'trip_id', 'driver', 'driver_id', 'truck', 'truck_id',
            'trailer', 'trailer_id', 'load', 'load_id',
            'current_location', 'current_lat', 'current_lng',
            'pickup_location', 'pickup_lat', 'pickup_lng',
            'dropoff_location', 'dropoff_lat', 'dropoff_lng',
            'current_cycle_used_hours', 'start_time', 'estimated_end_time',
            'actual_end_time', 'total_estimated_miles', 'total_actual_miles',
            'status',
            'waypoints', 'fuel_stops', 'rest_breaks',
            'estimated_duration_hours', 'estimated_fuel_stops_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'trip_id', 'created_at', 'updated_at']

    def get_estimated_duration_hours(self, obj):
        """Calculate estimated trip duration in hours"""
        if obj.start_time and obj.estimated_end_time:
            duration = obj.estimated_end_time - obj.start_time
            return round(duration.total_seconds() / 3600, 2)
        return None

    def get_estimated_fuel_stops_count(self, obj):
        """Calculate number of fuel stops based on 1,000 mile rule"""
        if obj.total_estimated_miles > 0:
            return (obj.total_estimated_miles // 1000) + 1
        return 0


class TripCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating trips with assessment inputs.
    """

    class Meta:
        model = Trip
        fields = [
            'driver_id', 'truck_id', 'trailer_id', 'load_id',
            'current_location', 'pickup_location', 'dropoff_location',
            'current_cycle_used_hours', 'start_time'
        ]

    def validate_current_cycle_used_hours(self, value):
        """Ensure cycle hours are within valid range (0-70)"""
        if value < 0 or value > 70:
            raise serializers.ValidationError(
                "Current cycle used hours must be between 0 and 70."
            )
        return value


class DutyStatusPeriodSerializer(serializers.ModelSerializer):
    """
    Serializer for individual duty status periods.
    """
    duration_minutes = serializers.SerializerMethodField()
    # Allow creating periods by passing the parent log sheet id
    log_sheet_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = DutyStatusPeriod
        fields = [
            'id', 'log_sheet_id', 'duty_status', 'start_time', 'end_time', 'location',
            'city', 'state', 'activity_description', 'vehicle_moved',
            'grid_start_minute', 'grid_end_minute', 'duration_minutes',
            'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        log_sheet_id = validated_data.pop('log_sheet_id')
        from .models import ELDLogSheet
        validated_data['log_sheet'] = ELDLogSheet.objects.get(pk=log_sheet_id)
        return super().create(validated_data)

    def get_duration_minutes(self, obj):
        """Calculate duration in minutes for the period"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            return int(duration.total_seconds() / 60)
        return 0


class ELDLogSheetSerializer(serializers.ModelSerializer):
    """
    ELD Log Sheet serializer.
    """
    driver = DriverSerializer(read_only=True)
    driver_id = serializers.IntegerField(write_only=True, required=True)
    trip = serializers.StringRelatedField(read_only=True)
    trip_id = serializers.IntegerField(write_only=True, required=True)
    duty_periods = DutyStatusPeriodSerializer(many=True, read_only=True)
    total_hours_check = serializers.SerializerMethodField()
    is_24_hour_total = serializers.SerializerMethodField()
    hos_compliant = serializers.SerializerMethodField()

    class Meta:
        model = ELDLogSheet
        fields = [
            'id', 'trip', 'trip_id', 'driver', 'driver_id', 'date',
            'total_off_duty_time', 'total_sleeper_berth_time',
            'total_driving_time', 'total_on_duty_time',
            'total_duty_time', 'miles_driven',
            'hos_violation', 'violation_notes',
            'duty_periods',
            'total_hours_check', 'is_24_hour_total', 'hos_compliant',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    def create(self, validated_data):
        driver_id = validated_data.pop('driver_id')
        trip_id = validated_data.pop('trip_id')
        validated_data['driver'] = Driver.objects.get(pk=driver_id)
        validated_data['trip'] = Trip.objects.get(pk=trip_id)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        driver_id = validated_data.pop('driver_id', None)
        trip_id = validated_data.pop('trip_id', None)
        if driver_id is not None:
            validated_data['driver'] = Driver.objects.get(pk=driver_id)
        if trip_id is not None:
            validated_data['trip'] = Trip.objects.get(pk=trip_id)
        return super().update(instance, validated_data)

    def get_total_hours_check(self, obj):
        """Verify that all duty times add up to 24 hours"""
        total = (obj.total_off_duty_time + obj.total_sleeper_berth_time +
                obj.total_driving_time + obj.total_on_duty_time)
        return float(total)

    def get_is_24_hour_total(self, obj):
        """Check if daily hours total exactly 24"""
        total = self.get_total_hours_check(obj)
        return abs(total - 24.0) < 0.01

    def get_hos_compliant(self, obj):
        """Basic HOS compliance check"""
        if obj.total_driving_time > 11:
            return False
        if obj.total_duty_time > 14:
            return False
        return not obj.hos_violation


class HOSCycleTrackingSerializer(serializers.ModelSerializer):
    """
    Serializer for Hours of Service cycle tracking.
    """
    driver = DriverSerializer(read_only=True)
    days_in_cycle = serializers.SerializerMethodField()
    hours_available_today = serializers.SerializerMethodField()

    class Meta:
        model = HOSCycleTracking
        fields = [
            'id', 'driver', 'cycle_start_date', 'cycle_end_date',
            'total_cycle_hours', 'remaining_hours', 'is_violation',
            'violation_type', 'violation_details', 'restart_available',
            'restart_start_time', 'restart_end_time', 'days_in_cycle',
            'hours_available_today', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_days_in_cycle(self, obj):
        """Calculate number of days in current cycle"""
        if obj.cycle_start_date and obj.cycle_end_date:
            return (obj.cycle_end_date - obj.cycle_start_date).days + 1
        return 0

    def get_hours_available_today(self, obj):
        """Calculate how many hours driver can work today"""
        return max(0, float(obj.remaining_hours))


class TripPlanningInputSerializer(serializers.Serializer):
    """
    Serializer for the assessment's required inputs.
    """
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    current_cycle_used_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=70
    )
    driver_id = serializers.IntegerField()
    truck_id = serializers.IntegerField()
    trailer_id = serializers.IntegerField(required=False, allow_null=True)
    load_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        """Validate that the driver and vehicles exist"""
        try:
            Driver.objects.get(id=data['driver_id'])
        except Driver.DoesNotExist:
            raise serializers.ValidationError("Driver does not exist")

        try:
            truck = Vehicle.objects.get(id=data['truck_id'])
            if truck.vehicle_type != 'truck':
                raise serializers.ValidationError("Selected vehicle is not a truck")
        except Vehicle.DoesNotExist:
            raise serializers.ValidationError("Tractor does not exist")

        if data.get('trailer_id'):
            try:
                trailer = Vehicle.objects.get(id=data['trailer_id'])
                if trailer.vehicle_type != 'trailer':
                    raise serializers.ValidationError("Selected vehicle is not a trailer")
            except Vehicle.DoesNotExist:
                raise serializers.ValidationError("Trailer does not exist")

        return data


class TripOutputSerializer(serializers.Serializer):
    """
    Serializer for the assessment's required outputs.
    """
    trip = TripSerializer(read_only=True)
    route_waypoints = RouteWaypointSerializer(many=True, read_only=True)
    fuel_stops = FuelStopSerializer(many=True, read_only=True)
    rest_breaks = RestBreakSerializer(many=True, read_only=True)
    log_sheets = ELDLogSheetSerializer(many=True, read_only=True)
    total_estimated_duration = serializers.CharField(read_only=True)
    estimated_arrival = serializers.DateTimeField(read_only=True)
    compliance_warnings = serializers.ListField(read_only=True)
    map_bounds = serializers.DictField(read_only=True)
