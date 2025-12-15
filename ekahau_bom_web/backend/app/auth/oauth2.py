"""OAuth2/OIDC authentication provider (Keycloak, Azure AD, Okta, etc.)."""

from datetime import datetime, timedelta, UTC
from typing import Optional
from urllib.parse import urlencode
import secrets

import httpx
import jwt

from app.config import settings
from .base import AuthProvider, UserInfo, TokenResponse


class OAuth2AuthProvider(AuthProvider):
    """OAuth2/OIDC authentication provider for Keycloak and other IdPs."""

    def __init__(
        self,
        issuer: str = None,
        client_id: str = None,
        client_secret: str = None,
        admin_role: str = None,
        user_role: str = None,
        jwt_secret: str = None,
        jwt_algorithm: str = None,
        jwt_expire_minutes: int = None,
    ):
        """Initialize OAuth2 provider.

        Args:
            issuer: OIDC issuer URL (e.g., https://keycloak.example.com/realms/ekahau)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            admin_role: Role name for admin access (default: ekahau-admin)
            user_role: Role name for user access (default: ekahau-user)
            jwt_secret: Secret for signing internal JWT (default from settings)
            jwt_algorithm: JWT algorithm (default from settings)
            jwt_expire_minutes: Internal token expiration (default from settings)
        """
        self.issuer = issuer or settings.oauth2_issuer
        self.client_id = client_id or settings.oauth2_client_id
        self.client_secret = client_secret or settings.oauth2_client_secret
        self.admin_role = admin_role or getattr(settings, "oauth2_admin_role", "ekahau-admin")
        self.user_role = user_role or getattr(settings, "oauth2_user_role", "ekahau-user")

        # For creating internal JWT after OAuth2 authentication
        self.jwt_secret = jwt_secret or settings.jwt_secret_key
        self.jwt_algorithm = jwt_algorithm or settings.jwt_algorithm
        self.jwt_expire_minutes = jwt_expire_minutes or settings.access_token_expire_minutes

        # OIDC endpoints (will be discovered from issuer)
        self._oidc_config: Optional[dict] = None
        self._jwks: Optional[dict] = None

    @property
    def provider_name(self) -> str:
        return "oauth2"

    @property
    def supports_oauth2(self) -> bool:
        return True

    async def _get_oidc_config(self) -> dict:
        """Fetch OIDC configuration from issuer."""
        if self._oidc_config is not None:
            return self._oidc_config

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.issuer}/.well-known/openid-configuration")
            response.raise_for_status()
            self._oidc_config = response.json()
            return self._oidc_config

    async def _get_jwks(self) -> dict:
        """Fetch JWKS (JSON Web Key Set) for token validation."""
        if self._jwks is not None:
            return self._jwks

        config = await self._get_oidc_config()
        jwks_uri = config.get("jwks_uri")

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            self._jwks = response.json()
            return self._jwks

    async def authenticate(self, username: str, password: str) -> Optional[UserInfo]:
        """Not supported for OAuth2 - use OAuth2 flow instead.

        For Resource Owner Password Credentials flow (not recommended):
        This could be implemented but is generally discouraged.
        """
        return None

    async def validate_token(self, token: str) -> Optional[UserInfo]:
        """Validate an access token (internal JWT or IdP token).

        Args:
            token: The access token to validate

        Returns:
            UserInfo if token is valid, None otherwise
        """
        # First try to validate as internal JWT
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            username = payload.get("sub")
            if username is None:
                return None

            return UserInfo(
                username=username,
                email=payload.get("email"),
                display_name=payload.get("name"),
                roles=payload.get("roles", []),
            )
        except jwt.InvalidTokenError:
            pass

        # If internal JWT validation fails, try IdP token validation
        try:
            return await self._validate_idp_token(token)
        except Exception:
            return None

    async def _validate_idp_token(self, token: str) -> Optional[UserInfo]:
        """Validate a token from the IdP using JWKS."""
        try:
            # Get JWKS for verification
            jwks = await self._get_jwks()

            # Get token header to find the key
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find the key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                    break

            if key is None:
                return None

            # Verify and decode the token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )

            # Extract user info
            username = payload.get("preferred_username") or payload.get("sub")
            email = payload.get("email")
            name = payload.get("name")

            # Extract roles from token
            roles = self._extract_roles(payload)

            return UserInfo(
                username=username,
                email=email,
                display_name=name,
                roles=roles,
            )
        except Exception:
            return None

    def _extract_roles(self, token_payload: dict) -> list[str]:
        """Extract roles from IdP token payload.

        Supports Keycloak realm_access.roles and resource_access.{client}.roles
        """
        roles = []

        # Keycloak realm roles
        realm_access = token_payload.get("realm_access", {})
        roles.extend(realm_access.get("roles", []))

        # Keycloak client roles
        resource_access = token_payload.get("resource_access", {})
        client_access = resource_access.get(self.client_id, {})
        roles.extend(client_access.get("roles", []))

        # Azure AD roles
        if "roles" in token_payload:
            roles.extend(token_payload["roles"])

        # Map to internal roles
        internal_roles = []
        if self.admin_role in roles:
            internal_roles.append("admin")
        if self.user_role in roles:
            internal_roles.append("user")

        # If no specific roles found but user is authenticated, give user role
        if not internal_roles:
            internal_roles.append("user")

        return internal_roles

    def create_token(self, user: UserInfo) -> TokenResponse:
        """Create an internal JWT access token after OAuth2 authentication.

        Args:
            user: User information from OAuth2 callback

        Returns:
            TokenResponse with internal JWT access token
        """
        expire = datetime.now(UTC) + timedelta(minutes=self.jwt_expire_minutes)
        to_encode = {
            "sub": user.username,
            "exp": expire,
            "roles": user.roles,
            "provider": "oauth2",
        }
        if user.email:
            to_encode["email"] = user.email
        if user.display_name:
            to_encode["name"] = user.display_name

        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

        return TokenResponse(
            access_token=encoded_jwt,
            expires_in=self.jwt_expire_minutes * 60,
        )

    def get_login_url(self, state: str, redirect_uri: str) -> str:
        """Get the OAuth2 authorization URL.

        Args:
            state: CSRF state parameter
            redirect_uri: Redirect URI after authentication

        Returns:
            Authorization URL to redirect user to
        """
        # Build authorization URL
        # Note: We use issuer + standard path for Keycloak
        # For other IdPs, may need to use OIDC discovery
        auth_endpoint = f"{self.issuer}/protocol/openid-connect/auth"

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "openid profile email",
            "redirect_uri": redirect_uri,
            "state": state,
        }

        return f"{auth_endpoint}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, redirect_uri: str) -> Optional[UserInfo]:
        """Handle the OAuth2 callback and exchange code for tokens.

        Args:
            code: Authorization code from IdP
            state: CSRF state (should be validated by caller)
            redirect_uri: Redirect URI (must match original request)

        Returns:
            UserInfo if callback successful, None otherwise
        """
        try:
            # Exchange code for tokens
            token_endpoint = f"{self.issuer}/protocol/openid-connect/token"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                )
                response.raise_for_status()
                tokens = response.json()

            # Validate ID token and extract user info
            id_token = tokens.get("id_token")
            if id_token:
                return await self._validate_idp_token(id_token)

            # Fallback: use access token
            access_token = tokens.get("access_token")
            if access_token:
                return await self._validate_idp_token(access_token)

            return None

        except Exception:
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token from IdP

        Returns:
            New TokenResponse if refresh successful, None otherwise
        """
        try:
            token_endpoint = f"{self.issuer}/protocol/openid-connect/token"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                    },
                )
                response.raise_for_status()
                tokens = response.json()

            # Validate new ID token
            id_token = tokens.get("id_token")
            if id_token:
                user = await self._validate_idp_token(id_token)
                if user:
                    return self.create_token(user)

            return None

        except Exception:
            return None


def generate_state() -> str:
    """Generate a secure random state for CSRF protection."""
    return secrets.token_urlsafe(32)
