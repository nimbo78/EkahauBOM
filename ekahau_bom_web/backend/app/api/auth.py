"""Authentication endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.auth import (
    get_auth_provider,
    UserInfo,
    generate_state,
    ADMIN_CREDENTIALS,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Store states for CSRF protection (in production, use Redis or similar)
_oauth_states: dict[str, bool] = {}


class LoginRequest(BaseModel):
    """Login request model for simple auth."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class AuthInfoResponse(BaseModel):
    """Authentication info response."""

    auth_backend: str
    supports_oauth2: bool
    oauth2_login_url: Optional[str] = None


class OAuth2CallbackRequest(BaseModel):
    """OAuth2 callback request model."""

    code: str
    state: str
    redirect_uri: Optional[str] = None


# ============================================================================
# Auth Info Endpoint
# ============================================================================


@router.get("/info", response_model=AuthInfoResponse)
async def auth_info():
    """Get authentication backend information.

    Returns:
        Auth backend type and OAuth2 support status
    """
    provider = get_auth_provider()

    response = AuthInfoResponse(
        auth_backend=provider.provider_name,
        supports_oauth2=provider.supports_oauth2,
    )

    return response


# ============================================================================
# Simple Auth Endpoints
# ============================================================================


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Admin login endpoint (simple auth).

    Args:
        request: Login credentials (username and password)

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid or auth backend is OAuth2
    """
    provider = get_auth_provider()

    # For OAuth2 backend, simple login is not supported
    if provider.supports_oauth2:
        raise HTTPException(
            status_code=400,
            detail="Simple login not supported. Use OAuth2 flow (/api/auth/oauth2/login).",
        )

    # Authenticate with simple provider
    user = await provider.authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create access token
    token_response = provider.create_token(user)

    return TokenResponse(
        access_token=token_response.access_token,
        expires_in=token_response.expires_in,
    )


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal).

    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}


# ============================================================================
# OAuth2 Endpoints
# ============================================================================


@router.get("/oauth2/login")
async def oauth2_login(
    redirect_uri: Optional[str] = Query(
        default=None, description="Redirect URI after authentication"
    ),
):
    """Get OAuth2 login URL.

    Args:
        redirect_uri: Optional redirect URI (defaults to settings.oauth2_redirect_uri)

    Returns:
        Login URL for OAuth2 flow

    Raises:
        HTTPException: If OAuth2 is not configured
    """
    provider = get_auth_provider()

    if not provider.supports_oauth2:
        raise HTTPException(
            status_code=400,
            detail="OAuth2 not configured. Use simple login (/api/auth/login).",
        )

    # Generate state for CSRF protection
    state = generate_state()
    _oauth_states[state] = True

    # Get redirect URI
    uri = redirect_uri or settings.oauth2_redirect_uri

    # Get login URL
    login_url = provider.get_login_url(state=state, redirect_uri=uri)

    return {
        "login_url": login_url,
        "state": state,
    }


@router.post("/oauth2/callback", response_model=TokenResponse)
async def oauth2_callback(request: OAuth2CallbackRequest):
    """Handle OAuth2 callback.

    Args:
        request: OAuth2 callback with authorization code and state

    Returns:
        JWT access token

    Raises:
        HTTPException: If callback fails or state is invalid
    """
    provider = get_auth_provider()

    if not provider.supports_oauth2:
        raise HTTPException(status_code=400, detail="OAuth2 not configured")

    # Verify state (CSRF protection)
    if request.state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Remove used state
    del _oauth_states[request.state]

    # Get redirect URI
    redirect_uri = request.redirect_uri or settings.oauth2_redirect_uri

    # Handle callback
    user = await provider.handle_callback(
        code=request.code,
        state=request.state,
        redirect_uri=redirect_uri,
    )

    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Create internal access token
    token_response = provider.create_token(user)

    return TokenResponse(
        access_token=token_response.access_token,
        expires_in=token_response.expires_in,
    )


@router.post("/oauth2/refresh", response_model=TokenResponse)
async def oauth2_refresh(refresh_token: str):
    """Refresh OAuth2 access token.

    Args:
        refresh_token: The refresh token from IdP

    Returns:
        New JWT access token

    Raises:
        HTTPException: If refresh fails
    """
    provider = get_auth_provider()

    if not provider.supports_oauth2:
        raise HTTPException(status_code=400, detail="OAuth2 not configured")

    token_response = await provider.refresh_token(refresh_token)

    if token_response is None:
        raise HTTPException(status_code=401, detail="Token refresh failed")

    return TokenResponse(
        access_token=token_response.access_token,
        expires_in=token_response.expires_in,
    )
