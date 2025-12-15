"""Authentication module with pluggable providers.

Supports:
- Simple JWT auth (username/password)
- OAuth2/OIDC (Keycloak, Azure AD, Okta, Google)
"""

from typing import Optional
from functools import lru_cache

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from .base import AuthProvider, UserInfo, TokenResponse
from .simple import SimpleAuthProvider
from .oauth2 import OAuth2AuthProvider, generate_state

# Re-export for convenience
__all__ = [
    "AuthProvider",
    "UserInfo",
    "TokenResponse",
    "SimpleAuthProvider",
    "OAuth2AuthProvider",
    "get_auth_provider",
    "verify_token",
    "verify_admin",
    "generate_state",
    # Backward compatibility
    "create_access_token",
    "ADMIN_CREDENTIALS",
]

# Security scheme
security = HTTPBearer()


@lru_cache()
def get_auth_provider() -> AuthProvider:
    """Get the configured authentication provider.

    Returns:
        AuthProvider instance based on settings.auth_backend

    The provider is determined by the AUTH_BACKEND environment variable:
    - "simple" (default): Username/password with JWT
    - "oauth2": OAuth2/OIDC with Keycloak or other IdP
    """
    backend = getattr(settings, "auth_backend", "simple")

    if backend == "oauth2":
        return OAuth2AuthProvider()
    else:
        return SimpleAuthProvider()


# Global provider instance (for backward compatibility)
_auth_provider: Optional[AuthProvider] = None


def _get_provider() -> AuthProvider:
    """Get or create the auth provider instance."""
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = get_auth_provider()
    return _auth_provider


# ============================================================================
# FastAPI Dependencies (used by API endpoints)
# ============================================================================


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserInfo:
    """Verify JWT token and return user info.

    Args:
        credentials: HTTP authorization credentials with Bearer token

    Returns:
        UserInfo from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    provider = _get_provider()
    token = credentials.credentials

    user = await provider.validate_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


async def verify_admin(user: UserInfo = Depends(verify_token)) -> UserInfo:
    """Verify that user has admin role.

    Args:
        user: UserInfo from verified token

    Returns:
        UserInfo if user is admin

    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ============================================================================
# Backward Compatibility
# ============================================================================


def create_access_token(username: str) -> str:
    """Create JWT access token (backward compatible).

    Args:
        username: Username to encode in token

    Returns:
        Encoded JWT token string
    """
    provider = _get_provider()
    user = UserInfo(username=username, roles=["admin"])
    response = provider.create_token(user)
    return response.access_token


# Simple admin credentials (backward compatible)
ADMIN_CREDENTIALS = {settings.admin_username: settings.admin_password}

# JWT settings (backward compatible)
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
