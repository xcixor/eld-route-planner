from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    Driver, Vehicle, Shipper, Load, Trip, RouteWaypoint,
    ELDLogSheet, DutyStatusPeriod, HOSCycleTracking,
    FuelStop, RestBreak
)
from .serializers import (
    DriverSerializer, DriverCreateSerializer, VehicleSerializer,
    ShipperSerializer, LoadSerializer, TripSerializer, TripCreateSerializer,
    RouteWaypointSerializer, ELDLogSheetSerializer, DutyStatusPeriodSerializer,
    HOSCycleTrackingSerializer, FuelStopSerializer, RestBreakSerializer,
    TripPlanningInputSerializer, TripOutputSerializer
)


class DriverViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing drivers.
    Supports CRUD operations and driver-specific queries.
    """
    queryset = Driver.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DriverCreateSerializer
        return DriverSerializer

    @action(detail=True, methods=['get'])
    def trips(self, request, pk=None):
        """Get all trips for a specific driver"""
        driver = self.get_object()
        trips = Trip.objects.filter(driver=driver)
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def current_hos_status(self, request, pk=None):
        """Get current Hours of Service status for driver"""
        driver = self.get_object()
        current_cycle = HOSCycleTracking.objects.filter(
            driver=driver,
            cycle_start_date__lte=datetime.now().date(),
            cycle_end_date__gte=datetime.now().date()
        ).first()

        if current_cycle:
            serializer = HOSCycleTrackingSerializer(current_cycle)
            return Response(serializer.data)
        else:
            return Response({
                'message': 'No active HOS cycle found',
                'available_hours': 70.0
            })


class VehicleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicles (tractors and trailers).
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Vehicle.objects.all()
        vehicle_type = self.request.query_params.get('type', None)
        is_active = self.request.query_params.get('active', None)

        if vehicle_type:
            queryset = queryset.filter(vehicle_type=vehicle_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    @action(detail=False, methods=['get'])
    def available_tractors(self, request):
        """Get available tractors for assignment"""
        tractors = Vehicle.objects.filter(
            vehicle_type='tractor',
            is_active=True
        )
        serializer = VehicleSerializer(tractors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available_trailers(self, request):
        """Get available trailers for assignment"""
        trailers = Vehicle.objects.filter(
            vehicle_type='trailer',
            is_active=True
        )
        serializer = VehicleSerializer(trailers, many=True)
        return Response(serializer.data)


class ShipperViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shippers/companies.
    """
    queryset = Shipper.objects.all()
    serializer_class = ShipperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Shipper.objects.all()
        state = self.request.query_params.get('state', None)

        if state:
            queryset = queryset.filter(state__iexact=state)

        return queryset


class LoadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loads/shipments.
    """
    queryset = Load.objects.all()
    serializer_class = LoadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Load.objects.all()
        shipper_id = self.request.query_params.get('shipper', None)
        commodity = self.request.query_params.get('commodity', None)

        if shipper_id:
            queryset = queryset.filter(shipper_id=shipper_id)
        if commodity:
            queryset = queryset.filter(commodity__icontains=commodity)

        return queryset


class TripViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing trips with route planning and ELD functionality.
    """
    queryset = Trip.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        return TripSerializer

    def get_queryset(self):
        queryset = Trip.objects.all()
        driver_id = self.request.query_params.get('driver', None)
        status_filter = self.request.query_params.get('status', None)

        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=True, methods=['get'])
    def route_details(self, request, pk=None):
        """Get detailed route information for a trip"""
        trip = self.get_object()
        waypoints = RouteWaypoint.objects.filter(trip=trip)
        fuel_stops = FuelStop.objects.filter(trip=trip)
        rest_breaks = RestBreak.objects.filter(trip=trip)

        return Response({
            'trip': TripSerializer(trip).data,
            'waypoints': RouteWaypointSerializer(waypoints, many=True).data,
            'fuel_stops': FuelStopSerializer(fuel_stops, many=True).data,
            'rest_breaks': RestBreakSerializer(rest_breaks, many=True).data
        })

    @action(detail=True, methods=['get'])
    def eld_logs(self, request, pk=None):
        """Get ELD log sheets for a trip"""
        trip = self.get_object()
        log_sheets = ELDLogSheet.objects.filter(trip=trip)
        serializer = ELDLogSheetSerializer(log_sheets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start_trip(self, request, pk=None):
        """Start a trip and begin ELD logging"""
        trip = self.get_object()

        if trip.status != 'planned':
            return Response(
                {'error': 'Trip must be in planned status to start'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip.status = 'in_progress'
        trip.start_time = datetime.now()
        trip.save()

        # Create initial ELD log sheet
        log_sheet = ELDLogSheet.objects.create(
            trip=trip,
            driver=trip.driver,
            date=datetime.now().date()
        )

        return Response({
            'message': 'Trip started successfully',
            'trip': TripSerializer(trip).data
        })

    @action(detail=True, methods=['post'])
    def complete_trip(self, request, pk=None):
        """Complete a trip and finalize ELD logs"""
        trip = self.get_object()

        if trip.status != 'in_progress':
            return Response(
                {'error': 'Trip must be in progress to complete'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip.status = 'completed'
        trip.actual_end_time = datetime.now()
        trip.save()

        return Response({
            'message': 'Trip completed successfully',
            'trip': TripSerializer(trip).data
        })


class TripPlanningView(APIView):
    """
    Main API endpoint for trip planning as required by the assessment.
    Takes inputs (current location, pickup, dropoff, cycle hours) and
    returns route information and ELD log sheets.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Create a trip plan with route and ELD compliance.

        Required inputs (from assessment):
        - current_location
        - pickup_location
        - dropoff_location
        - current_cycle_used_hours
        - driver_id
        - tractor_id
        - trailer_id (optional)
        - load_id (optional)
        """
        serializer = TripPlanningInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Create the trip
        trip = Trip.objects.create(
            driver_id=validated_data['driver_id'],
            tractor_id=validated_data['tractor_id'],
            trailer_id=validated_data.get('trailer_id'),
            load_id=validated_data.get('load_id'),
            current_location=validated_data['current_location'],
            pickup_location=validated_data['pickup_location'],
            dropoff_location=validated_data['dropoff_location'],
            current_cycle_used_hours=validated_data['current_cycle_used_hours'],
            start_time=datetime.now(),
            status='planned'
        )

        # Generate route waypoints (simplified for demo)
        self._generate_route_waypoints(trip)

        # Generate fuel stops (every 1,000 miles)
        self._generate_fuel_stops(trip)

        # Generate rest breaks based on HOS rules
        self._generate_rest_breaks(trip)

        # Create ELD log sheets for the trip
        log_sheets = self._generate_eld_log_sheets(trip)

        # Prepare response data
        response_data = {
            'trip': TripSerializer(trip).data,
            'route_waypoints': RouteWaypointSerializer(trip.waypoints.all(), many=True).data,
            'fuel_stops': FuelStopSerializer(trip.fuel_stops.all(), many=True).data,
            'rest_breaks': RestBreakSerializer(trip.rest_breaks.all(), many=True).data,
            'log_sheets': ELDLogSheetSerializer(log_sheets, many=True).data,
            'total_estimated_duration': self._calculate_trip_duration(trip),
            'estimated_arrival': trip.estimated_end_time,
            'compliance_warnings': self._check_compliance_warnings(trip),
            'map_bounds': self._calculate_map_bounds(trip)
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    def _generate_route_waypoints(self, trip):
        """Generate route waypoints for the trip"""
        # Simplified implementation - in production, integrate with mapping API
        waypoints = [
            {
                'sequence': 1,
                'location_name': trip.current_location,
                'waypoint_type': 'route',
                'latitude': trip.current_lat or Decimal('0.0'),
                'longitude': trip.current_lng or Decimal('0.0')
            },
            {
                'sequence': 2,
                'location_name': trip.pickup_location,
                'waypoint_type': 'route',
                'latitude': trip.pickup_lat or Decimal('0.0'),
                'longitude': trip.pickup_lng or Decimal('0.0')
            },
            {
                'sequence': 3,
                'location_name': trip.dropoff_location,
                'waypoint_type': 'route',
                'latitude': trip.dropoff_lat or Decimal('0.0'),
                'longitude': trip.dropoff_lng or Decimal('0.0')
            }
        ]

        for waypoint_data in waypoints:
            RouteWaypoint.objects.create(trip=trip, **waypoint_data)

    def _generate_fuel_stops(self, trip):
        """Generate fuel stops every 1,000 miles as per assessment requirements"""
        estimated_miles = trip.total_estimated_miles or 1000
        fuel_stops_needed = (estimated_miles // 1000) + 1

        for i in range(fuel_stops_needed):
            miles_from_start = (i + 1) * 1000
            if miles_from_start > estimated_miles:
                miles_from_start = estimated_miles

            FuelStop.objects.create(
                trip=trip,
                location=f"Fuel Stop {i + 1}",
                miles_from_start=miles_from_start,
                estimated_time=trip.start_time + timedelta(hours=miles_from_start/60),
                fuel_needed=True
            )

    def _generate_rest_breaks(self, trip):
        """Generate mandatory rest breaks based on HOS rules"""
        # 30-minute break after 8 hours
        RestBreak.objects.create(
            trip=trip,
            break_type='30_min',
            location='30-Minute Break Location',
            scheduled_start=trip.start_time + timedelta(hours=8),
            scheduled_end=trip.start_time + timedelta(hours=8.5)
        )

        # 10-hour rest break
        RestBreak.objects.create(
            trip=trip,
            break_type='10_hour',
            location='10-Hour Rest Location',
            scheduled_start=trip.start_time + timedelta(hours=14),
            scheduled_end=trip.start_time + timedelta(hours=24)
        )

    def _generate_eld_log_sheets(self, trip):
        """Generate ELD log sheets for the trip duration"""
        # Simplified implementation - create log sheet for trip date
        log_sheet = ELDLogSheet.objects.create(
            trip=trip,
            driver=trip.driver,
            date=trip.start_time.date(),
            total_driving_time=Decimal('8.0'),  # Example
            total_on_duty_time=Decimal('2.0'),   # Example
            total_off_duty_time=Decimal('4.0'),  # Example
            total_sleeper_berth_time=Decimal('10.0'),  # Example
            total_duty_time=Decimal('10.0'),     # Example
            miles_driven=trip.total_estimated_miles or 500
        )

        # Create duty status periods
        self._generate_duty_status_periods(log_sheet)

        return [log_sheet]

    def _generate_duty_status_periods(self, log_sheet):
        """Generate duty status periods for the log sheet"""
        start_time = datetime.combine(log_sheet.date, datetime.min.time())

        # Example duty status periods
        periods = [
            {
                'duty_status': 'off_duty',
                'start_time': start_time,
                'end_time': start_time + timedelta(hours=6),
                'location': 'Home Base',
                'city': 'Green Bay',
                'state': 'WI',
                'activity_description': 'Off duty',
                'vehicle_moved': False,
                'grid_start_minute': 0,
                'grid_end_minute': 360
            },
            {
                'duty_status': 'on_duty',
                'start_time': start_time + timedelta(hours=6),
                'end_time': start_time + timedelta(hours=6.5),
                'location': 'Yard',
                'city': 'Green Bay',
                'state': 'WI',
                'activity_description': 'Pre-trip inspection',
                'vehicle_moved': False,
                'grid_start_minute': 360,
                'grid_end_minute': 390
            }
        ]

        for period_data in periods:
            DutyStatusPeriod.objects.create(log_sheet=log_sheet, **period_data)

    def _calculate_trip_duration(self, trip):
        """Calculate estimated trip duration"""
        return "12 hours 30 minutes"  # Simplified

    def _check_compliance_warnings(self, trip):
        """Check for HOS compliance warnings"""
        warnings = []

        if trip.current_cycle_used_hours > 60:
            warnings.append("Approaching 70-hour limit")

        return warnings

    def _calculate_map_bounds(self, trip):
        """Calculate map bounds for route display"""
        return {
            'north': 45.0,
            'south': 40.0,
            'east': -85.0,
            'west': -90.0
        }


class ELDLogSheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ELD log sheets.
    """
    queryset = ELDLogSheet.objects.all()
    serializer_class = ELDLogSheetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ELDLogSheet.objects.all()
        driver_id = self.request.query_params.get('driver', None)
        date = self.request.query_params.get('date', None)

        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)
        if date:
            queryset = queryset.filter(date=date)

        return queryset

    @action(detail=True, methods=['get'])
    def duty_periods(self, request, pk=None):
        """Get duty status periods for a log sheet"""
        log_sheet = self.get_object()
        periods = DutyStatusPeriod.objects.filter(log_sheet=log_sheet)
        serializer = DutyStatusPeriodSerializer(periods, many=True)
        return Response(serializer.data)


class DutyStatusPeriodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duty status periods.
    """
    queryset = DutyStatusPeriod.objects.all()
    serializer_class = DutyStatusPeriodSerializer
    permission_classes = [permissions.IsAuthenticated]


class HOSCycleTrackingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Hours of Service cycle tracking.
    """
    queryset = HOSCycleTracking.objects.all()
    serializer_class = HOSCycleTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = HOSCycleTracking.objects.all()
        driver_id = self.request.query_params.get('driver', None)

        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)

        return queryset
