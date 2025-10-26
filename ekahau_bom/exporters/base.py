#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base class for exporters."""

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path

from ..models import ProjectData

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for all exporters.

    Exporters are responsible for converting ProjectData into various
    output formats (CSV, Excel, HTML, JSON, etc.).
    """

    def __init__(self, output_dir: Path):
        """Initialize exporter with output directory.

        Args:
            output_dir: Directory where export files will be saved
        """
        self.output_dir = Path(output_dir)

    @abstractmethod
    def export(self, project_data: ProjectData) -> list[Path]:
        """Export project data to one or more files.

        Args:
            project_data: Processed project data to export

        Returns:
            List of paths to created files

        Raises:
            IOError: If export fails
        """
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        pass

    def _sanitize_filename(self, filename: str) -> str:
        r"""Sanitize filename by removing invalid characters.

        Removes or replaces characters that are not allowed in filenames
        on Windows: < > : " / \ | ? *

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for all operating systems
        """
        # Replace invalid characters with underscore
        # Windows reserved: < > : " / \ | ? *
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')

        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    def _get_output_filename(self, project_name: str, suffix: str) -> Path:
        """Generate output filename.

        Args:
            project_name: Name of the project (base name)
            suffix: Type/category suffix (e.g., 'access_points', 'antennas')

        Returns:
            Full path to output file
        """
        # Sanitize project name to remove invalid filename characters
        safe_project_name = self._sanitize_filename(project_name)
        filename = f"{safe_project_name}_{suffix}"
        return self.output_dir / filename

    def log_export_success(self, files: list[Path]) -> None:
        """Log successful export.

        Args:
            files: List of exported files
        """
        logger.info(f"{self.format_name} export completed: {len(files)} file(s) created")
        for file in files:
            logger.info(f"  - {file}")
