"""
Driver endpoint tests for ELD Route Planning System
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from eld_system.models import Driver
from .base import BaseAPITestCase, AuthTestMixin, TestDataMixin


class DriverEndpointTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):

    def setUp(self):
        super().setUp()
        self.drivers_url = reverse('driver-list')
        self.authenticated_client, self.token = self.get_authenticated_client()

    def test_list_drivers_authenticated(self):
        """Test listing drivers with authentication"""
        response = self.authenticated_client.get(self.drivers_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_drivers_unauthenticated(self):
        """Test listing drivers without authentication"""
        response = self.client.get(self.drivers_url)
        self.assertUnauthorized(response)

    def test_create_driver_success(self):
        """Test creating a new driver"""
        driver_data = {
            'driver_number': 'D999',
            'initials': 'TD',
            'home_operating_center': 'Test Center',
            'license_number': 'LIC999',
            'license_state': 'CA'
        }

        response = self.authenticated_client.post(
            self.drivers_url,
            driver_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['driver_number'], 'D999')

        driver = Driver.objects.get(driver_number='D999')
        self.assertEqual(driver.initials, 'TD')

    def test_create_driver_duplicate_number(self):
        """Test creating driver with duplicate driver number"""
        driver_data = {
            'driver_number': self.test_driver.driver_number,
            'initials': 'XX',
            'home_operating_center': 'Test Center',
            'license_number': 'LIC999',
            'license_state': 'CA'
        }

        response = self.authenticated_client.post(
            self.drivers_url,
            driver_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_create_driver_missing_required_fields(self):
        """Test creating driver with missing required fields"""
        driver_data = {
            'driver_number': 'D999'
        }

        response = self.authenticated_client.post(
            self.drivers_url,
            driver_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_create_driver_unauthenticated(self):
        """Test creating driver without authentication"""
        driver_data = self.get_valid_driver_data()

        response = self.client.post(
            self.drivers_url,
            driver_data,
            format='json'
        )

        self.assertUnauthorized(response)

    def test_retrieve_driver_success(self):
        """Test retrieving a specific driver"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        response = self.authenticated_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['driver_number'], self.test_driver.driver_number)

    def test_retrieve_driver_not_found(self):
        """Test retrieving non-existent driver"""
        url = reverse('driver-detail', kwargs={'pk': 99999})
        response = self.authenticated_client.get(url)

        self.assertNotFound(response)

    def test_retrieve_driver_unauthenticated(self):
        """Test retrieving driver without authentication"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        response = self.client.get(url)

        self.assertUnauthorized(response)

    def test_update_driver_success(self):
        """Test updating a driver"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        update_data = {
            'driver_number': self.test_driver.driver_number,
            'initials': 'UU',
            'home_operating_center': 'Updated Center',
            'license_number': self.test_driver.license_number,
            'license_state': self.test_driver.license_state
        }

        response = self.authenticated_client.put(
            url,
            update_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['initials'], 'UU')

        self.test_driver.refresh_from_db()
        self.assertEqual(self.test_driver.initials, 'UU')

    def test_partial_update_driver_success(self):
        """Test partially updating a driver"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        update_data = {
            'initials': 'PU'
        }

        response = self.authenticated_client.patch(
            url,
            update_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['initials'], 'PU')

    def test_update_driver_duplicate_number(self):
        """Test updating driver with duplicate driver number"""
        other_driver = self.create_test_driver(driver_number='D888')

        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        update_data = {
            'driver_number': other_driver.driver_number,
            'initials': self.test_driver.initials,
            'home_operating_center': self.test_driver.home_operating_center,
            'license_number': self.test_driver.license_number,
            'license_state': self.test_driver.license_state
        }

        response = self.authenticated_client.put(
            url,
            update_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_delete_driver_success(self):
        """Test deleting a driver"""
        driver = self.create_test_driver(driver_number='D777')
        url = reverse('driver-detail', kwargs={'pk': driver.pk})

        response = self.authenticated_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Driver.objects.filter(pk=driver.pk).exists())

    def test_delete_driver_not_found(self):
        """Test deleting non-existent driver"""
        url = reverse('driver-detail', kwargs={'pk': 99999})
        response = self.authenticated_client.delete(url)

        self.assertNotFound(response)

    def test_delete_driver_unauthenticated(self):
        """Test deleting driver without authentication"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        response = self.client.delete(url)

        self.assertUnauthorized(response)

    def test_driver_trips_endpoint(self):
        """Test getting trips for a specific driver"""
        url = reverse('driver-trips', kwargs={'pk': self.test_driver.pk})
        response = self.authenticated_client.get(url)

        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_driver_serializer_includes_user_data(self):
        """Test that driver serializer includes user information"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})
        response = self.authenticated_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], self.test_user.username)

    def test_driver_search_functionality(self):
        """Test driver search/filtering if implemented"""
        response = self.authenticated_client.get(
            self.drivers_url,
            {'search': self.test_driver.driver_number}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DriverValidationTestCase(BaseAPITestCase, AuthTestMixin):

    def setUp(self):
        super().setUp()
        self.drivers_url = reverse('driver-list')
        self.authenticated_client, self.token = self.get_authenticated_client()

    def test_driver_number_validation(self):
        """Test driver number format validation"""
        invalid_data = {
            'driver_number': '',
            'initials': 'XX',
            'home_operating_center': 'Test',
            'license_number': 'LIC123',
            'license_state': 'CA'
        }

        response = self.authenticated_client.post(
            self.drivers_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_license_state_validation(self):
        """Test license state format validation"""
        invalid_data = {
            'driver_number': 'D999',
            'initials': 'XX',
            'home_operating_center': 'Test',
            'license_number': 'LIC123',
            'license_state': 'CALIFORNIA'
        }

        response = self.authenticated_client.post(
            self.drivers_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_initials_length_validation(self):
        """Test initials length validation"""
        invalid_data = {
            'driver_number': 'D999',
            'initials': 'TOOLONG',
            'home_operating_center': 'Test',
            'license_number': 'LIC123',
            'license_state': 'CA'
        }

        response = self.authenticated_client.post(
            self.drivers_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response)


class DriverIntegrationTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):

    def setUp(self):
        super().setUp()
        self.drivers_url = reverse('driver-list')
        self.authenticated_client, self.token = self.get_authenticated_client()

    def test_create_and_retrieve_driver_flow(self):
        """Test complete create and retrieve driver workflow"""
        driver_data = self.get_valid_driver_data()

        create_response = self.authenticated_client.post(
            self.drivers_url,
            driver_data,
            format='json'
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        driver_id = create_response.data['id']

        retrieve_url = reverse('driver-detail', kwargs={'pk': driver_id})
        retrieve_response = self.authenticated_client.get(retrieve_url)

        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.data['driver_number'], driver_data['driver_number'])

    def test_update_and_verify_driver_flow(self):
        """Test complete update and verify driver workflow"""
        url = reverse('driver-detail', kwargs={'pk': self.test_driver.pk})

        update_data = {
            'driver_number': self.test_driver.driver_number,
            'initials': 'UP',
            'home_operating_center': 'Updated Center',
            'license_number': 'NEWLIC123',
            'license_state': 'NY'
        }

        update_response = self.authenticated_client.put(
            url,
            update_data,
            format='json'
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        verify_response = self.authenticated_client.get(url)
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_response.data['license_state'], 'NY')
        self.assertEqual(verify_response.data['license_number'], 'NEWLIC123')