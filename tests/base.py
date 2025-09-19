"""
Base test utilities for ELD Route Planning System

Provides common test setup, helper methods, and fixtures
for use across all test files.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from knox.models import AuthToken
from eld_system.models import Driver, Vehicle, Shipper, Load


class BaseAPITestCase(APITestCase):
    """Base test case with common setup and helper methods"""

    def setUp(self):
        """Set up common test data"""
        self.client = APIClient()

        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )

        # Create test driver
        self.test_driver = Driver.objects.create(
            user=self.test_user,
            driver_number='D001',
            initials='TU',
            home_operating_center='Test Terminal',
            license_number='DL123456789',
            license_state='IL'
        )

        # Create test vehicle
        self.test_vehicle = Vehicle.objects.create(
            vehicle_number='T001',
            vehicle_type='tractor',
            make='Freightliner',
            model='Cascadia',
            year=2023,
            vin='1FUJGDDR0NLAA1234'
        )

        # Create test shipper
        self.test_shipper = Shipper.objects.create(
            name='Test Shipping Co',
            address='123 Shipper St',
            city='Chicago',
            state='IL',
            zip_code='60601',
            contact_phone='555-0123',
            contact_email='shipper@test.com'
        )

        # Create test load
        self.test_load = Load.objects.create(
            load_id='L001',
            shipper=self.test_shipper,
            commodity='Test Freight',
            weight=25000,
            pieces=10
        )

    def get_authenticated_client(self, user=None):
        """Get API client with authentication token"""
        if user is None:
            user = self.test_user

        instance, token = AuthToken.objects.create(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        return client, token

    def create_test_user(self, username='newuser', email='newuser@test.com'):
        """Helper to create additional test users"""
        return User.objects.create_user(
            username=username,
            email=email,
            password='TestPass123!',
            first_name='New',
            last_name='User'
        )

    def create_test_driver(self, user=None, driver_number='D999'):
        """Helper to create additional test drivers"""
        if user is None:
            user = self.create_test_user(f'driver_{driver_number}')

        return Driver.objects.create(
            user=user,
            driver_number=driver_number,
            initials='TD',
            home_operating_center='Test Terminal',
            license_number=f'DL{driver_number}',
            license_state='IL'
        )

    def create_test_vehicle(self, vehicle_number='T999'):
        """Helper to create additional test vehicles"""
        return Vehicle.objects.create(
            vehicle_number=vehicle_number,
            vehicle_type='tractor',
            make='Test Make',
            model='Test Model',
            year=2023,
            vin=f'VIN{vehicle_number}'
        )

    def assertResponseHasKeys(self, response, keys):
        """Assert that response data contains specified keys"""
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in keys:
            self.assertIn(key, response.data, f"Response missing key: {key}")

    def assertValidationError(self, response, field=None):
        """Assert that response contains validation error"""
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        if field:
            self.assertIn(field, str(response.data))

    def assertUnauthorized(self, response):
        """Assert that response is unauthorized"""
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def assertNotFound(self, response):
        """Assert that response is not found"""
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def tearDown(self):
        """Clean up after tests"""
        # Clear all tokens
        AuthToken.objects.all().delete()


class AuthTestMixin:
    """Mixin providing authentication test helpers"""

    def get_login_token(self, username='testuser', password='TestPass123!'):
        """Get authentication token by logging in"""
        from django.urls import reverse

        login_data = {
            'username': username,
            'password': password
        }

        response = self.client.post(
            reverse('login'),
            login_data,
            format='json'
        )

        if response.status_code == status.HTTP_200_OK:
            return response.data['token']
        return None

    def authenticate_client(self, token):
        """Set authentication credentials on client"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def logout_client(self):
        """Clear authentication credentials"""
        self.client.credentials()


class TestDataMixin:
    """Mixin providing test data generation helpers"""

    @staticmethod
    def get_valid_trip_planning_data():
        """Get valid trip planning input data"""
        return {
            'current_location': '123 Main St, Chicago, IL 60601',
            'pickup_location': '456 Industrial Way, Detroit, MI 48201',
            'dropoff_location': '789 Delivery Dr, Atlanta, GA 30309',
            'current_cycle_used_hours': 45.5,
            'driver_id': 1,
            'tractor_id': 1
        }

    @staticmethod
    def get_valid_driver_data():
        """Get valid driver creation data"""
        return {
            'user_data': {
                'username': 'testdriver2',
                'email': 'testdriver2@example.com',
                'first_name': 'Test',
                'last_name': 'Driver'
            },
            'driver_number': 'D002',
            'initials': 'TD',
            'home_operating_center': 'Test Terminal',
            'license_number': 'DL987654321',
            'license_state': 'IL'
        }

    @staticmethod
    def get_valid_vehicle_data():
        """Get valid vehicle creation data"""
        return {
            'vehicle_number': 'T002',
            'vehicle_type': 'tractor',
            'make': 'Peterbilt',
            'model': '579',
            'year': 2022,
            'vin': '1XPWD49X0ED123456'
        }

    @staticmethod
    def get_valid_registration_data():
        """Get valid user registration data"""
        return {
            'username': 'newdriver',
            'email': 'newdriver@example.com',
            'first_name': 'New',
            'last_name': 'Driver',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }