"""In-Memory Index Service for fast project lookups."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.config import settings
from app.models import ProcessingStatus, ProjectListItem, ProjectMetadata


class IndexService:
    """In-memory index for fast project searches."""

    def __init__(self):
        self.index_file = settings.index_file
        self._projects: dict[UUID, ProjectMetadata] = {}
        self._short_links: dict[str, UUID] = {}  # short_link -> project_id

    def load_from_disk(self) -> None:
        """Load index from disk (index.json)."""
        if not self.index_file.exists():
            return

        with open(self.index_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._projects = {}
        self._short_links = {}

        for project_data in data.get("projects", []):
            metadata = ProjectMetadata(**project_data)
            self._projects[metadata.project_id] = metadata

            if metadata.short_link:
                self._short_links[metadata.short_link] = metadata.project_id

    def save_to_disk(self) -> None:
        """Save index to disk (index.json)."""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "projects": [
                metadata.model_dump(mode="json") for metadata in self._projects.values()
            ]
        }

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, metadata: ProjectMetadata) -> None:
        """Add or update project in index."""
        self._projects[metadata.project_id] = metadata

        if metadata.short_link:
            self._short_links[metadata.short_link] = metadata.project_id

    def remove(self, project_id: UUID) -> None:
        """Remove project from index."""
        metadata = self._projects.get(project_id)
        if metadata and metadata.short_link:
            self._short_links.pop(metadata.short_link, None)

        self._projects.pop(project_id, None)

    def get(self, project_id: UUID) -> Optional[ProjectMetadata]:
        """Get project metadata by ID."""
        return self._projects.get(project_id)

    def get_by_short_link(self, short_link: str) -> Optional[ProjectMetadata]:
        """Get project metadata by short link."""
        project_id = self._short_links.get(short_link)
        if project_id:
            return self._projects.get(project_id)
        return None

    def list_all(
        self, status: Optional[ProcessingStatus] = None, limit: Optional[int] = None
    ) -> list[ProjectListItem]:
        """List all projects, optionally filtered by status."""
        projects = self._projects.values()

        # Filter by status
        if status:
            projects = [p for p in projects if p.processing_status == status]

        # Sort by upload date (newest first)
        projects = sorted(projects, key=lambda p: p.upload_date, reverse=True)

        # Limit results
        if limit:
            projects = list(projects)[:limit]

        # Convert to ProjectListItem
        return [
            ProjectListItem(
                project_id=p.project_id,
                project_name=p.project_name or p.filename,
                filename=p.filename,
                upload_date=p.upload_date,
                aps_count=p.aps_count,
                processing_status=p.processing_status,
                short_link=p.short_link,
            )
            for p in projects
        ]

    def search(self, query: str) -> list[ProjectListItem]:
        """Search projects by name or filename."""
        query_lower = query.lower()

        projects = [
            p
            for p in self._projects.values()
            if query_lower in (p.project_name or "").lower()
            or query_lower in p.filename.lower()
        ]

        # Sort by upload date (newest first)
        projects = sorted(projects, key=lambda p: p.upload_date, reverse=True)

        return [
            ProjectListItem(
                project_id=p.project_id,
                project_name=p.project_name or p.filename,
                filename=p.filename,
                upload_date=p.upload_date,
                aps_count=p.aps_count,
                processing_status=p.processing_status,
                short_link=p.short_link,
            )
            for p in projects
        ]

    def count(self, status: Optional[ProcessingStatus] = None) -> int:
        """Count projects, optionally filtered by status."""
        if status:
            return sum(
                1 for p in self._projects.values() if p.processing_status == status
            )
        return len(self._projects)


# Global singleton
index_service = IndexService()
