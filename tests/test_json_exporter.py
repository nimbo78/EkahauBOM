#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for JSON exporter."""

from __future__ import annotations


import json
import pytest
from pathlib import Path
from ekahau_bom.exporters.json_exporter import JSONExporter, CompactJSONExporter
from ekahau_bom.models import (
    ProjectData,
    AccessPoint,
    Antenna,
    Tag,
    Floor,
    Radio,
    CableNote,
    ProjectMetadata,
)


@pytest.fixture
def sample_project_data():
    """Create sample project data for testing."""
    aps = [
        AccessPoint(
            id="ap1",
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag("Location", "Building A", "tag1")],
        ),
        AccessPoint(
            id="ap2",
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag("Location", "Building A", "tag1")],
        ),
        AccessPoint(
            id="ap3", vendor="Cisco", model="AP-635", color="Red", floor_name="Floor 2", tags=[]
        ),
        AccessPoint(
            id="ap4", vendor="Aruba", model="AP-515", color="Yellow", floor_name="Floor 1", tags=[]
        ),
        AccessPoint(
            id="ap5",
            vendor="Aruba",
            model="AP-635",
            color="Blue",
            floor_name="Floor 2",
            tags=[Tag("Location", "Building B", "tag2")],
        ),
    ]
    antennas = [
        Antenna("ANT-2513P4M-N-R", "ant1"),
        Antenna("ANT-2513P4M-N-R", "ant1"),
        Antenna("ANT-20", "ant2"),
    ]
    floors = {
        "floor1": Floor("floor1", "Floor 1"),
        "floor2": Floor("floor2", "Floor 2"),
    }
    return ProjectData(
        access_points=aps, antennas=antennas, floors=floors, project_name="Test Project"
    )


class TestJSONExporter:
    """Test JSONExporter class."""

    def test_export_creates_file(self, sample_project_data, tmp_path):
        """Test that export creates JSON file."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()
        assert files[0].suffix == ".json"
        assert "Test Project" in files[0].name

    def test_format_name(self, tmp_path):
        """Test format_name property."""
        exporter = JSONExporter(tmp_path)
        assert exporter.format_name == "JSON"

    def test_json_is_valid(self, sample_project_data, tmp_path):
        """Test that exported JSON is valid and can be parsed."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict)

    def test_json_has_metadata(self, sample_project_data, tmp_path):
        """Test that JSON has metadata section."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert data["metadata"]["file_name"] == "Test Project"
        assert data["metadata"]["export_format"] == "json"
        assert "version" in data["metadata"]

    def test_json_has_summary(self, sample_project_data, tmp_path):
        """Test that JSON has summary section."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "summary" in data
        assert data["summary"]["total_access_points"] == 5
        assert data["summary"]["total_antennas"] == 3
        assert data["summary"]["unique_vendors"] == 2
        assert data["summary"]["unique_floors"] == 2

    def test_json_has_floors(self, sample_project_data, tmp_path):
        """Test that JSON has floors section."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "floors" in data
        assert isinstance(data["floors"], list)
        assert len(data["floors"]) == 2

        floor_names = [floor["name"] for floor in data["floors"]]
        assert "Floor 1" in floor_names
        assert "Floor 2" in floor_names

    def test_json_has_access_points_bom(self, sample_project_data, tmp_path):
        """Test that JSON has access points BOM."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "access_points" in data
        assert "bill_of_materials" in data["access_points"]
        assert isinstance(data["access_points"]["bill_of_materials"], list)

        bom = data["access_points"]["bill_of_materials"]
        assert len(bom) > 0

        # Check BOM structure
        first_item = bom[0]
        assert "vendor" in first_item
        assert "model" in first_item
        assert "floor" in first_item
        assert "quantity" in first_item

    def test_json_has_access_points_details(self, sample_project_data, tmp_path):
        """Test that JSON has detailed access points list."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "details" in data["access_points"]
        assert isinstance(data["access_points"]["details"], list)
        assert len(data["access_points"]["details"]) == 5

    def test_json_has_tags(self, sample_project_data, tmp_path):
        """Test that JSON includes tags."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check that some APs have tags
        details = data["access_points"]["details"]
        ap_with_tags = [ap for ap in details if ap["tags"]]

        assert len(ap_with_tags) > 0

        # Check tag structure
        first_tag = ap_with_tags[0]["tags"][0]
        assert "key" in first_tag
        assert "value" in first_tag
        assert "tag_key_id" in first_tag

    def test_json_has_antennas_bom(self, sample_project_data, tmp_path):
        """Test that JSON has antennas BOM."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "antennas" in data
        assert "bill_of_materials" in data["antennas"]

        bom = data["antennas"]["bill_of_materials"]
        assert len(bom) == 2  # 2 unique antennas

        # Check antenna structure
        first_antenna = bom[0]
        assert "name" in first_antenna
        assert "quantity" in first_antenna

    def test_json_has_analytics(self, sample_project_data, tmp_path):
        """Test that JSON has analytics section."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "analytics" in data
        assert "by_vendor" in data["analytics"]
        assert "by_floor" in data["analytics"]
        assert "by_color" in data["analytics"]
        assert "by_model" in data["analytics"]

    def test_json_analytics_structure(self, sample_project_data, tmp_path):
        """Test analytics section structure."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        vendor_analytics = data["analytics"]["by_vendor"]
        assert "total" in vendor_analytics
        assert "groups" in vendor_analytics
        assert isinstance(vendor_analytics["groups"], list)

        # Check group structure
        if vendor_analytics["groups"]:
            first_group = vendor_analytics["groups"][0]
            assert "name" in first_group
            assert "count" in first_group
            assert "percentage" in first_group

    def test_json_analytics_percentages(self, sample_project_data, tmp_path):
        """Test that analytics includes correct percentages."""
        exporter = JSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        vendor_analytics = data["analytics"]["by_vendor"]
        total_percentage = sum(group["percentage"] for group in vendor_analytics["groups"])

        # Should sum to approximately 100%
        assert 99.9 <= total_percentage <= 100.1

    def test_json_pretty_print(self, sample_project_data, tmp_path):
        """Test that JSON is pretty-printed by default."""
        exporter = JSONExporter(tmp_path, indent=2)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            content = f.read()

        # Check for indentation (newlines and spaces)
        assert "\n" in content
        assert "  " in content  # 2-space indentation

    def test_compact_json_exporter(self, sample_project_data, tmp_path):
        """Test compact JSON exporter."""
        exporter = CompactJSONExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            content = f.read()

        # Compact JSON should have fewer newlines
        compact_newlines = content.count("\n")

        # Compare with pretty-printed
        pretty_exporter = JSONExporter(tmp_path, indent=2)
        pretty_files = pretty_exporter.export(sample_project_data)

        with open(pretty_files[0], "r", encoding="utf-8") as f:
            pretty_content = f.read()

        pretty_newlines = pretty_content.count("\n")

        assert compact_newlines < pretty_newlines

    def test_compact_json_format_name(self, tmp_path):
        """Test compact JSON format name."""
        exporter = CompactJSONExporter(tmp_path)
        assert exporter.format_name == "JSON (Compact)"

    def test_empty_project(self, tmp_path):
        """Test export with empty project."""
        project_data = ProjectData(
            access_points=[], antennas=[], floors={}, project_name="Empty Project"
        )

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)

        assert len(files) == 1
        assert files[0].exists()

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["summary"]["total_access_points"] == 0
        assert data["summary"]["total_antennas"] == 0
        assert len(data["floors"]) == 0

    def test_json_special_characters(self, tmp_path):
        """Test that special characters are properly handled in JSON."""
        aps = [
            AccessPoint(
                'Test"Vendor',
                "Model'123",
                None,
                "Floor\n1",
                tags=[Tag("Key&1", "Value<2>", "tag1")],
            ),
        ]
        project_data = ProjectData(
            access_points=aps, antennas=[], floors={}, project_name='Test"Project'
        )

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should be able to parse without errors
        assert data["metadata"]["file_name"] == 'Test"Project'

    def test_json_unicode_support(self, tmp_path):
        """Test that JSON supports Unicode characters."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Тест",
                model="モデル-123",
                color="Yellow",
                floor_name="第1層",
                tags=[],
            ),
        ]
        project_data = ProjectData(
            access_points=aps, antennas=[], floors={}, project_name="テストプロジェクト"
        )

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)  # Use project_data instead of sample_project_data

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should handle Unicode without errors
        assert isinstance(data, dict)

    def test_json_with_metadata(self, tmp_path):
        """Test JSON export with project metadata."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1"
            )
        ]
        metadata = ProjectMetadata(
            name="Test Project",
            customer="Test Customer",
            location="Test Location",
            responsible_person="Test Person",
            schema_version="1.0",
            note_ids=["note1", "note2"],
            project_ancestors=["ancestor1"],
        )
        project_data = ProjectData(
            access_points=aps, antennas=[], floors={}, project_name="Test", metadata=metadata
        )

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check metadata section
        assert "metadata" in data
        assert "project_info" in data["metadata"]
        project_info = data["metadata"]["project_info"]
        assert project_info["project_name"] == "Test Project"
        assert project_info["customer"] == "Test Customer"
        assert project_info["location"] == "Test Location"
        assert project_info["responsible_person"] == "Test Person"
        assert project_info["schema_version"] == "1.0"
        assert project_info["note_ids"] == ["note1", "note2"]
        assert project_info["project_ancestors"] == ["ancestor1"]

    def test_json_with_radios(self, tmp_path):
        """Test JSON export with radios data."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1"
            )
        ]
        radios = [
            Radio(id="radio1", access_point_id="ap1", frequency_band="2.4GHz"),
            Radio(id="radio2", access_point_id="ap1", frequency_band="5GHz"),
        ]
        project_data = ProjectData(
            access_points=aps, antennas=[], floors={}, project_name="Test", radios=radios
        )

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check that radios data is processed (radio metrics should be calculated)
        assert "summary" in data

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check that radios data is processed (radio metrics should be calculated)
        assert "summary" in data
        # Radio metrics would be in analytics if present

    def test_json_with_cable_notes(self, tmp_path):
        """Test JSON export with cable notes."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1"
            )
        ]
        cable_notes = [
            CableNote(id="cable1", floor_plan_id="floor1"),
            CableNote(id="cable2", floor_plan_id="floor1"),
        ]
        floors = {"floor1": Floor("floor1", "Floor 1")}
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors=floors,
            project_name="Test",
            cable_notes=cable_notes,
        )

        exporter = JSONExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check that cable data is processed
        assert "summary" in data
