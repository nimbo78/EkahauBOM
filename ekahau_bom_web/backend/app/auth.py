"""Authentication module for admin panel."""

from datetime import datetime, timedelta, UTC
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings

# Security scheme
security = HTTPBearer()

# Load configuration from settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Simple admin credentials (в production хранить в БД с хешированием)
ADMIN_CREDENTIALS = {settings.admin_username: settings.admin_password}


def create_access_token(username: str) -> str:
    """Create JWT access token.

    Args:
        username: Username to encode in token

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify JWT token and return username.

    Args:
        credentials: HTTP authorization credentials with Bearer token

    Returns:
        Username from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_admin(username: str = Depends(verify_token)) -> str:
    """Verify that user is an admin.

    Args:
        username: Username from verified token

    Returns:
        Username if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if username not in ADMIN_CREDENTIALS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return username
