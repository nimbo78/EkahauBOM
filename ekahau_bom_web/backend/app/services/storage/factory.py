"""Storage backend factory."""

from app.config import Settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorage
from app.services.storage.s3 import S3Storage


class StorageFactory:
    """Factory for creating storage backends based on configuration."""

    @staticmethod
    def create_backend(settings: Settings) -> StorageBackend:
        """Create storage backend based on configuration.

        Args:
            settings: Application settings

        Returns:
            Storage backend instance (LocalStorage or S3Storage)

        Raises:
            ValueError: If backend type is unknown or configuration is invalid
        """
        backend_type = settings.storage_backend.lower()

        if backend_type == "local":
            return LocalStorage(base_dir=settings.projects_dir)

        elif backend_type == "s3":
            # Validate S3 configuration
            if not settings.s3_bucket_name:
                raise ValueError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")

            return S3Storage(
                bucket=settings.s3_bucket_name,
                region=settings.s3_region,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                endpoint_url=settings.s3_endpoint_url,
                use_ssl=settings.s3_use_ssl,
                verify=settings.s3_verify,
                ca_bundle=settings.s3_ca_bundle,
            )

        else:
            raise ValueError(
                f"Unknown storage backend: {backend_type}. " f"Supported: 'local', 's3'"
            )
