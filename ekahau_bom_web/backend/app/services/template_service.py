"""Batch template service."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from app.models import (
    BatchTemplate,
    ProcessingRequest,
    TemplateCreateRequest,
    TemplateListItem,
    TemplateUpdateRequest,
)

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing batch processing templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template service.

        Args:
            templates_dir: Optional directory for storing templates
        """
        self.templates_dir = templates_dir or Path("data/templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._init_predefined_templates()

    def _get_template_path(self, template_id: UUID) -> Path:
        """Get path to template JSON file.

        Args:
            template_id: Template UUID

        Returns:
            Path to template JSON file
        """
        return self.templates_dir / f"{template_id}.json"

    def _init_predefined_templates(self) -> None:
        """Initialize predefined system templates if they don't exist."""
        predefined = self._get_predefined_templates()

        for template in predefined:
            template_path = self._get_template_path(template.template_id)
            if not template_path.exists():
                self._save_template(template)
                logger.info(f"Created predefined template: {template.name}")

    def _get_predefined_templates(self) -> list[BatchTemplate]:
        """Get list of predefined system templates.

        Returns:
            List of predefined templates
        """
        # Use fixed UUIDs for predefined templates for consistency
        csv_only_id = UUID("00000000-0000-0000-0000-000000000001")
        full_reports_id = UUID("00000000-0000-0000-0000-000000000002")
        quick_processing_id = UUID("00000000-0000-0000-0000-000000000003")

        return [
            # CSV Only - Minimal processing, CSV output only
            BatchTemplate(
                template_id=csv_only_id,
                name="CSV Only",
                description="Minimal processing with CSV output only. Fast and lightweight.",
                is_system=True,
                processing_options=ProcessingRequest(
                    group_by="model",
                    output_formats=["csv"],
                    visualize_floor_plans=False,
                    show_azimuth_arrows=False,
                    include_text_notes=False,
                    include_picture_notes=False,
                    include_cable_notes=False,
                ),
                parallel_workers=4,
            ),
            # Full Reports - Complete processing with all formats
            BatchTemplate(
                template_id=full_reports_id,
                name="Full Reports",
                description="Complete processing with all formats (CSV, Excel, HTML, PDF) and floor plan visualizations.",
                is_system=True,
                processing_options=ProcessingRequest(
                    group_by="model",
                    output_formats=["csv", "excel", "html", "pdf"],
                    visualize_floor_plans=True,
                    show_azimuth_arrows=True,
                    ap_opacity=0.6,
                    include_text_notes=True,
                    include_picture_notes=True,
                    include_cable_notes=True,
                ),
                parallel_workers=2,
            ),
            # Quick Processing - Balanced settings for fast results
            BatchTemplate(
                template_id=quick_processing_id,
                name="Quick Processing",
                description="Balanced settings for quick results with CSV, Excel, and basic visualizations.",
                is_system=True,
                processing_options=ProcessingRequest(
                    group_by="model",
                    output_formats=["csv", "excel"],
                    visualize_floor_plans=True,
                    show_azimuth_arrows=False,
                    ap_opacity=0.6,
                    include_text_notes=False,
                    include_picture_notes=False,
                    include_cable_notes=False,
                ),
                parallel_workers=4,
            ),
        ]

    def _save_template(self, template: BatchTemplate) -> None:
        """Save template to JSON file.

        Args:
            template: Template to save
        """
        template_path = self._get_template_path(template.template_id)
        template_path.parent.mkdir(parents=True, exist_ok=True)

        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(template.model_dump(mode="json"), f, indent=2, default=str)

    def load_template(self, template_id: UUID) -> Optional[BatchTemplate]:
        """Load template from storage.

        Args:
            template_id: Template UUID

        Returns:
            Template or None if not found
        """
        template_path = self._get_template_path(template_id)
        if not template_path.exists():
            return None

        with open(template_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return BatchTemplate(**data)

    def list_templates(self, include_system: bool = True) -> list[BatchTemplate]:
        """List all templates.

        Args:
            include_system: Whether to include system templates

        Returns:
            List of templates
        """
        templates = []

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    template = BatchTemplate(**data)

                    # Filter system templates if requested
                    if not include_system and template.is_system:
                        continue

                    templates.append(template)
            except Exception as e:
                logger.warning(f"Failed to load template {template_file.name}: {e}")
                continue

        # Sort: system templates first, then by name
        templates.sort(key=lambda t: (not t.is_system, t.name.lower()))

        return templates

    def create_template(
        self, request: TemplateCreateRequest, created_by: str = "admin"
    ) -> BatchTemplate:
        """Create a new template.

        Args:
            request: Template creation request
            created_by: User creating the template

        Returns:
            Created template
        """
        template = BatchTemplate(
            template_id=uuid4(),
            name=request.name,
            description=request.description,
            created_by=created_by,
            processing_options=request.processing_options,
            parallel_workers=request.parallel_workers,
            is_system=False,  # User templates are never system templates
        )

        self._save_template(template)
        logger.info(f"Created template {template.template_id}: {template.name}")

        return template

    def update_template(
        self, template_id: UUID, request: TemplateUpdateRequest
    ) -> Optional[BatchTemplate]:
        """Update an existing template.

        Args:
            template_id: Template UUID
            request: Template update request

        Returns:
            Updated template or None if not found

        Raises:
            ValueError: If trying to update a system template
        """
        template = self.load_template(template_id)
        if not template:
            return None

        # Prevent updating system templates
        if template.is_system:
            raise ValueError("Cannot update system templates")

        # Update fields if provided
        if request.name is not None:
            template.name = request.name
        if request.description is not None:
            template.description = request.description
        if request.processing_options is not None:
            template.processing_options = request.processing_options
        if request.parallel_workers is not None:
            template.parallel_workers = request.parallel_workers

        self._save_template(template)
        logger.info(f"Updated template {template_id}: {template.name}")

        return template

    def delete_template(self, template_id: UUID) -> bool:
        """Delete a template.

        Args:
            template_id: Template UUID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete a system template
        """
        template = self.load_template(template_id)
        if not template:
            return False

        # Prevent deleting system templates
        if template.is_system:
            raise ValueError("Cannot delete system templates")

        template_path = self._get_template_path(template_id)
        template_path.unlink()
        logger.info(f"Deleted template {template_id}: {template.name}")

        return True

    def increment_usage(self, template_id: UUID) -> None:
        """Increment template usage count and update last_used timestamp.

        Args:
            template_id: Template UUID
        """
        template = self.load_template(template_id)
        if not template:
            return

        template.usage_count += 1
        template.last_used = datetime.now(UTC)

        self._save_template(template)
        logger.debug(f"Incremented usage for template {template_id}: {template.usage_count}")


# Singleton instance
template_service = TemplateService()
