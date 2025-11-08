"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


class StorageBackend(ABC):
    """Abstract storage backend interface.

    All storage implementations must implement these methods.
    This enables switching between local filesystem, S3, and other storage backends.
    """

    @abstractmethod
    def save_file(self, project_id: UUID, file_path: str, content: bytes | BinaryIO) -> str:
        """Save file to storage.

        Args:
            project_id: Project UUID
            file_path: Relative file path within project (e.g., "reports/file.csv")
            content: File content as bytes or file-like object

        Returns:
            Storage path or key (local path for filesystem, S3 URI for S3)

        Raises:
            StorageError: If save fails
        """
        pass

    @abstractmethod
    def get_file(self, project_id: UUID, file_path: str) -> bytes:
        """Get file content.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If read fails
        """
        pass

    @abstractmethod
    def delete_project(self, project_id: UUID) -> bool:
        """Delete entire project directory and all its files.

        Args:
            project_id: Project UUID

        Returns:
            True if successful

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def delete_file(self, project_id: UUID, file_path: str) -> bool:
        """Delete specific file.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            True if successful, False if file doesn't exist

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def exists(self, project_id: UUID, file_path: str = "") -> bool:
        """Check if file or directory exists.

        Args:
            project_id: Project UUID
            file_path: Relative file path (empty = check project directory)

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def list_files(self, project_id: UUID, prefix: str = "", recursive: bool = True) -> list[str]:
        """List files in project directory.

        Args:
            project_id: Project UUID
            prefix: File path prefix filter (e.g., "reports/")
            recursive: Include subdirectories

        Returns:
            List of relative file paths
        """
        pass

    @abstractmethod
    def get_project_size(self, project_id: UUID) -> int:
        """Get total size of project.

        Args:
            project_id: Project UUID

        Returns:
            Size in bytes
        """
        pass

    @abstractmethod
    def get_file_path(self, project_id: UUID, file_path: str) -> str:
        """Get full storage path/key for file.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            Full path (string for local, S3 key for S3)
        """
        pass

    @abstractmethod
    def get_project_dir(self, project_id: UUID) -> Path | str:
        """Get project directory path.

        Args:
            project_id: Project UUID

        Returns:
            Directory path (Path for local, str for S3 prefix)
        """
        pass


class StorageError(Exception):
    """Storage operation error.

    Raised when storage backend operations fail (network issues, permissions, etc.).
    """

    pass
