"""Base authentication provider abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserInfo:
    """User information from authentication."""

    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    roles: list[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles or "ekahau-admin" in self.roles


@dataclass
class TokenResponse:
    """Token response from authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name (e.g., 'simple', 'oauth2')."""
        pass

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> Optional[UserInfo]:
        """Authenticate with username and password.

        Args:
            username: The username
            password: The password

        Returns:
            UserInfo if authentication successful, None otherwise
        """
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[UserInfo]:
        """Validate an access token.

        Args:
            token: The access token to validate

        Returns:
            UserInfo if token is valid, None otherwise
        """
        pass

    @abstractmethod
    def create_token(self, user: UserInfo) -> TokenResponse:
        """Create an access token for a user.

        Args:
            user: User information

        Returns:
            TokenResponse with access token
        """
        pass

    def get_login_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """Get OAuth2 login URL (for OAuth2 providers).

        Args:
            state: CSRF state parameter
            redirect_uri: Redirect URI after authentication

        Returns:
            Login URL for OAuth2 flow, None for simple auth
        """
        return None

    async def handle_callback(self, code: str, state: str, redirect_uri: str) -> Optional[UserInfo]:
        """Handle OAuth2 callback (for OAuth2 providers).

        Args:
            code: Authorization code from IdP
            state: CSRF state parameter
            redirect_uri: Redirect URI

        Returns:
            UserInfo if callback successful, None otherwise
        """
        return None

    async def refresh_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """Refresh an access token (for OAuth2 providers).

        Args:
            refresh_token: The refresh token

        Returns:
            New TokenResponse if refresh successful, None otherwise
        """
        return None

    @property
    def supports_oauth2(self) -> bool:
        """Check if this provider supports OAuth2 flow."""
        return False
