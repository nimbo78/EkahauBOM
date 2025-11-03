"""Configuration settings for Ekahau BOM Web API."""

from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = "development"  # development | production

    # Paths
    projects_dir: Path = Path("data/projects")
    index_file: Path = Path("data/index.json")

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

    # Authentication (JWT)
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VARIABLE"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # Admin credentials (в production использовать БД с хешированием)
    admin_username: str = "admin"
    admin_password: str = "EkahauAdmin"

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
