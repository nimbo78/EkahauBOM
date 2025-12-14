"""Tests for OAuth2 authentication."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.auth.base import UserInfo, TokenResponse
from app.auth.oauth2 import OAuth2AuthProvider

client = TestClient(app)


class TestAuthInfo:
    """Tests for /api/auth/info endpoint."""

    def test_auth_info_simple_backend(self):
        """Test auth info returns simple backend by default."""
        response = client.get("/api/auth/info")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_backend"] == "simple"
        assert data["supports_oauth2"] is False


class TestOAuth2Endpoints:
    """Tests for OAuth2-specific endpoints."""

    def test_oauth2_login_not_configured(self):
        """Test OAuth2 login returns error when not configured."""
        response = client.get(
            "/api/auth/oauth2/login", params={"redirect_uri": "http://localhost:4200/auth/callback"}
        )
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"].lower()

    def test_oauth2_callback_not_configured(self):
        """Test OAuth2 callback returns error when not configured."""
        response = client.post(
            "/api/auth/oauth2/callback",
            json={
                "code": "test_code",
                "state": "test_state",
                "redirect_uri": "http://localhost:4200/auth/callback",
            },
        )
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"].lower()

    def test_oauth2_refresh_not_configured(self):
        """Test OAuth2 refresh returns error when not configured."""
        response = client.post("/api/auth/oauth2/refresh", params={"refresh_token": "test_token"})
        assert response.status_code == 400  # OAuth2 not configured


class TestOAuth2Provider:
    """Tests for OAuth2AuthProvider class."""

    def test_provider_not_configured(self):
        """Test provider detects when issuer is not configured."""
        provider = OAuth2AuthProvider()
        # When issuer is empty, provider should have empty issuer
        # (default settings have empty oauth2_issuer)
        assert provider.issuer == "" or provider.issuer == settings.oauth2_issuer
        # supports_oauth2 is True because it's an OAuth2 provider type
        # (configuration check happens at API level)

    def test_provider_name(self):
        """Test provider name based on configuration."""
        provider = OAuth2AuthProvider()
        # When not configured, provider name indicates OAuth2 (not configured)
        assert provider.provider_name == "oauth2"

    def test_create_token(self):
        """Test creating JWT token from user info."""
        provider = OAuth2AuthProvider()
        user = UserInfo(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            roles=["ekahau-admin"],
        )
        token_response = provider.create_token(user)

        assert token_response.access_token
        assert token_response.token_type == "bearer"
        assert token_response.expires_in == settings.access_token_expire_minutes * 60

    def test_user_info_is_admin(self):
        """Test UserInfo.is_admin property."""
        # Admin role
        user1 = UserInfo(username="admin", roles=["admin"])
        assert user1.is_admin is True

        # Keycloak admin role
        user2 = UserInfo(username="admin", roles=["ekahau-admin"])
        assert user2.is_admin is True

        # Regular user
        user3 = UserInfo(username="user", roles=["ekahau-user"])
        assert user3.is_admin is False

        # No roles
        user4 = UserInfo(username="user", roles=[])
        assert user4.is_admin is False


class TestSimpleAuthWithOAuth2Endpoints:
    """Test that simple auth still works alongside OAuth2 endpoints."""

    def test_simple_login_still_works(self):
        """Test simple login works when auth_backend is simple."""
        response = client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_logout_works(self):
        """Test logout endpoint works."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        token = login_response.json()["access_token"]

        # Logout
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/auth/logout", headers=headers)
        assert response.status_code == 200
        assert "Logged out" in response.json()["message"]


class TestStateGeneration:
    """Test OAuth2 state parameter generation."""

    def test_generate_state(self):
        """Test state generation produces valid state."""
        from app.auth.oauth2 import generate_state

        state = generate_state()
        assert state is not None
        assert len(state) > 20  # Should be sufficiently long

        # Generate multiple states, they should be unique
        states = [generate_state() for _ in range(10)]
        assert len(set(states)) == 10  # All unique


class TestTokenValidation:
    """Test token validation."""

    def test_validate_simple_token(self):
        """Test validating a token from simple auth."""
        # Login to get a valid token
        login_response = client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        token = login_response.json()["access_token"]

        # Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/projects", headers=headers)
        assert response.status_code == 200

    def test_invalid_token_rejected(self):
        """Test invalid tokens are rejected."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.delete("/api/projects/some-uuid", headers=headers)
        assert response.status_code == 401
