"""Tests for authentication and authorization."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

# Get credentials from settings
ADMIN_USERNAME = settings.admin_username
ADMIN_PASSWORD = settings.admin_password


def test_login_success():
    """Test successful admin login."""
    response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_login_nonexistent_user():
    """Test login with non-existent user."""
    response = client.post("/api/auth/login", json={"username": "hacker", "password": "password"})
    assert response.status_code == 401


def test_protected_endpoint_without_token():
    """Test accessing protected upload endpoint without token."""
    # Upload endpoint requires admin authentication
    response = client.post(
        "/api/upload", files={"file": ("test.esx", b"test", "application/octet-stream")}
    )
    assert response.status_code == 403  # FastAPI returns 403 when no credentials provided
    assert "Not authenticated" in response.json()["detail"]


def test_protected_endpoint_with_invalid_token():
    """Test accessing protected endpoint with invalid token."""
    headers = {"Authorization": "Bearer invalid_token_12345"}
    response = client.delete("/api/projects/some-uuid", headers=headers)
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]  # "Invalid or expired token"


def test_protected_endpoint_with_valid_token():
    """Test accessing protected endpoint with valid token."""
    # First, login to get token
    login_response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login_response.json()["access_token"]

    # Try to access projects list (public endpoint, should work with or without token)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/projects", headers=headers)
    assert response.status_code == 200


def test_delete_project_requires_admin():
    """Test that delete endpoint requires admin token."""
    # Try without token
    response = client.delete("/api/projects/some-uuid")
    assert response.status_code == 403  # FastAPI returns 403 when no credentials provided

    # Try with valid token
    login_response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # DELETE with non-existent project ID should return validation or not found error
    response = client.delete("/api/projects/non-existent-uuid", headers=headers)
    assert response.status_code in [
        400,
        404,
        422,
        500,
    ]  # Validation error, not found, or processing error


def test_token_expiry():
    """Test that expired tokens are rejected."""
    import jwt
    from datetime import datetime, timedelta, UTC
    from app.auth import SECRET_KEY, ALGORITHM

    # Create an expired token
    expired_token = jwt.encode(
        {"sub": "admin", "exp": datetime.now(UTC) - timedelta(hours=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.delete("/api/projects/some-uuid", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_logout():
    """Test logout endpoint (should always succeed - stateless JWT)."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login_response.json()["access_token"]

    # Logout
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 200
    assert "Logged out successfully" in response.json()["message"]


def test_upload_requires_admin():
    """Test that upload endpoint requires admin authentication."""
    # Try without token
    response = client.post(
        "/api/upload", files={"file": ("test.esx", b"test", "application/octet-stream")}
    )
    assert response.status_code == 403  # FastAPI returns 403 when no credentials provided

    # Try with token (will fail at validation stage, but auth should pass)
    login_response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Should fail at file validation, not auth (or succeed if minimal test file is valid)
    response = client.post(
        "/api/upload",
        files={"file": ("test.esx", b"test", "application/octet-stream")},
        headers=headers,
    )
    # Auth passed - either succeeds or fails at validation
    assert response.status_code in [200, 400, 422, 500]  # Success or validation error


def test_process_requires_admin():
    """Test that process endpoint requires admin authentication."""
    # Try without token
    response = client.post("/api/upload/some-uuid/process", json={})
    assert response.status_code == 403  # FastAPI returns 403 when no credentials provided

    # With token
    login_response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Should fail at finding project or validation, not auth
    response = client.post("/api/upload/non-existent-uuid/process", json={}, headers=headers)
    assert response.status_code in [
        400,
        404,
        422,
        500,
    ]  # Bad request, not found, validation, or processing error
