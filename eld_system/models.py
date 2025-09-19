from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class Driver(models.Model):
    """
    Driver information.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    driver_number = models.CharField(max_length=20, unique=True)
    initials = models.CharField(max_length=5)
    signature = models.TextField(blank=True, help_text="Digital signature or signature image path")
    home_operating_center = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50)
    license_state = models.CharField(max_length=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.driver_number} - {self.user.get_full_name()}"


class Vehicle(models.Model):
    """
    Vehicle information for tractors and trailers.
    """
    VEHICLE_TYPES = [
        ('tractor', 'Tractor'),
        ('trailer', 'Trailer'),
    ]

    vehicle_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPES)
    make = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    vin = models.CharField(max_length=17, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_type.title()} {self.vehicle_number}"


class Shipper(models.Model):
    """
    Shipper/Company information for loads as required by ELD regulations.
    """
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Load(models.Model):
    """
    Load information.
    """
    load_id = models.CharField(max_length=50, unique=True)
    shipper = models.ForeignKey(Shipper, on_delete=models.CASCADE)
    commodity = models.CharField(max_length=200, help_text="e.g., paper products")
    weight = models.PositiveIntegerField(help_text="Weight in pounds", blank=True, null=True)
    pieces = models.PositiveIntegerField(blank=True, null=True)
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Load {self.load_id} - {self.commodity}"


class Trip(models.Model):
    """
    Enhanced Trip model with route planning and ELD compliance data.
    """
    trip_id = models.UUIDField(default=uuid.uuid4, unique=True)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    tractor = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='trips_as_tractor',
        limit_choices_to={'vehicle_type': 'tractor'}
    )
    trailer = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trips_as_trailer',
        limit_choices_to={'vehicle_type': 'trailer'}
    )
    load = models.ForeignKey(Load, on_delete=models.SET_NULL, null=True, blank=True)
    current_location = models.CharField(max_length=255)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    pickup_location = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_location = models.CharField(max_length=255)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_cycle_used_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('70'))]
    )
    start_time = models.DateTimeField()
    estimated_end_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    total_estimated_miles = models.PositiveIntegerField(default=0)
    total_actual_miles = models.PositiveIntegerField(default=0)
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {self.trip_id} - {self.pickup_location} to {self.dropoff_location}"


class RouteWaypoint(models.Model):
    """
    Waypoints for route planning and map display.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='waypoints')
    sequence = models.PositiveIntegerField()
    location_name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    WAYPOINT_TYPES = [
        ('route', 'Route Point'),
        ('fuel', 'Fuel Stop'),
        ('rest', 'Rest Area'),
        ('checkpoint', 'Checkpoint'),
    ]
    waypoint_type = models.CharField(max_length=20, choices=WAYPOINT_TYPES, default='route')

    class Meta:
        ordering = ['trip', 'sequence']
        unique_together = ['trip', 'sequence']

    def __str__(self):
        return f"Waypoint {self.sequence}: {self.location_name}"


class ELDLogSheet(models.Model):
    """
    Daily log sheet.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='log_sheets')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    date = models.DateField()
    total_off_duty_time = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('0'),
        help_text="Line 1 total hours"
    )
    total_sleeper_berth_time = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('0'),
        help_text="Line 2 total hours"
    )
    total_driving_time = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('0'),
        help_text="Line 3 total hours"
    )
    total_on_duty_time = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('0'),
        help_text="Line 4 total hours"
    )
    total_duty_time = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('0'),
        help_text="Driving + On Duty time"
    )
    miles_driven = models.PositiveIntegerField(default=0)
    hos_violation = models.BooleanField(default=False)
    violation_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['driver', 'date']

    def __str__(self):
        return f"Log Sheet {self.date} - {self.driver.driver_number}"


class DutyStatusPeriod(models.Model):
    """
    Individual duty status periods for drawing the ELD log grid.
    """
    log_sheet = models.ForeignKey(ELDLogSheet, on_delete=models.CASCADE, related_name='duty_periods')

    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty (Line 1)'),
        ('sleeper_berth', 'Sleeper Berth (Line 2)'),
        ('driving', 'Driving (Line 3)'),
        ('on_duty', 'On Duty Not Driving (Line 4)'),
    ]

    duty_status = models.CharField(max_length=20, choices=DUTY_STATUS_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    activity_description = models.CharField(
        max_length=200,
        help_text="e.g., pre-trip inspection, fueling, 30-min break"
    )
    vehicle_moved = models.BooleanField(
        default=True,
        help_text="False for bracketed periods where truck didn't move"
    )
    grid_start_minute = models.PositiveIntegerField(
        help_text="Start position in 15-minute increments from midnight (0-1439)"
    )
    grid_end_minute = models.PositiveIntegerField(
        help_text="End position in 15-minute increments from midnight (0-1439)"
    )

    class Meta:
        ordering = ['log_sheet', 'start_time']

    def __str__(self):
        return f"{self.duty_status} from {self.start_time} to {self.end_time}"


class HOSCycleTracking(models.Model):
    """
    Hours of Service cycle tracking for regulatory compliance.
    Tracks 70 hours / 8 days rule and violations.
    """
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    cycle_start_date = models.DateField()
    cycle_end_date = models.DateField()
    total_cycle_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('70'))]
    )
    remaining_hours = models.DecimalField(max_digits=4, decimal_places=2)
    is_violation = models.BooleanField(default=False)
    violation_type = models.CharField(max_length=50, blank=True)
    violation_details = models.TextField(blank=True)
    restart_available = models.BooleanField(default=False)
    restart_start_time = models.DateTimeField(null=True, blank=True)
    restart_end_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['driver', 'cycle_start_date']

    def __str__(self):
        return f"HOS Cycle {self.cycle_start_date} - {self.driver.driver_number}"


class FuelStop(models.Model):
    """
    Fuel stops as required by the assessment (every 1,000 miles).
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='fuel_stops')
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estimated_time = models.DateTimeField()
    actual_time = models.DateTimeField(null=True, blank=True)
    miles_from_start = models.PositiveIntegerField()
    fuel_needed = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['trip', 'miles_from_start']

    def __str__(self):
        return f"Fuel Stop at {self.location} ({self.miles_from_start} miles)"


class RestBreak(models.Model):
    """
    Mandatory rest breaks and 30-minute breaks as per HOS regulations.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='rest_breaks')

    BREAK_TYPES = [
        ('30_min', '30-Minute Break'),
        ('10_hour', '10-Hour Rest'),
        ('34_hour', '34-Hour Restart'),
    ]

    break_type = models.CharField(max_length=10, choices=BREAK_TYPES)
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['trip', 'scheduled_start']

    def __str__(self):
        return f"{self.break_type} at {self.location}"
