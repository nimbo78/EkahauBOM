"""Local filesystem storage backend."""

import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from app.services.storage.base import StorageBackend, StorageError


class LocalStorage(StorageBackend):
    """Local filesystem storage implementation.

    Stores all project files on local filesystem with directory structure:
        base_dir/
            {project_id}/
                original.esx
                metadata.json
                reports/
                    *.csv, *.xlsx, *.html, *.pdf, *.json
                    visualizations/
                        *.png
    """

    def __init__(self, base_dir: Path):
        """Initialize local storage.

        Args:
            base_dir: Base directory for all projects
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, project_id: UUID, file_path: str, content: bytes | BinaryIO) -> str:
        """Save file to local filesystem.

        Args:
            project_id: Project UUID
            file_path: Relative file path within project
            content: File content as bytes or file-like object

        Returns:
            Absolute path to saved file

        Raises:
            StorageError: If save fails
        """
        full_path = self.get_project_dir(project_id) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if isinstance(content, bytes):
                full_path.write_bytes(content)
            else:
                # File-like object (BinaryIO)
                with open(full_path, "wb") as f:
                    shutil.copyfileobj(content, f)
            return str(full_path)
        except Exception as e:
            raise StorageError(f"Failed to save file {file_path}: {e}") from e

    def get_file(self, project_id: UUID, file_path: str) -> bytes:
        """Get file from local filesystem.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If read fails
        """
        full_path = self.get_project_dir(project_id) / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            return full_path.read_bytes()
        except Exception as e:
            raise StorageError(f"Failed to read file {file_path}: {e}") from e

    def delete_project(self, project_id: UUID) -> bool:
        """Delete project directory and all its files.

        Args:
            project_id: Project UUID

        Returns:
            True if successful

        Raises:
            StorageError: If deletion fails
        """
        project_dir = self.get_project_dir(project_id)
        if not project_dir.exists():
            return True  # Already deleted

        try:
            shutil.rmtree(project_dir)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete project {project_id}: {e}") from e

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
        full_path = self.get_project_dir(project_id) / file_path
        if not full_path.exists():
            return False

        try:
            full_path.unlink()
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete file {file_path}: {e}") from e

    def exists(self, project_id: UUID, file_path: str = "") -> bool:
        """Check if file or directory exists.

        Args:
            project_id: Project UUID
            file_path: Relative file path (empty = check project directory)

        Returns:
            True if exists, False otherwise
        """
        path = self.get_project_dir(project_id)
        if file_path:
            path = path / file_path
        return path.exists()

    def list_files(self, project_id: UUID, prefix: str = "", recursive: bool = True) -> list[str]:
        """List files in project directory.

        Args:
            project_id: Project UUID
            prefix: File path prefix filter (e.g., "reports/")
            recursive: Include subdirectories

        Returns:
            Sorted list of relative file paths
        """
        project_dir = self.get_project_dir(project_id)
        search_dir = project_dir / prefix if prefix else project_dir

        if not search_dir.exists():
            return []

        pattern = "**/*" if recursive else "*"
        files = [
            str(f.relative_to(project_dir)).replace("\\", "/")  # Normalize to forward slashes
            for f in search_dir.glob(pattern)
            if f.is_file()
        ]
        return sorted(files)

    def get_project_size(self, project_id: UUID) -> int:
        """Get total project size.

        Args:
            project_id: Project UUID

        Returns:
            Size in bytes
        """
        project_dir = self.get_project_dir(project_id)
        if not project_dir.exists():
            return 0

        total = 0
        for file in project_dir.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total

    def get_file_path(self, project_id: UUID, file_path: str) -> str:
        """Get full file path.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            Absolute path as string
        """
        return str(self.get_project_dir(project_id) / file_path)

    def get_project_dir(self, project_id: UUID) -> Path:
        """Get project directory path.

        Args:
            project_id: Project UUID

        Returns:
            Path to project directory
        """
        return self.base_dir / str(project_id)
