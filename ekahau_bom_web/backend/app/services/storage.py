"""Storage Service - работа с файловой системой."""

import json
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID

import aiofiles

from app.config import settings
from app.models import ProjectMetadata


class StorageService:
    """Сервис для работы с файловой системой."""

    def __init__(self):
        """Инициализация сервиса."""
        self.projects_dir = settings.projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: UUID) -> Path:
        """
        Получить директорию проекта.

        Args:
            project_id: UUID проекта

        Returns:
            Path к директории проекта
        """
        return self.projects_dir / str(project_id)

    async def save_uploaded_file(
        self, project_id: UUID, filename: str, file_content: bytes
    ) -> Path:
        """
        Сохранить загруженный .esx файл.

        Args:
            project_id: UUID проекта
            filename: Имя файла
            file_content: Содержимое файла

        Returns:
            Path к сохранённому файлу
        """
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Сохранить оригинальный файл
        file_path = project_dir / "original.esx"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return file_path

    def save_metadata(self, project_id: UUID, metadata: ProjectMetadata) -> None:
        """
        Сохранить metadata.json.

        Args:
            project_id: UUID проекта
            metadata: Метаданные проекта
        """
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(
            parents=True, exist_ok=True
        )  # Создать директорию если не существует
        metadata_file = project_dir / "metadata.json"

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_metadata(self, project_id: UUID) -> Optional[ProjectMetadata]:
        """
        Загрузить metadata.json.

        Args:
            project_id: UUID проекта

        Returns:
            Метаданные проекта или None если файл не существует
        """
        metadata_file = self.get_project_dir(project_id) / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ProjectMetadata(**data)

    def get_reports_dir(self, project_id: UUID) -> Path:
        """
        Получить директорию с отчётами.

        Args:
            project_id: UUID проекта

        Returns:
            Path к директории с отчётами
        """
        return self.get_project_dir(project_id) / "reports"

    def get_visualizations_dir(self, project_id: UUID) -> Path:
        """
        Получить директорию с визуализациями.

        Args:
            project_id: UUID проекта

        Returns:
            Path к директории с визуализациями
        """
        # Visualizations are created by EkahauBOM CLI in output_dir/visualizations/
        # Since we pass reports_dir as output_dir, they end up in reports/visualizations/
        return self.get_reports_dir(project_id) / "visualizations"

    def list_report_files(self, project_id: UUID) -> list[dict]:
        """
        Список файлов отчётов.

        Args:
            project_id: UUID проекта

        Returns:
            Список словарей с информацией о файлах (filename, size)
        """
        reports_dir = self.get_reports_dir(project_id)
        if not reports_dir.exists():
            return []

        files = []
        for f in reports_dir.iterdir():
            if f.is_file():
                files.append({"filename": f.name, "size": f.stat().st_size})
        return files

    def list_visualization_files(self, project_id: UUID) -> list[dict]:
        """
        Список файлов визуализаций.

        Args:
            project_id: UUID проекта

        Returns:
            Список словарей с информацией о файлах (filename, size)
        """
        viz_dir = self.get_visualizations_dir(project_id)
        if not viz_dir.exists():
            return []

        files = []
        for f in viz_dir.iterdir():
            if f.suffix == ".png":
                files.append({"filename": f.name, "size": f.stat().st_size})
        return files

    def load_project_data(self, project_id: UUID) -> Optional[dict]:
        """
        Загрузить {project_name}_data.json из reports директории.

        Args:
            project_id: UUID проекта

        Returns:
            Словарь с данными проекта или None если файл не существует
        """
        # Get metadata to find project name
        metadata = self.load_metadata(project_id)
        if not metadata or not metadata.project_name:
            return None

        # Construct path to data.json
        reports_dir = self.get_reports_dir(project_id)
        data_file = reports_dir / f"{metadata.project_name}_data.json"

        if not data_file.exists():
            return None

        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_project(self, project_id: UUID) -> None:
        """
        Удалить проект полностью.

        Args:
            project_id: UUID проекта
        """
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)


# Singleton instance
storage_service = StorageService()
