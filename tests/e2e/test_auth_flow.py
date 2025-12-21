"""
E2E Tests for Authentication Flows

Tests complete authentication workflows:
- JWT token operations (login, refresh, blacklist)
- Permission-based access control
- Protected endpoint access
"""
import pytest
from tests.e2e.base import BaseE2ETest


@pytest.mark.django_db
class TestJWTTokenOperations(BaseE2ETest):
    """Test JWT token generation, refresh, and blacklist operations."""

    def test_jwt_token_generation(self):
        """
        E2E Test: JWT token generation

        Workflow:
        1. Login with valid credentials → Get access and refresh tokens
        2. Verify tokens are returned
        """
        # Login with credentials
        response = self.client.post('/api/auth/token/', {
            'username': 'admin_e2e',
            'password': 'AdminPass123!'
        })
        self.assert_response_success(response, 200)

        tokens = response.json()
        self.assert_has_keys(tokens, 'access', 'refresh')
        assert len(tokens['access']) > 0
        assert len(tokens['refresh']) > 0

    def test_jwt_token_refresh(self):
        """
        E2E Test: JWT token refresh

        Workflow:
        1. Get initial tokens
        2. Refresh access token → New access token returned
        3. Verify new token is different
        """
        # Get initial tokens
        response = self.client.post('/api/auth/token/', {
            'username': 'admin_e2e',
            'password': 'AdminPass123!'
        })
        tokens = response.json()
        initial_access = tokens['access']
        refresh_token = tokens['refresh']

        # Refresh token
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': refresh_token
        })
        self.assert_response_success(response, 200)

        new_tokens = response.json()
        self.assert_has_keys(new_tokens, 'access')
        assert new_tokens['access'] != initial_access

    def test_jwt_token_blacklist(self):
        """
        E2E Test: JWT token blacklist

        Workflow:
        1. Get tokens
        2. Blacklist refresh token → Success
        3. Attempt to refresh blacklisted token → 401
        """
        # Get tokens
        response = self.client.post('/api/auth/token/', {
            'username': 'admin_e2e',
            'password': 'AdminPass123!'
        })
        tokens = response.json()
        refresh_token = tokens['refresh']

        # Blacklist token
        response = self.client.post('/api/auth/token/blacklist/', {
            'refresh': refresh_token
        })
        self.assert_response_success(response, 200)

        # Attempt to refresh blacklisted token
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': refresh_token
        })
        self.assert_response_error(response, 401)

    def test_invalid_credentials(self):
        """
        E2E Test: Invalid credentials handling

        Workflow:
        1. Attempt login with wrong password → 401
        2. Attempt login with non-existent user → 401
        """
        # Wrong password
        response = self.client.post('/api/auth/token/', {
            'username': 'admin_e2e',
            'password': 'WrongPassword'
        })
        self.assert_response_error(response, 401)

        # Non-existent user
        response = self.client.post('/api/auth/token/', {
            'username': 'nonexistent',
            'password': 'SomePassword'
        })
        self.assert_response_error(response, 401)


@pytest.mark.django_db
class TestAuthenticationFlow(BaseE2ETest):
    """Test authentication and authorization workflows."""

    def test_unauthenticated_access(self):
        """
        E2E Test: Unauthenticated access to protected endpoints

        Workflow:
        1. Attempt to access protected endpoint without auth → 401
        """
        response = self.client.get('/api/buildings/')
        self.assert_response_error(response, 401)

    def test_authenticated_access(self):
        """
        E2E Test: Authenticated user can access protected endpoints

        Workflow:
        1. Authenticate as user → Access granted
        2. Access protected endpoint → 200
        """
        self.authenticate_as_user()
        response = self.client.get('/api/buildings/')
        self.assert_response_success(response, 200)

    def test_permission_levels_flow(self):
        """
        E2E Test: Different permission levels

        Workflow:
        1. Admin creates a building → 201
        2. Regular user attempts to create building → 403
        3. Regular user can list buildings → 200
        4. Regular user can view building detail → 200
        """
        # Step 1: Admin creates building
        self.authenticate_as_admin()
        building = self.create_building(street_number=999)
        assert building['street_number'] == 999

        # Step 2: Regular user attempts to create building
        self.authenticate_as_user()
        response = self.client.post('/api/buildings/', {
            'street_number': 1000,
            'name': 'Unauthorized Building',
            'address': 'Test Address'
        }, format='json')
        self.assert_response_error(response, 403)

        # Step 3: Regular user can list buildings
        response = self.client.get('/api/buildings/')
        self.assert_response_success(response, 200)

        # Step 4: Regular user can view building detail
        response = self.client.get(f'/api/buildings/{building["id"]}/')
        self.assert_response_success(response, 200)


@pytest.mark.django_db
class TestOAuthFlow(BaseE2ETest):
    """Test OAuth authentication flows."""

    def test_oauth_status_endpoint(self):
        """
        E2E Test: OAuth configuration status

        Workflow:
        1. Access OAuth status endpoint (public) → 200
        2. Verify response contains OAuth configuration
        """
        # Step 1: Access OAuth status (public endpoint)
        response = self.client.get('/api/auth/oauth/status/')
        self.assert_response_success(response, 200)

        # Step 2: Verify configuration keys
        data = response.json()
        self.assert_has_keys(
            data,
            'google_oauth_configured',
            'google_client_id_present',
            'google_client_secret_present',
            'frontend_url',
            'oauth_callback_path'
        )

    def test_oauth_link_account_flow(self):
        """
        E2E Test: OAuth account linking

        Workflow:
        1. Attempt to link without email → 400
        2. Attempt to link non-existent user → 404
        3. Successfully link existing user → 200
        """
        # Step 1: No email provided
        response = self.client.post('/api/auth/oauth/link/', {}, format='json')
        self.assert_response_error(response, 400)
        assert 'Email is required' in response.json()['error']

        # Step 2: Non-existent user
        response = self.client.post('/api/auth/oauth/link/', {
            'email': 'nonexistent@test.com'
        }, format='json')
        self.assert_response_error(response, 404)

        # Step 3: Existing user
        response = self.client.post('/api/auth/oauth/link/', {
            'email': self.admin_user.email
        }, format='json')
        self.assert_response_success(response, 200)
        data = response.json()
        assert data['success'] is True
        assert data['user_id'] == self.admin_user.id
