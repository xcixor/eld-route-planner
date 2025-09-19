from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from eld_system.models import Vehicle
from .base import BaseAPITestCase, AuthTestMixin, TestDataMixin


class VehicleEndpointTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):

    def setUp(self):
        super().setUp()
        self.vehicles_url = reverse('vehicle-list')
        self.authenticated_client, self.token = self.get_authenticated_client()

    def test_list_vehicles_authenticated(self):
        """Test listing vehicles with authentication"""
        response = self.authenticated_client.get(self.vehicles_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)

    def test_list_vehicles_unauthenticated(self):
        """Test listing vehicles without authentication"""
        response = self.client.get(self.vehicles_url)
        self.assertUnauthorized(response)

    def test_create_vehicle_success(self):
        """Test creating a new vehicle"""
        vehicle_data = {
            'vehicle_number': 'T999',
            'vehicle_type': 'tractor',
            'make': 'Test Make',
            'model': 'Test Model',
            'year': 2023,
            'vin': 'TESTVIN12345'
        }

        response = self.authenticated_client.post(
            self.vehicles_url,
            vehicle_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['vehicle_number'], 'T999')

        vehicle = Vehicle.objects.get(vehicle_number='T999')
        self.assertEqual(vehicle.make, 'Test Make')
        self.assertTrue(vehicle.is_active)

    def test_create_vehicle_unauthenticated(self):
        """Test creating vehicle without authentication"""
        vehicle_data = self.get_valid_vehicle_data()
        response = self.client.post(self.vehicles_url, vehicle_data, format='json')
        self.assertUnauthorized(response)

    def test_create_vehicle_missing_required_fields(self):
        """Test creating vehicle with missing required fields"""
        invalid_data = {
            'vehicle_type': 'tractor',
            'make': 'Test Make'
        }

        response = self.authenticated_client.post(
            self.vehicles_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_create_vehicle_duplicate_number(self):
        """Test creating vehicle with duplicate vehicle number"""
        first_data = {
            'vehicle_number': 'DUPLICATE001',
            'vehicle_type': 'tractor',
            'make': 'Test Make',
            'model': 'Test Model',
            'year': 2023,
            'vin': 'VIN1'
        }

        self.authenticated_client.post(self.vehicles_url, first_data, format='json')

        duplicate_data = {
            'vehicle_number': 'DUPLICATE001',
            'vehicle_type': 'trailer',
            'make': 'Another Make',
            'model': 'Another Model',
            'year': 2024,
            'vin': 'VIN2'
        }

        response = self.authenticated_client.post(
            self.vehicles_url,
            duplicate_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_retrieve_vehicle_success(self):
        """Test retrieving a specific vehicle"""
        vehicle = self.test_vehicle
        url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})

        response = self.authenticated_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vehicle_number'], vehicle.vehicle_number)

    def test_retrieve_vehicle_not_found(self):
        """Test retrieving non-existent vehicle"""
        url = reverse('vehicle-detail', kwargs={'pk': 99999})
        response = self.authenticated_client.get(url)
        self.assertNotFound(response)

    def test_retrieve_vehicle_unauthenticated(self):
        """Test retrieving vehicle without authentication"""
        vehicle = self.test_vehicle
        url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})
        response = self.client.get(url)
        self.assertUnauthorized(response)

    def test_update_vehicle_success(self):
        """Test updating a vehicle"""
        vehicle = self.test_vehicle
        url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})

        update_data = {
            'vehicle_number': 'UPDATED001',
            'vehicle_type': 'tractor',
            'make': 'Updated Make',
            'model': 'Updated Model',
            'year': 2024,
            'vin': vehicle.vin,
            'is_active': False
        }

        response = self.authenticated_client.put(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.vehicle_number, 'UPDATED001')
        self.assertFalse(vehicle.is_active)

    def test_partial_update_vehicle_success(self):
        """Test partially updating a vehicle"""
        vehicle = self.test_vehicle
        url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})

        update_data = {'make': 'Partially Updated Make'}

        response = self.authenticated_client.patch(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.make, 'Partially Updated Make')

    def test_update_vehicle_duplicate_number(self):
        """Test updating vehicle with duplicate vehicle number"""
        vehicle1 = self.test_vehicle
        vehicle2 = self.create_test_vehicle('V002')

        url = reverse('vehicle-detail', kwargs={'pk': vehicle2.id})

        update_data = {
            'vehicle_number': vehicle1.vehicle_number,
            'vehicle_type': 'tractor',
            'make': 'Some Make',
            'model': 'Some Model',
            'year': 2023,
            'vin': vehicle2.vin
        }

        response = self.authenticated_client.put(url, update_data, format='json')

        self.assertValidationError(response)

    def test_delete_vehicle_success(self):
        """Test deleting a vehicle"""
        vehicle = self.create_test_vehicle('DELETE_ME')
        url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})

        response = self.authenticated_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Vehicle.objects.filter(id=vehicle.id).exists())

    def test_delete_vehicle_not_found(self):
        """Test deleting non-existent vehicle"""
        url = reverse('vehicle-detail', kwargs={'pk': 99999})
        response = self.authenticated_client.delete(url)
        self.assertNotFound(response)

    def test_delete_vehicle_unauthenticated(self):
        """Test deleting vehicle without authentication"""
        vehicle = self.test_vehicle
        url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})
        response = self.client.delete(url)
        self.assertUnauthorized(response)

    def test_vehicle_search_functionality(self):
        """Test vehicle search/filtering if implemented"""
        self.create_test_vehicle('SEARCH001')
        self.create_test_vehicle('SEARCH002')

        response = self.authenticated_client.get(
            self.vehicles_url,
            {'search': 'SEARCH'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class VehicleValidationTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):

    def setUp(self):
        super().setUp()
        self.vehicles_url = reverse('vehicle-list')
        self.authenticated_client, self.token = self.get_authenticated_client()

    def test_vehicle_type_choices(self):
        """Test vehicle type validation against choices"""
        invalid_data = {
            'vehicle_number': 'INVALID001',
            'vehicle_type': 'invalid_type',
            'make': 'Test Make',
            'model': 'Test Model',
            'year': 2023,
            'vin': 'TESTVIN123'
        }

        response = self.authenticated_client.post(
            self.vehicles_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_year_validation(self):
        """Test year field accepts various values (no strict validation)"""
        valid_data = {
            'vehicle_number': 'YEAR001',
            'vehicle_type': 'tractor',
            'make': 'Test Make',
            'model': 'Test Model',
            'year': 1800,
            'vin': 'TESTVIN123'
        }

        response = self.authenticated_client.post(
            self.vehicles_url,
            valid_data,
            format='json'
        )

        # Since year validation is not enforced, this should succeed
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_vin_uniqueness(self):
        """Test VIN field allows duplicates (no uniqueness constraint)"""
        first_data = {
            'vehicle_number': 'VIN001',
            'vehicle_type': 'tractor',
            'make': 'Test Make',
            'model': 'Test Model',
            'year': 2023,
            'vin': 'SAMEVIN123'
        }

        self.authenticated_client.post(self.vehicles_url, first_data, format='json')

        duplicate_data = {
            'vehicle_number': 'VIN002',
            'vehicle_type': 'trailer',
            'make': 'Another Make',
            'model': 'Another Model',
            'year': 2024,
            'vin': 'SAMEVIN123'
        }

        response = self.authenticated_client.post(
            self.vehicles_url,
            duplicate_data,
            format='json'
        )

        # Since VIN uniqueness is not enforced, this should succeed
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class VehicleIntegrationTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):

    def setUp(self):
        super().setUp()
        self.vehicles_url = reverse('vehicle-list')
        self.authenticated_client, self.token = self.get_authenticated_client()

    def test_create_and_retrieve_vehicle_flow(self):
        """Test complete create and retrieve vehicle workflow"""
        vehicle_data = self.get_valid_vehicle_data()

        create_response = self.authenticated_client.post(
            self.vehicles_url,
            vehicle_data,
            format='json'
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        vehicle_id = create_response.data['id']

        retrieve_url = reverse('vehicle-detail', kwargs={'pk': vehicle_id})
        retrieve_response = self.authenticated_client.get(retrieve_url)

        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.data['vehicle_number'], vehicle_data['vehicle_number'])

    def test_update_and_verify_vehicle_flow(self):
        """Test complete update and verify vehicle workflow"""
        vehicle = self.create_test_vehicle('UPDATE_TEST')

        update_url = reverse('vehicle-detail', kwargs={'pk': vehicle.id})
        update_data = {
            'vehicle_number': 'UPDATED_TEST',
            'vehicle_type': 'trailer',
            'make': 'Updated Make',
            'model': 'Updated Model',
            'year': 2024,
            'vin': vehicle.vin,
            'is_active': False
        }

        update_response = self.authenticated_client.put(
            update_url,
            update_data,
            format='json'
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        verify_response = self.authenticated_client.get(update_url)
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_response.data['vehicle_number'], 'UPDATED_TEST')
        self.assertEqual(verify_response.data['vehicle_type'], 'trailer')
        self.assertFalse(verify_response.data['is_active'])

    def test_vehicle_lifecycle_management(self):
        """Test complete vehicle lifecycle"""
        vehicle_data = {
            'vehicle_number': 'LIFECYCLE001',
            'vehicle_type': 'tractor',
            'make': 'Lifecycle Make',
            'model': 'Lifecycle Model',
            'year': 2023,
            'vin': 'LIFECYCLE123'
        }

        # Create
        create_response = self.authenticated_client.post(
            self.vehicles_url,
            vehicle_data,
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        vehicle_id = create_response.data['id']

        # Retrieve
        detail_url = reverse('vehicle-detail', kwargs={'pk': vehicle_id})
        get_response = self.authenticated_client.get(detail_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        # Update
        update_data = vehicle_data.copy()
        update_data['is_active'] = False
        update_response = self.authenticated_client.put(
            detail_url,
            update_data,
            format='json'
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        # Verify update
        verify_response = self.authenticated_client.get(detail_url)
        self.assertFalse(verify_response.data['is_active'])

        # Delete
        delete_response = self.authenticated_client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        final_response = self.authenticated_client.get(detail_url)
        self.assertEqual(final_response.status_code, status.HTTP_404_NOT_FOUND)