"""Configuration settings for Ekahau BOM Web API."""

from pathlib import Path
from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = "development"  # development | production

    # Storage Backend Configuration
    storage_backend: Literal["local", "s3"] = "local"  # local | s3

    # Paths (used when storage_backend=local)
    projects_dir: Path = Path("data/projects")
    index_file: Path = Path("data/index.json")

    # S3-Compatible Storage Settings (used when storage_backend=s3)
    # Works with AWS S3, MinIO, Wasabi, DigitalOcean Spaces, Dell EMC ECS, etc.
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"  # Provider-specific region
    s3_bucket_name: str | None = None
    s3_endpoint_url: str | None = None  # Custom endpoint for MinIO/Corporate S3
    s3_use_ssl: bool = True
    s3_verify: bool = True  # Can be False for dev/test (not recommended for prod)
    s3_ca_bundle: str | None = None  # Path to custom CA certificate bundle

    # API
    api_prefix: str = "/api"
    max_upload_size: int = 500 * 1024 * 1024  # 500 MB

    # Processing
    ekahau_bom_flags: dict = {
        "group_aps": True,
        "output_formats": ["csv", "xlsx", "html"],
        "visualize_floor_plans": True,
    }

    # Short links
    short_link_length: int = 8
    short_link_expiry_days: int = 30

    # Authentication Backend
    # Options: "simple" (username/password + JWT) or "oauth2" (Keycloak/OIDC)
    auth_backend: Literal["simple", "oauth2"] = "simple"

    # JWT Settings (used by both simple and oauth2 backends)
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VARIABLE"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # Simple Auth: Admin credentials (used when auth_backend=simple)
    admin_username: str = "admin"
    admin_password: str = "EkahauAdmin"

    # OAuth2/OIDC Settings (used when auth_backend=oauth2)
    # Works with Keycloak, Azure AD, Okta, Google Workspace
    oauth2_issuer: str = ""  # e.g., https://keycloak.example.com/realms/ekahau
    oauth2_client_id: str = ""
    oauth2_client_secret: str = ""
    oauth2_redirect_uri: str = "http://localhost:4200/auth/callback"
    oauth2_admin_role: str = "ekahau-admin"  # Role name for admin access
    oauth2_user_role: str = "ekahau-user"  # Role name for user access

    # SMTP Settings (for email notifications)
    smtp_host: str = ""  # e.g., "smtp.gmail.com"
    smtp_port: int = 587  # TLS: 587, SSL: 465
    smtp_username: str = ""  # SMTP username
    smtp_password: str = ""  # SMTP password or app password
    smtp_from_email: str = "noreply@ekahau-bom.local"  # Sender email address
    smtp_use_tls: bool = True  # Use TLS encryption

    # Scheduler Settings
    scheduler_timezone: str = "UTC"  # Timezone for scheduled jobs
    scheduler_enabled: bool = True  # Enable/disable scheduler

    # CORS
    cors_origins: list[str] = ["http://localhost:4200"]

    model_config = ConfigDict(env_file=".env")


settings = Settings()

# Production CORS
if settings.environment == "production":
    settings.cors_origins = [
        "https://ekahau-bom.example.com",
        # Add production domains here
    ]


def get_settings() -> Settings:
    """Get application settings.

    Returns:
        Settings instance

    Note:
        This function is useful for dependency injection in FastAPI.
    """
    return settings
