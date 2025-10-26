#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Parser for Ekahau .esx project files."""

import json
import logging
from pathlib import Path
from typing import Any
from zipfile import ZipFile, BadZipFile

from .constants import (
    ESX_ACCESS_POINTS_FILE,
    ESX_FLOOR_PLANS_FILE,
    ESX_SIMULATED_RADIOS_FILE,
    ESX_ANTENNA_TYPES_FILE,
    ESX_TAG_KEYS_FILE,
    ESX_PROJECT_FILE,
    ESX_MEASURED_AREAS_FILE,
    ESX_NOTES_FILE,
    ESX_CABLE_NOTES_FILE,
    ESX_PICTURE_NOTES_FILE,
    ESX_ACCESS_POINT_MODELS_FILE,
)

logger = logging.getLogger(__name__)


class EkahauParser:
    """Parser for Ekahau .esx project files.

    .esx files are ZIP archives containing JSON files with project data.
    """

    def __init__(self, esx_file: Path):
        """Initialize parser with path to .esx file.

        Args:
            esx_file: Path to the .esx file to parse

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not a .esx file
        """
        self.esx_file = Path(esx_file)

        if not self.esx_file.exists():
            raise FileNotFoundError(f"File not found: {self.esx_file}")

        if self.esx_file.suffix.lower() != '.esx':
            raise ValueError(f"Invalid file extension. Expected .esx, got {self.esx_file.suffix}")

        self._zip_file: ZipFile | None = None
        self._data_cache: dict[str, Any] = {}

    def __enter__(self):
        """Context manager entry."""
        try:
            self._zip_file = ZipFile(self.esx_file, 'r')
            logger.info(f"Opened .esx file: {self.esx_file}")
            return self
        except BadZipFile as e:
            raise ValueError(f"Invalid .esx file (not a valid ZIP): {self.esx_file}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._zip_file:
            self._zip_file.close()
            logger.debug(f"Closed .esx file: {self.esx_file}")

    def _read_json(self, filename: str) -> dict[str, Any]:
        """Read and parse JSON file from the archive.

        Args:
            filename: Name of the JSON file in the archive

        Returns:
            Parsed JSON data as dictionary

        Raises:
            KeyError: If file not found in archive
            json.JSONDecodeError: If file contains invalid JSON
        """
        if filename in self._data_cache:
            return self._data_cache[filename]

        if not self._zip_file:
            raise RuntimeError("Parser not opened. Use 'with' statement.")

        try:
            data = self._zip_file.read(filename)
            parsed = json.loads(data)
            self._data_cache[filename] = parsed
            logger.debug(f"Successfully parsed {filename}")
            return parsed
        except KeyError as e:
            raise KeyError(f"Required file '{filename}' not found in .esx archive") from e
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {filename}: {e.msg}",
                e.doc,
                e.pos
            ) from e

    def get_access_points(self) -> dict[str, Any]:
        """Get access points data from the project.

        Returns:
            Dictionary with access points data
        """
        return self._read_json(ESX_ACCESS_POINTS_FILE)

    def get_floor_plans(self) -> dict[str, Any]:
        """Get floor plans data from the project.

        Returns:
            Dictionary with floor plans data
        """
        return self._read_json(ESX_FLOOR_PLANS_FILE)

    def get_simulated_radios(self) -> dict[str, Any]:
        """Get simulated radios data from the project.

        Returns:
            Dictionary with simulated radios data
        """
        return self._read_json(ESX_SIMULATED_RADIOS_FILE)

    def get_antenna_types(self) -> dict[str, Any]:
        """Get antenna types data from the project.

        Returns:
            Dictionary with antenna types data
        """
        return self._read_json(ESX_ANTENNA_TYPES_FILE)

    def get_tag_keys(self) -> dict[str, Any]:
        """Get tag keys data from the project.

        Tag keys define the available tags that can be applied to access points.
        Tags were introduced in Ekahau v10.2+.

        Returns:
            Dictionary with tag keys data. Returns empty dict if tagKeys.json
            not found (for older Ekahau versions or projects without tags).
        """
        try:
            return self._read_json(ESX_TAG_KEYS_FILE)
        except KeyError:
            # tagKeys.json may not exist in older Ekahau projects
            logger.info(f"{ESX_TAG_KEYS_FILE} not found in project (older Ekahau version or no tags)")
            return {"tagKeys": []}

    def get_measured_areas(self) -> dict[str, Any]:
        """Get measured areas data from the project.

        Measured areas define coverage zones and excluded areas.

        Returns:
            Dictionary with measured areas data. Returns empty dict if not found.
        """
        try:
            return self._read_json(ESX_MEASURED_AREAS_FILE)
        except KeyError:
            logger.info(f"{ESX_MEASURED_AREAS_FILE} not found in project")
            return {"measuredAreas": []}

    def get_notes(self) -> dict[str, Any]:
        """Get notes data from the project.

        Returns:
            Dictionary with notes data. Returns empty dict if not found.
        """
        try:
            return self._read_json(ESX_NOTES_FILE)
        except KeyError:
            logger.debug(f"{ESX_NOTES_FILE} not found in project")
            return {"notes": []}

    def get_access_point_models(self) -> dict[str, Any]:
        """Get access point models data from the project.

        Contains detailed specifications for AP models.

        Returns:
            Dictionary with AP models data. Returns empty dict if not found.
        """
        try:
            return self._read_json(ESX_ACCESS_POINT_MODELS_FILE)
        except KeyError:
            logger.debug(f"{ESX_ACCESS_POINT_MODELS_FILE} not found in project")
            return {"accessPointModels": []}

    def get_project_metadata(self) -> dict[str, Any]:
        """Get project metadata from the project.

        Project metadata includes project name, customer, location, responsible person,
        schema version, and other project-level information.

        Returns:
            Dictionary with project metadata. Returns empty dict if not found.
        """
        try:
            data = self._read_json(ESX_PROJECT_FILE)
            # project.json contains {"project": {...}} structure
            return data.get("project", {})
        except KeyError:
            logger.warning(f"{ESX_PROJECT_FILE} not found in project")
            return {}

    def get_cable_notes(self) -> dict[str, Any]:
        """Get cable notes data from the project.

        Cable notes contain cabling infrastructure information with coordinates
        and references to text notes.

        Returns:
            Dictionary with cable notes data. Returns empty dict if not found.
        """
        try:
            return self._read_json(ESX_CABLE_NOTES_FILE)
        except KeyError:
            logger.debug(f"{ESX_CABLE_NOTES_FILE} not found in project")
            return {"cableNotes": []}

    def get_picture_notes(self) -> dict[str, Any]:
        """Get picture notes data from the project.

        Picture notes contain image annotations and related information.

        Returns:
            Dictionary with picture notes data. Returns empty dict if not found.
        """
        try:
            return self._read_json(ESX_PICTURE_NOTES_FILE)
        except KeyError:
            logger.debug(f"{ESX_PICTURE_NOTES_FILE} not found in project")
            return {"pictureNotes": []}

    def list_files(self) -> list[str]:
        """List all files in the .esx archive.

        Returns:
            List of filenames in the archive
        """
        if not self._zip_file:
            raise RuntimeError("Parser not opened. Use 'with' statement.")

        return self._zip_file.namelist()
