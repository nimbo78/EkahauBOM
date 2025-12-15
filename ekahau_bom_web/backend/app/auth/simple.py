"""Simple JWT authentication provider (username/password)."""

from datetime import datetime, timedelta, UTC
from typing import Optional

import jwt

from app.config import settings
from .base import AuthProvider, UserInfo, TokenResponse


class SimpleAuthProvider(AuthProvider):
    """Simple authentication provider using username/password and JWT tokens."""

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = None,
        expire_minutes: int = None,
        credentials: dict[str, str] = None,
    ):
        """Initialize simple auth provider.

        Args:
            secret_key: JWT secret key (default from settings)
            algorithm: JWT algorithm (default from settings)
            expire_minutes: Token expiration in minutes (default from settings)
            credentials: Dict of username -> password (default from settings)
        """
        self.secret_key = secret_key or settings.jwt_secret_key
        self.algorithm = algorithm or settings.jwt_algorithm
        self.expire_minutes = expire_minutes or settings.access_token_expire_minutes
        self.credentials = credentials or {settings.admin_username: settings.admin_password}

    @property
    def provider_name(self) -> str:
        return "simple"

    async def authenticate(self, username: str, password: str) -> Optional[UserInfo]:
        """Authenticate with username and password.

        Args:
            username: The username
            password: The password

        Returns:
            UserInfo if credentials are valid, None otherwise
        """
        if username not in self.credentials:
            return None
        if self.credentials[username] != password:
            return None

        return UserInfo(
            username=username,
            roles=["admin"],  # All simple auth users are admins
        )

    async def validate_token(self, token: str) -> Optional[UserInfo]:
        """Validate a JWT token.

        Args:
            token: The JWT token to validate

        Returns:
            UserInfo if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None

            # Get roles from token or default to admin
            roles = payload.get("roles", ["admin"])

            return UserInfo(
                username=username,
                email=payload.get("email"),
                display_name=payload.get("name"),
                roles=roles,
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def create_token(self, user: UserInfo) -> TokenResponse:
        """Create a JWT access token.

        Args:
            user: User information

        Returns:
            TokenResponse with JWT access token
        """
        expire = datetime.now(UTC) + timedelta(minutes=self.expire_minutes)
        to_encode = {
            "sub": user.username,
            "exp": expire,
            "roles": user.roles,
        }
        if user.email:
            to_encode["email"] = user.email
        if user.display_name:
            to_encode["name"] = user.display_name

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return TokenResponse(
            access_token=encoded_jwt,
            expires_in=self.expire_minutes * 60,
        )
