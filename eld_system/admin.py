from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Driver, Vehicle, Shipper, Load, Trip, RouteWaypoint,
    ELDLogSheet, DutyStatusPeriod, HOSCycleTracking,
    FuelStop, RestBreak
)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['driver_number', 'get_full_name', 'initials', 'home_operating_center', 'license_state', 'created_at']
    list_filter = ['home_operating_center', 'license_state', 'created_at']
    search_fields = ['driver_number', 'user__first_name', 'user__last_name', 'initials']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'driver_number', 'initials')
        }),
        ('License Information', {
            'fields': ('license_number', 'license_state')
        }),
        ('Company Information', {
            'fields': ('home_operating_center', 'signature')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else "No Name"
    get_full_name.short_description = 'Full Name'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['vehicle_number', 'vehicle_type', 'make', 'model', 'year', 'is_active', 'created_at']
    list_filter = ['vehicle_type', 'is_active', 'make', 'created_at']
    search_fields = ['vehicle_number', 'make', 'model', 'vin']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Vehicle Identification', {
            'fields': ('vehicle_number', 'vehicle_type', 'vin')
        }),
        ('Vehicle Details', {
            'fields': ('make', 'model', 'year', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Shipper)
class ShipperAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'contact_phone', 'contact_email']
    list_filter = ['state', 'city']
    search_fields = ['name', 'city', 'contact_phone', 'contact_email']

    fieldsets = (
        ('Company Information', {
            'fields': ('name',)
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
        ('Contact Information', {
            'fields': ('contact_phone', 'contact_email')
        }),
    )


@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display = ['load_id', 'shipper', 'commodity', 'weight', 'pieces', 'created_at']
    list_filter = ['shipper', 'commodity', 'created_at']
    search_fields = ['load_id', 'commodity', 'shipper__name']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Load Identification', {
            'fields': ('load_id', 'shipper')
        }),
        ('Load Details', {
            'fields': ('commodity', 'weight', 'pieces', 'special_instructions')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class RouteWaypointInline(admin.TabularInline):
    model = RouteWaypoint
    extra = 0
    fields = ['sequence', 'location_name', 'waypoint_type', 'latitude', 'longitude', 'estimated_arrival']
    ordering = ['sequence']


class FuelStopInline(admin.TabularInline):
    model = FuelStop
    extra = 0
    fields = ['location', 'miles_from_start', 'estimated_time', 'fuel_needed', 'completed']
    ordering = ['miles_from_start']


class RestBreakInline(admin.TabularInline):
    model = RestBreak
    extra = 0
    fields = ['break_type', 'location', 'scheduled_start', 'scheduled_end', 'completed']
    ordering = ['scheduled_start']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['trip_id', 'driver', 'get_route', 'status', 'current_cycle_used_hours', 'total_estimated_miles', 'created_at']
    list_filter = ['status', 'driver__home_operating_center', 'created_at']
    search_fields = ['trip_id', 'driver__driver_number', 'pickup_location', 'dropoff_location']
    readonly_fields = ['trip_id', 'created_at', 'updated_at']
    inlines = [RouteWaypointInline, FuelStopInline, RestBreakInline]

    fieldsets = (
        ('Trip Information', {
            'fields': ('trip_id', 'driver', 'status')
        }),
        ('Vehicle Assignment', {
            'fields': ('tractor', 'trailer', 'load')
        }),
        ('Route Details', {
            'fields': (
                ('current_location', 'current_lat', 'current_lng'),
                ('pickup_location', 'pickup_lat', 'pickup_lng'),
                ('dropoff_location', 'dropoff_lat', 'dropoff_lng')
            )
        }),
        ('Hours of Service', {
            'fields': ('current_cycle_used_hours',)
        }),
        ('Timing', {
            'fields': ('start_time', 'estimated_end_time', 'actual_end_time')
        }),
        ('Mileage', {
            'fields': ('total_estimated_miles', 'total_actual_miles')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_route(self, obj):
        return f"{obj.pickup_location} → {obj.dropoff_location}"
    get_route.short_description = 'Route'


@admin.register(RouteWaypoint)
class RouteWaypointAdmin(admin.ModelAdmin):
    list_display = ['trip', 'sequence', 'location_name', 'waypoint_type', 'estimated_arrival', 'actual_arrival']
    list_filter = ['waypoint_type', 'trip__status']
    search_fields = ['location_name', 'trip__trip_id']
    ordering = ['trip', 'sequence']


class DutyStatusPeriodInline(admin.TabularInline):
    model = DutyStatusPeriod
    extra = 0
    fields = ['duty_status', 'start_time', 'end_time', 'location', 'activity_description', 'vehicle_moved']
    ordering = ['start_time']


@admin.register(ELDLogSheet)
class ELDLogSheetAdmin(admin.ModelAdmin):
    list_display = ['date', 'driver', 'get_trip_info', 'total_driving_time', 'total_duty_time', 'miles_driven', 'hos_violation']
    list_filter = ['date', 'driver__home_operating_center', 'hos_violation']
    search_fields = ['driver__driver_number', 'trip__trip_id']
    readonly_fields = ['created_at', 'updated_at', 'get_total_hours_check', 'get_compliance_status']
    inlines = [DutyStatusPeriodInline]
    date_hierarchy = 'date'

    fieldsets = (
        ('Log Information', {
            'fields': ('trip', 'driver', 'date')
        }),
        ('Duty Status Totals', {
            'fields': (
                ('total_off_duty_time', 'total_sleeper_berth_time'),
                ('total_driving_time', 'total_on_duty_time'),
                'total_duty_time', 'miles_driven'
            )
        }),
        ('Compliance', {
            'fields': ('hos_violation', 'violation_notes', 'get_total_hours_check', 'get_compliance_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_trip_info(self, obj):
        if obj.trip:
            return f"Trip {obj.trip.trip_id}"
        return "No Trip"
    get_trip_info.short_description = 'Trip'

    def get_total_hours_check(self, obj):
        total = (obj.total_off_duty_time + obj.total_sleeper_berth_time +
                obj.total_driving_time + obj.total_on_duty_time)
        color = "green" if abs(total - 24) < 0.01 else "red"
        return format_html(
            '<span style="color: {};">{:.2f} hours</span>',
            color, total
        )
    get_total_hours_check.short_description = '24-Hour Check'

    def get_compliance_status(self, obj):
        issues = []
        if obj.total_driving_time > 11:
            issues.append("Exceeds 11-hour driving limit")
        if obj.total_duty_time > 14:
            issues.append("Exceeds 14-hour duty limit")
        if obj.hos_violation:
            issues.append("HOS Violation Flagged")

        if not issues:
            return format_html('<span style="color: green;">✓ Compliant</span>')
        else:
            return format_html('<span style="color: red;">⚠ {}</span>', "; ".join(issues))
    get_compliance_status.short_description = 'Compliance Status'


@admin.register(DutyStatusPeriod)
class DutyStatusPeriodAdmin(admin.ModelAdmin):
    list_display = ['log_sheet', 'duty_status', 'start_time', 'end_time', 'location', 'get_duration', 'vehicle_moved']
    list_filter = ['duty_status', 'vehicle_moved', 'log_sheet__date']
    search_fields = ['location', 'city', 'activity_description', 'log_sheet__driver__driver_number']
    ordering = ['log_sheet', 'start_time']

    fieldsets = (
        ('Period Information', {
            'fields': ('log_sheet', 'duty_status')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'grid_start_minute', 'grid_end_minute')
        }),
        ('Location', {
            'fields': ('location', 'city', 'state')
        }),
        ('Activity Details', {
            'fields': ('activity_description', 'vehicle_moved')
        }),
    )

    def get_duration(self, obj):
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return f"{hours:.2f} hours"
        return "Unknown"
    get_duration.short_description = 'Duration'


@admin.register(HOSCycleTracking)
class HOSCycleTrackingAdmin(admin.ModelAdmin):
    list_display = ['driver', 'cycle_start_date', 'cycle_end_date', 'total_cycle_hours', 'remaining_hours', 'is_violation', 'restart_available']
    list_filter = ['is_violation', 'restart_available', 'cycle_start_date']
    search_fields = ['driver__driver_number', 'violation_type']
    readonly_fields = ['created_at', 'updated_at', 'get_cycle_status']
    date_hierarchy = 'cycle_start_date'

    fieldsets = (
        ('Cycle Information', {
            'fields': ('driver', 'cycle_start_date', 'cycle_end_date')
        }),
        ('Hours Tracking', {
            'fields': ('total_cycle_hours', 'remaining_hours')
        }),
        ('Violations', {
            'fields': ('is_violation', 'violation_type', 'violation_details')
        }),
        ('34-Hour Restart', {
            'fields': ('restart_available', 'restart_start_time', 'restart_end_time')
        }),
        ('Status', {
            'fields': ('get_cycle_status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_cycle_status(self, obj):
        if obj.is_violation:
            return format_html('<span style="color: red;">⚠ VIOLATION</span>')
        elif obj.remaining_hours <= 5:
            return format_html('<span style="color: orange;">⚠ Low Hours Remaining</span>')
        elif obj.restart_available:
            return format_html('<span style="color: blue;">🔄 Restart Available</span>')
        else:
            return format_html('<span style="color: green;">✓ Normal</span>')
    get_cycle_status.short_description = 'Status'


@admin.register(FuelStop)
class FuelStopAdmin(admin.ModelAdmin):
    list_display = ['trip', 'location', 'miles_from_start', 'estimated_time', 'fuel_needed', 'completed']
    list_filter = ['fuel_needed', 'completed', 'trip__status']
    search_fields = ['location', 'trip__trip_id']
    ordering = ['trip', 'miles_from_start']


@admin.register(RestBreak)
class RestBreakAdmin(admin.ModelAdmin):
    list_display = ['trip', 'break_type', 'location', 'scheduled_start', 'scheduled_end', 'completed']
    list_filter = ['break_type', 'completed', 'trip__status']
    search_fields = ['location', 'trip__trip_id']
    ordering = ['trip', 'scheduled_start']
