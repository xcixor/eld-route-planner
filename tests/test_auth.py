"""
Authentication Tests for ELD Route Planning System

Tests cover:
- User registration (with validation and edge cases)
- User login (with Knox token authentication)
- User logout
- Token authentication middleware
- Error handling and edge cases
"""

import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from knox.models import AuthToken
from eld_system.models import Driver
from .base import BaseAPITestCase, AuthTestMixin, TestDataMixin


class AuthenticationTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):
    """Test suite for authentication endpoints"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.valid_user_data = self.get_valid_registration_data()

    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(
            self.register_url,
            self.valid_user_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('username', response.data)
        self.assertIn('email', response.data)
        user = User.objects.get(username=self.valid_user_data['username'])
        self.assertEqual(user.email, self.valid_user_data['email'])
        self.assertEqual(user.first_name, self.valid_user_data['first_name'])
        self.assertEqual(user.last_name, self.valid_user_data['last_name'])
        self.assertTrue(user.check_password(self.valid_user_data['password']))

    def test_user_registration_password_mismatch(self):
        """Test registration with password confirmation mismatch"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password_confirm'] = 'DifferentPassword'

        response = self.client.post(
            self.register_url,
            invalid_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_user_registration_duplicate_username(self):
        """Test registration with existing username"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['username'] = self.test_user.username

        response = self.client.post(
            self.register_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_user_registration_duplicate_email(self):
        """Test registration with existing email"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = self.test_user.email
        invalid_data['username'] = 'different_username'  # Use different username

        response = self.client.post(
            self.register_url,
            invalid_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn('email already exists', str(response.data))

    def test_user_registration_invalid_email(self):
        """Test registration with invalid email format"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = 'invalid-email'

        response = self.client.post(
            self.register_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response, 'email')

    def test_user_registration_weak_password(self):
        """Test registration with weak password"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = '123'
        invalid_data['password_confirm'] = '123'

        response = self.client.post(
            self.register_url,
            invalid_data,
            format='json'
        )

        self.assertValidationError(response, 'password')

    def test_user_registration_missing_fields(self):
        """Test registration with missing required fields"""
        incomplete_data = {
            'username': 'testuser',
            'password': 'SecurePass123!'
        }

        response = self.client.post(
            self.register_url,
            incomplete_data,
            format='json'
        )

        self.assertValidationError(response)

    def test_user_login_success(self):
        """Test successful user login"""
        login_data = {
            'username': self.test_user.username,
            'password': 'TestPass123!'
        }

        response = self.client.post(
            self.login_url,
            login_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertIn('expires', response.data)

        token = response.data['token']
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 20)

        user_data = response.data['user']
        self.assertEqual(user_data['username'], self.test_user.username)
        self.assertEqual(user_data['email'], self.test_user.email)

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        invalid_login_data = {
            'username': self.test_user.username,
            'password': 'WrongPassword'
        }

        response = self.client.post(
            self.login_url,
            invalid_login_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_login_nonexistent_user(self):
        """Test login with non-existent username"""
        invalid_login_data = {
            'username': 'nonexistentuser',
            'password': 'SomePassword123!'
        }

        response = self.client.post(
            self.login_url,
            invalid_login_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_login_missing_fields(self):
        """Test login with missing required fields"""
        incomplete_data = {
            'username': self.test_user.username
            # Missing password
        }

        response = self.client.post(
            self.login_url,
            incomplete_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_authentication(self):
        """Test using token for authenticated requests"""
        client, token = self.get_authenticated_client()
        drivers_url = reverse('driver-list')
        response = client.get(drivers_url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_invalid_token_authentication(self):
        """Test authentication with invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token_12345')
        drivers_url = reverse('driver-list')
        response = self.client.get(drivers_url)
        self.assertUnauthorized(response)

    def test_missing_token_authentication(self):
        """Test accessing protected endpoint without token"""
        drivers_url = reverse('driver-list')
        response = self.client.get(drivers_url)
        self.assertUnauthorized(response)

    def test_user_logout_success(self):
        """Test successful user logout"""
        client, token = self.get_authenticated_client()
        response = client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        drivers_url = reverse('driver-list')
        response = client.get(drivers_url)
        self.assertUnauthorized(response)

    def test_logout_without_token(self):
        """Test logout without authentication token"""
        response = self.client.post(self.logout_url)
        self.assertUnauthorized(response)

    def test_token_expiry_configuration(self):
        """Test that tokens have proper expiry configuration"""
        instance, token = AuthToken.objects.create(self.test_user)
        self.assertIsNotNone(instance.expiry)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)

    def test_multiple_concurrent_tokens(self):
        """Test that users can have multiple valid tokens"""
        login_data = {
            'username': self.test_user.username,
            'password': 'TestPass123!'
        }

        response1 = self.client.post(self.login_url, login_data, format='json')
        response2 = self.client.post(self.login_url, login_data, format='json')

        token1 = response1.data['token']
        token2 = response2.data['token']

        self.assertNotEqual(token1, token2)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token1}')
        drivers_url = reverse('driver-list')
        response = self.client.get(drivers_url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token2}')
        response = self.client.get(drivers_url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def tearDown(self):
        """Clean up after tests"""
        super().tearDown()
        User.objects.filter(username__in=['testdriver', 'newdriver']).delete()


class AuthenticationIntegrationTestCase(BaseAPITestCase, AuthTestMixin, TestDataMixin):
    """Integration tests for authentication flow"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')

    def test_complete_authentication_flow(self):
        """Test complete user journey: register -> login -> access protected resource -> logout"""
        register_data = self.get_valid_registration_data()
        register_data['username'] = 'flowtest'
        register_data['email'] = 'flowtest@example.com'

        register_response = self.client.post(
            self.register_url,
            register_data,
            format='json'
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        login_data = {
            'username': 'flowtest',
            'password': register_data['password']
        }

        login_response = self.client.post(
            self.login_url,
            login_data,
            format='json'
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        drivers_url = reverse('driver-list')
        protected_response = self.client.get(drivers_url)

        self.assertIn(protected_response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        post_logout_response = self.client.get(drivers_url)
        self.assertUnauthorized(post_logout_response)

    def test_registration_with_driver_profile_creation(self):
        """Test that registration works properly with driver profile creation if implemented"""
        register_data = self.get_valid_registration_data()
        register_data['username'] = 'driverprofiletest'
        register_data['email'] = 'driverprofile@example.com'

        response = self.client.post(
            self.register_url,
            register_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='driverprofiletest')
        self.assertIsNotNone(user)
        try:
            driver = Driver.objects.get(user=user)
            self.assertEqual(driver.user, user)
        except Driver.DoesNotExist:
            pass