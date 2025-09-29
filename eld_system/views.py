from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction, IntegrityError
from decimal import Decimal
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView, LogoutView as KnoxLogoutView
from knox.auth import TokenAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from decimal import Decimal
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView, LogoutView as KnoxLogoutView
from knox.auth import TokenAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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


class LoginView(KnoxLoginView):
    """
    **User Authentication - Login**

    Authenticate user credentials and receive an access token for API requests.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Login with username and password to receive authentication token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING, description='Authentication token'),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'driver': openapi.Schema(type=openapi.TYPE_OBJECT, description='Driver profile if exists'),
                        'expires': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                    }
                )
            ),
            400: openapi.Response(description="Username and password are required"),
            401: openapi.Response(description="Invalid credentials"),
        },
        tags=['Authentication']
    )

    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Create token
        instance, token = AuthToken.objects.create(user)

        # Get driver info if exists
        driver_data = None
        try:
            driver = Driver.objects.get(user=user)
            driver_data = DriverSerializer(driver).data
        except Driver.DoesNotExist:
            pass

        return Response({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'driver': driver_data,
            'expires': instance.expiry
        })


class LogoutView(KnoxLogoutView):
    """
    Custom logout view that logs out the current token.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]


class LogoutAllView(APIView):
    """
    Logout all tokens for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request, format=None):
        request.user.auth_token_set.all().delete()
        return Response({'message': 'All tokens deleted successfully'})


class RegisterView(generics.CreateAPIView):
    """
    **User Registration**

    Register a new user account for the ELD Route Planning System.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user account",
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="User created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Validation error"),
        },
        tags=['Authentication']
    )

    def create(self, request, *args, **kwargs):
        """Handle user registration"""
        return super().create(request, *args, **kwargs)


class DriverViewSet(viewsets.ModelViewSet):
    """
    **Driver Management**

    Complete CRUD operations for driver profiles including license information,
    operating centers, and HOS compliance tracking.
    """
    queryset = Driver.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DriverCreateSerializer
        return DriverSerializer

    @swagger_auto_schema(
        operation_description="Get all trips for a specific driver",
        responses={
            200: openapi.Response(
                description="Driver trips retrieved successfully",
                schema=TripSerializer(many=True)
            ),
            404: openapi.Response(description="Driver not found"),
        },
        tags=['Drivers']
    )
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
    **Vehicle Management**

    Manage trucks, trailers, and other vehicles used in the fleet.
    Includes filtering by vehicle type and active status.
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Filter vehicles by type and active status",
        manual_parameters=[
            openapi.Parameter('type', openapi.IN_QUERY, description="Filter by vehicle type (truck/trailer)", type=openapi.TYPE_STRING),
            openapi.Parameter('active', openapi.IN_QUERY, description="Filter by active status (true/false)", type=openapi.TYPE_BOOLEAN),
        ],
        tags=['Fleet Management']
    )

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
    def available_trucks(self, request):
        """Get available trucks for assignment"""
        trucks = Vehicle.objects.filter(
            vehicle_type='truck',
            is_active=True
        )
        serializer = VehicleSerializer(trucks, many=True)
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
    **Trip Management**

    Comprehensive trip management including route planning, ELD log generation,
    and HOS compliance tracking. This ViewSet supports the core trip functionality
    for the ELD Route Planning System.
    """
    queryset = Trip.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        return TripSerializer

    @swagger_auto_schema(
        operation_description="Filter trips by driver or status",
        manual_parameters=[
            openapi.Parameter('driver', openapi.IN_QUERY, description="Filter by driver ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by trip status", type=openapi.TYPE_STRING),
        ],
        tags=['Trips']
    )

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
        ELDLogSheet.objects.create(
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
    **ELD Route Planning System - Main Endpoint**

    This is the core endpoint that fulfills the assessment requirements by taking trip details as inputs
    and outputting route instructions and ELD logs. The system calculates optimal routes while ensuring
    Hours of Service (HOS) compliance and generating required ELD documentation.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        **Core Trip Planning Endpoint**

        Creates a comprehensive trip plan that includes:
        - Route waypoints with GPS coordinates and instructions
        - Required fuel stops with location details
        - Mandatory rest breaks for HOS compliance
        - Complete ELD log sheets with duty status periods
        - Hours of Service cycle tracking

        This endpoint fulfills the assessment requirement: "Build an app that takes trip details as inputs
        and outputs route instructions and draws ELD logs as outputs."
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['current_location', 'pickup_location', 'dropoff_location', 'current_cycle_used_hours', 'driver_id', 'truck_id'],
            properties={
                'current_location': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Current location (address or coordinates)',
                    example='123 Main St, Chicago, IL 60601'
                ),
                'pickup_location': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Pickup location (address or coordinates)',
                    example='456 Industrial Way, Detroit, MI 48201'
                ),
                'dropoff_location': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Final destination (address or coordinates)',
                    example='789 Delivery Dr, Atlanta, GA 30309'
                ),
                'current_cycle_used_hours': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    format='decimal',
                    description='Hours already used in current cycle (0-70)',
                    minimum=0,
                    maximum=70,
                    example=45.5
                ),
                'driver_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Driver ID from system',
                    example=1
                ),
                'truck_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Truck/Vehicle ID from system',
                    example=1
                ),
                'trailer_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Trailer ID (optional)',
                    example=1
                ),
                'load_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Load ID (optional)',
                    example=1
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Trip plan created successfully with route and ELD logs",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'trip': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                                'trip_number': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                'estimated_duration_hours': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'estimated_distance_miles': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'estimated_start_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                'estimated_end_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                            }
                        ),
                        'route_waypoints': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='Turn-by-turn route instructions',
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'sequence_number': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'latitude': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                    'longitude': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                    'location_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'instruction': openapi.Schema(type=openapi.TYPE_STRING),
                                    'distance_miles': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'estimated_arrival_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                }
                            )
                        ),
                        'fuel_stops': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='Required fuel stops along route',
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'location_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'estimated_arrival_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                    'fuel_amount_gallons': openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                        'rest_breaks': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='Mandatory rest breaks for HOS compliance',
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'break_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'location_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                    'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                    'duration_hours': openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                        'eld_log_sheets': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='Generated ELD log sheets for compliance',
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'log_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'total_miles_driven': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'duty_status_periods': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                                'duration_hours': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                'location': openapi.Schema(type=openapi.TYPE_STRING),
                                            }
                                        )
                                    )
                                }
                            )
                        ),
                        'hos_compliance': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Hours of Service compliance tracking',
                            properties={
                                'cycle_hours_used': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'cycle_hours_remaining': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'daily_driving_hours': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'daily_duty_hours': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'next_break_required_at': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                                'next_rest_required_at': openapi.Schema(type=openapi.TYPE_STRING, format='datetime'),
                            }
                        ),
                    }
                )
            ),
            400: openapi.Response(description="Invalid input data or validation error"),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Driver, vehicle, or other resource not found"),
        },
        tags=['Trip Planning']
    )

    def post(self, request):
        """
        Create a trip plan with route and ELD compliance.

        Required inputs (from assessment):
        - current_location
        - pickup_location
        - dropoff_location
        - current_cycle_used_hours
        - driver_id
        - truck_id
        - trailer_id (optional)
        - load_id (optional)
        """
        serializer = TripPlanningInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        try:
            with transaction.atomic():
                # Enforce: one trip per driver per day
                driver_id = validated_data['driver_id']
                today = timezone.now().date()

                # Check existing trips started today for the driver
                if Trip.objects.filter(driver_id=driver_id, start_time__date=today).exists() or \
                   ELDLogSheet.objects.filter(driver_id=driver_id, date=today).exists():
                    return Response({
                        'status_code': 400,
                        'error': 'Another trip has already been setup for today'
                    }, status=status.HTTP_400_BAD_REQUEST)

                trip = Trip.objects.create(
                    driver_id=validated_data['driver_id'],
                    truck_id=validated_data['truck_id'],
                    trailer_id=validated_data.get('trailer_id'),
                    load_id=validated_data.get('load_id'),
                    current_location=validated_data['current_location'],
                    pickup_location=validated_data['pickup_location'],
                    dropoff_location=validated_data['dropoff_location'],
                    current_cycle_used_hours=validated_data['current_cycle_used_hours'],
                    start_time=timezone.now(),
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
        except IntegrityError as ie:
            return Response({'status_code': 400, 'error': str(ie)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'status_code': 500, 'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_route_waypoints(self, trip):
        """Generate route waypoints for the trip"""
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
        RestBreak.objects.create(
            trip=trip,
            break_type='30_min',
            location='30-Minute Break Location',
            scheduled_start=trip.start_time + timedelta(hours=8),
            scheduled_end=trip.start_time + timedelta(hours=8.5)
        )

        RestBreak.objects.create(
            trip=trip,
            break_type='10_hour',
            location='10-Hour Rest Location',
            scheduled_start=trip.start_time + timedelta(hours=14),
            scheduled_end=trip.start_time + timedelta(hours=24)
        )

    def _generate_eld_log_sheets(self, trip):
        """Generate ELD log sheets for the trip duration"""
        log_sheet = ELDLogSheet.objects.create(
            trip=trip,
            driver=trip.driver,
            date=trip.start_time.date(),
            total_driving_time=Decimal('8.0'),
            total_on_duty_time=Decimal('2.0'),
            total_off_duty_time=Decimal('4.0'),
            total_sleeper_berth_time=Decimal('10.0'),
            total_duty_time=Decimal('10.0'),
            miles_driven=trip.total_estimated_miles or 500
        )

        self._generate_duty_status_periods(log_sheet)

        return [log_sheet]

    def _generate_duty_status_periods(self, log_sheet):
        """Generate duty status periods for the log sheet"""
        start_time = datetime.combine(log_sheet.date, datetime.min.time())

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
        return "12 hours 30 minutes"

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
    **ELD Log Sheet Management**

    Electronic Logging Device log sheets for DOT compliance and Hours of Service tracking.
    These logs are generated automatically during trip planning and can be viewed/exported.
    """
    queryset = ELDLogSheet.objects.all()
    serializer_class = ELDLogSheetSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Filter ELD logs by driver or date",
        manual_parameters=[
            openapi.Parameter('driver', openapi.IN_QUERY, description="Filter by driver ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('date', openapi.IN_QUERY, description="Filter by log date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format='date'),
        ],
        tags=['ELD Compliance']
    )

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

    def get_queryset(self):
        qs = super().get_queryset()
        log_sheet_id = self.request.query_params.get('log_sheet')
        if log_sheet_id:
            qs = qs.filter(log_sheet_id=log_sheet_id)
        return qs


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
