#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for Ekahau project parser."""

from __future__ import annotations


import json
import pytest
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from ekahau_bom.parser import EkahauParser
from ekahau_bom.constants import (
    ESX_ACCESS_POINTS_FILE,
    ESX_FLOOR_PLANS_FILE,
    ESX_SIMULATED_RADIOS_FILE,
    ESX_ANTENNA_TYPES_FILE,
    ESX_TAG_KEYS_FILE,
    ESX_MEASURED_AREAS_FILE,
    ESX_NOTES_FILE,
    ESX_ACCESS_POINT_MODELS_FILE,
    ESX_PROJECT_FILE,
    ESX_CABLE_NOTES_FILE,
    ESX_PICTURE_NOTES_FILE,
    ESX_NETWORK_CAPACITY_SETTINGS_FILE,
)


@pytest.fixture
def create_valid_esx_file(tmp_path):
    """Create a valid .esx file with sample data."""

    def _create_esx(filename="test.esx", include_optional=True):
        esx_path = tmp_path / filename

        # Sample data
        access_points_data = {
            "accessPoints": [
                {"id": "ap-1", "name": "AP-01", "vendor": "Cisco", "model": "C9120AXI"}
            ]
        }

        floor_plans_data = {"floorPlans": [{"id": "floor-1", "name": "Floor 1"}]}

        simulated_radios_data = {
            "simulatedRadios": [
                {"id": "radio-1", "accessPointId": "ap-1", "frequencyBand": "5 GHz"}
            ]
        }

        antenna_types_data = {"antennaTypes": [{"id": "ant-1", "name": "ANT-2513P4M-N-R"}]}

        tag_keys_data = {"tagKeys": [{"id": "tag-1", "key": "Zone"}]}

        measured_areas_data = {"measuredAreas": [{"id": "area-1", "name": "Coverage Area"}]}

        notes_data = {"notes": [{"id": "note-1", "text": "Test note"}]}

        ap_models_data = {"accessPointModels": [{"id": "model-1", "name": "C9120AXI"}]}

        # Create ZIP file with JSON data
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps(access_points_data))
            zf.writestr(ESX_FLOOR_PLANS_FILE, json.dumps(floor_plans_data))
            zf.writestr(ESX_SIMULATED_RADIOS_FILE, json.dumps(simulated_radios_data))
            zf.writestr(ESX_ANTENNA_TYPES_FILE, json.dumps(antenna_types_data))

            if include_optional:
                zf.writestr(ESX_TAG_KEYS_FILE, json.dumps(tag_keys_data))
                zf.writestr(ESX_MEASURED_AREAS_FILE, json.dumps(measured_areas_data))
                zf.writestr(ESX_NOTES_FILE, json.dumps(notes_data))
                zf.writestr(ESX_ACCESS_POINT_MODELS_FILE, json.dumps(ap_models_data))

        return esx_path

    return _create_esx


@pytest.fixture
def create_invalid_json_esx(tmp_path):
    """Create an .esx file with invalid JSON."""

    def _create_invalid():
        esx_path = tmp_path / "invalid.esx"
        with ZipFile(esx_path, "w") as zf:
            # Write invalid JSON
            zf.writestr(ESX_ACCESS_POINTS_FILE, "{invalid json content")
        return esx_path

    return _create_invalid


@pytest.fixture
def create_corrupt_zip(tmp_path):
    """Create a corrupt ZIP file."""

    def _create_corrupt():
        corrupt_path = tmp_path / "corrupt.esx"
        # Write garbage data
        corrupt_path.write_text("This is not a valid ZIP file")
        return corrupt_path

    return _create_corrupt


class TestEkahauParserInit:
    """Test parser initialization."""

    def test_init_with_valid_file(self, create_valid_esx_file):
        """Test initialization with valid .esx file."""
        esx_file = create_valid_esx_file()
        parser = EkahauParser(esx_file)
        assert parser.esx_file == esx_file

    def test_init_with_nonexistent_file(self, tmp_path):
        """Test initialization with nonexistent file raises FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.esx"
        with pytest.raises(FileNotFoundError, match="File not found"):
            EkahauParser(nonexistent)

    def test_init_with_wrong_extension(self, tmp_path):
        """Test initialization with wrong file extension raises ValueError."""
        wrong_ext = tmp_path / "test.zip"
        wrong_ext.touch()
        with pytest.raises(ValueError, match="Invalid file extension"):
            EkahauParser(wrong_ext)

    def test_init_accepts_string_path(self, create_valid_esx_file):
        """Test that init accepts string path (converted to Path)."""
        esx_file = create_valid_esx_file()
        parser = EkahauParser(str(esx_file))
        assert isinstance(parser.esx_file, Path)


class TestEkahauParserContextManager:
    """Test context manager functionality."""

    def test_context_manager_opens_file(self, create_valid_esx_file):
        """Test that context manager opens the file."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            assert parser._zip_file is not None

    def test_context_manager_closes_file(self, create_valid_esx_file):
        """Test that context manager closes the file on exit."""
        esx_file = create_valid_esx_file()
        parser = EkahauParser(esx_file)
        with parser:
            assert parser._zip_file is not None
        # After exiting, zip should be closed (we can't check directly but it should not raise)

    def test_context_manager_with_corrupt_zip(self, create_corrupt_zip):
        """Test that context manager raises ValueError for corrupt ZIP."""
        corrupt_file = create_corrupt_zip()
        with pytest.raises(ValueError, match="not a valid ZIP"):
            with EkahauParser(corrupt_file):
                pass


class TestEkahauParserReadJSON:
    """Test JSON reading functionality."""

    def test_read_json_basic(self, create_valid_esx_file):
        """Test basic JSON reading."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser._read_json(ESX_ACCESS_POINTS_FILE)
            assert "accessPoints" in data
            assert len(data["accessPoints"]) == 1

    def test_read_json_caching(self, create_valid_esx_file):
        """Test that JSON data is cached."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            # First read
            data1 = parser._read_json(ESX_ACCESS_POINTS_FILE)
            # Second read should return cached data
            data2 = parser._read_json(ESX_ACCESS_POINTS_FILE)
            # Should be the same object (from cache)
            assert data1 is data2
            # Cache should contain the file
            assert ESX_ACCESS_POINTS_FILE in parser._data_cache

    def test_read_json_without_context_manager(self, create_valid_esx_file):
        """Test that reading JSON without context manager raises RuntimeError."""
        esx_file = create_valid_esx_file()
        parser = EkahauParser(esx_file)
        with pytest.raises(RuntimeError, match="not opened"):
            parser._read_json(ESX_ACCESS_POINTS_FILE)

    def test_read_json_missing_file(self, create_valid_esx_file):
        """Test reading non-existent file raises KeyError."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            with pytest.raises(KeyError, match="not found in .esx archive"):
                parser._read_json("nonexistent.json")

    def test_read_json_invalid_json(self, create_invalid_json_esx):
        """Test reading invalid JSON raises JSONDecodeError."""
        esx_file = create_invalid_json_esx()
        with EkahauParser(esx_file) as parser:
            with pytest.raises(json.JSONDecodeError):
                parser._read_json(ESX_ACCESS_POINTS_FILE)


class TestEkahauParserGetMethods:
    """Test getter methods for project data."""

    def test_get_access_points(self, create_valid_esx_file):
        """Test getting access points data."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_access_points()
            assert "accessPoints" in data
            assert data["accessPoints"][0]["vendor"] == "Cisco"

    def test_get_floor_plans(self, create_valid_esx_file):
        """Test getting floor plans data."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_floor_plans()
            assert "floorPlans" in data
            assert data["floorPlans"][0]["name"] == "Floor 1"

    def test_get_simulated_radios(self, create_valid_esx_file):
        """Test getting simulated radios data."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_simulated_radios()
            assert "simulatedRadios" in data
            assert data["simulatedRadios"][0]["frequencyBand"] == "5 GHz"

    def test_get_antenna_types(self, create_valid_esx_file):
        """Test getting antenna types data."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_antenna_types()
            assert "antennaTypes" in data
            assert data["antennaTypes"][0]["name"] == "ANT-2513P4M-N-R"

    def test_get_tag_keys_present(self, create_valid_esx_file):
        """Test getting tag keys when file exists."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_tag_keys()
            assert "tagKeys" in data
            assert data["tagKeys"][0]["key"] == "Zone"

    def test_get_tag_keys_missing(self, create_valid_esx_file):
        """Test getting tag keys when file doesn't exist (older projects)."""
        esx_file = create_valid_esx_file(include_optional=False)
        with EkahauParser(esx_file) as parser:
            data = parser.get_tag_keys()
            # Should return empty tagKeys list instead of raising error
            assert data == {"tagKeys": []}

    def test_get_measured_areas_present(self, create_valid_esx_file):
        """Test getting measured areas when file exists."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_measured_areas()
            assert "measuredAreas" in data
            assert data["measuredAreas"][0]["name"] == "Coverage Area"

    def test_get_measured_areas_missing(self, create_valid_esx_file):
        """Test getting measured areas when file doesn't exist."""
        esx_file = create_valid_esx_file(include_optional=False)
        with EkahauParser(esx_file) as parser:
            data = parser.get_measured_areas()
            assert data == {"measuredAreas": []}

    def test_get_notes_present(self, create_valid_esx_file):
        """Test getting notes when file exists."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_notes()
            assert "notes" in data
            assert data["notes"][0]["text"] == "Test note"

    def test_get_notes_missing(self, create_valid_esx_file):
        """Test getting notes when file doesn't exist."""
        esx_file = create_valid_esx_file(include_optional=False)
        with EkahauParser(esx_file) as parser:
            data = parser.get_notes()
            assert data == {"notes": []}

    def test_get_access_point_models_present(self, create_valid_esx_file):
        """Test getting AP models when file exists."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            data = parser.get_access_point_models()
            assert "accessPointModels" in data
            assert data["accessPointModels"][0]["name"] == "C9120AXI"

    def test_get_access_point_models_missing(self, create_valid_esx_file):
        """Test getting AP models when file doesn't exist."""
        esx_file = create_valid_esx_file(include_optional=False)
        with EkahauParser(esx_file) as parser:
            data = parser.get_access_point_models()
            assert data == {"accessPointModels": []}

    def test_get_project_metadata_missing_file(self, tmp_path):
        """Test get_project_metadata when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without project.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            metadata = parser.get_project_metadata()
            assert metadata == {}

    def test_get_project_metadata_missing_project_key(self, tmp_path):
        """Test get_project_metadata when project.json exists but has no 'project' key."""
        esx_path = tmp_path / "minimal.esx"

        # Create archive with project.json but without 'project' key
        project_data = {"someOtherKey": "value"}  # No 'project' key
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))
            zf.writestr(ESX_PROJECT_FILE, json.dumps(project_data))

        with EkahauParser(esx_path) as parser:
            metadata = parser.get_project_metadata()
            # Should return empty dict when 'project' key is missing
            assert metadata == {}

    def test_get_cable_notes_missing_file(self, tmp_path):
        """Test get_cable_notes when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without cableNotes.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            cable_notes = parser.get_cable_notes()
            assert cable_notes == {"cableNotes": []}

    def test_get_picture_notes_missing_file(self, tmp_path):
        """Test get_picture_notes when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without pictureNotes.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            picture_notes = parser.get_picture_notes()
            assert picture_notes == {"pictureNotes": []}

    def test_get_network_capacity_settings_missing_file(self, tmp_path):
        """Test get_network_capacity_settings when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without networkCapacitySettings.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            settings = parser.get_network_capacity_settings()
            assert settings == {"networkCapacitySettings": []}


class TestEkahauParserListFiles:
    """Test file listing functionality."""

    def test_list_files(self, create_valid_esx_file):
        """Test listing files in the archive."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            files = parser.list_files()
            # Should contain at least the required files
            assert ESX_ACCESS_POINTS_FILE in files
            assert ESX_FLOOR_PLANS_FILE in files
            assert ESX_SIMULATED_RADIOS_FILE in files
            assert ESX_ANTENNA_TYPES_FILE in files

    def test_list_files_without_context_manager(self, create_valid_esx_file):
        """Test that listing files without context manager raises RuntimeError."""
        esx_file = create_valid_esx_file()
        parser = EkahauParser(esx_file)
        with pytest.raises(RuntimeError, match="not opened"):
            parser.list_files()

    def test_list_files_includes_optional(self, create_valid_esx_file):
        """Test that list_files includes optional files when present."""
        esx_file = create_valid_esx_file(include_optional=True)
        with EkahauParser(esx_file) as parser:
            files = parser.list_files()
            assert ESX_TAG_KEYS_FILE in files
            assert ESX_MEASURED_AREAS_FILE in files
            assert ESX_NOTES_FILE in files
            assert ESX_ACCESS_POINT_MODELS_FILE in files


class TestEkahauParserIntegration:
    """Integration tests for parser."""

    def test_multiple_reads_in_one_context(self, create_valid_esx_file):
        """Test multiple reads in one context."""
        esx_file = create_valid_esx_file()
        with EkahauParser(esx_file) as parser:
            aps = parser.get_access_points()
            floors = parser.get_floor_plans()
            radios = parser.get_simulated_radios()

            assert "accessPoints" in aps
            assert "floorPlans" in floors
            assert "simulatedRadios" in radios

    def test_parser_reusable(self, create_valid_esx_file):
        """Test that parser can be reused with context manager."""
        esx_file = create_valid_esx_file()
        parser = EkahauParser(esx_file)

        # First use
        with parser:
            data1 = parser.get_access_points()
            assert "accessPoints" in data1

        # Second use - cache should be cleared
        parser._data_cache.clear()
        with parser:
            data2 = parser.get_access_points()
            assert "accessPoints" in data2

    def test_unicode_in_json(self, tmp_path):
        """Test parser handles unicode in JSON data."""
        esx_path = tmp_path / "unicode.esx"

        unicode_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "name": "点接入",  # Chinese
                    "vendor": "Производитель",  # Russian
                    "model": "Modèle",  # French
                }
            ]
        }

        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps(unicode_data, ensure_ascii=False))

        with EkahauParser(esx_path) as parser:
            data = parser.get_access_points()
            assert data["accessPoints"][0]["name"] == "点接入"
            assert data["accessPoints"][0]["vendor"] == "Производитель"
            assert data["accessPoints"][0]["model"] == "Modèle"

    def test_empty_project(self, tmp_path):
        """Test parser with minimal/empty project data."""
        esx_path = tmp_path / "empty.esx"

        empty_data = {"accessPoints": []}

        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps(empty_data))
            zf.writestr(ESX_FLOOR_PLANS_FILE, json.dumps({"floorPlans": []}))
            zf.writestr(ESX_SIMULATED_RADIOS_FILE, json.dumps({"simulatedRadios": []}))
            zf.writestr(ESX_ANTENNA_TYPES_FILE, json.dumps({"antennaTypes": []}))

        with EkahauParser(esx_path) as parser:
            aps = parser.get_access_points()
            assert aps["accessPoints"] == []

    def test_get_project_metadata_missing_file(self, tmp_path):
        """Test get_project_metadata when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without project.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            metadata = parser.get_project_metadata()
            assert metadata == {}

    def test_get_cable_notes_missing_file(self, tmp_path):
        """Test get_cable_notes when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without cableNotes.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            cable_notes = parser.get_cable_notes()
            assert cable_notes == {"cableNotes": []}

    def test_get_picture_notes_missing_file(self, tmp_path):
        """Test get_picture_notes when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without pictureNotes.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            picture_notes = parser.get_picture_notes()
            assert picture_notes == {"pictureNotes": []}

    def test_get_network_capacity_settings_missing_file(self, tmp_path):
        """Test get_network_capacity_settings when file is missing."""
        esx_path = tmp_path / "minimal.esx"

        # Create minimal archive without networkCapacitySettings.json
        with ZipFile(esx_path, "w") as zf:
            zf.writestr(ESX_ACCESS_POINTS_FILE, json.dumps({"accessPoints": []}))

        with EkahauParser(esx_path) as parser:
            settings = parser.get_network_capacity_settings()
            assert settings == {"networkCapacitySettings": []}
