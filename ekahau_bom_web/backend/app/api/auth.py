"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.auth import create_access_token, ADMIN_CREDENTIALS

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response model."""

    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Admin login endpoint.

    Args:
        request: Login credentials (username and password)

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    # Verify credentials
    if (
        request.username not in ADMIN_CREDENTIALS
        or ADMIN_CREDENTIALS[request.username] != request.password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create access token
    access_token = create_access_token(request.username)

    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal).

    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}
