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

    def list_files(self) -> list[str]:
        """List all files in the .esx archive.

        Returns:
            List of filenames in the archive
        """
        if not self._zip_file:
            raise RuntimeError("Parser not opened. Use 'with' statement.")

        return self._zip_file.namelist()
