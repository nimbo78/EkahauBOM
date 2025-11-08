"""Storage abstraction layer.

Provides storage backend abstraction for local filesystem and S3-compatible storage.
"""

from app.services.storage.base import StorageBackend, StorageError
from app.services.storage.factory import StorageFactory
from app.services.storage.local import LocalStorage
from app.services.storage.s3 import S3Storage

__all__ = [
    "StorageBackend",
    "StorageError",
    "StorageFactory",
    "LocalStorage",
    "S3Storage",
]
