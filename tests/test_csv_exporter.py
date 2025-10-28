#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for CSV exporter."""

from __future__ import annotations


import csv
from pathlib import Path

import pytest

from ekahau_bom.exporters.csv_exporter import CSVExporter
from ekahau_bom.models import ProjectData, AccessPoint, Antenna, Tag, Radio, Floor


@pytest.fixture
def output_dir(tmp_path):
    """Create temporary output directory."""
    return tmp_path


@pytest.fixture
def sample_access_points():
    """Create sample access points for testing."""
    return [
        AccessPoint(
            vendor="Cisco",
            model="C9120AXI",
            color="Red",
            floor_name="Floor 1",
            name="AP-01",
            location_x=10.5,
            location_y=20.3,
            mounting_height=3.2,
            azimuth=45.0,
            tilt=10.0,
            antenna_height=3.5,
            enabled=True,
            tags=[Tag("Zone", "Office", "zone-id"), Tag("Building", "HQ", "bldg-id")],
        ),
        AccessPoint(
            vendor="Cisco",
            model="C9120AXI",
            color="Red",
            floor_name="Floor 1",
            name="AP-02",
            location_x=15.7,
            location_y=25.9,
            mounting_height=3.2,
            azimuth=90.0,
            tilt=10.0,
            antenna_height=3.5,
            enabled=True,
            tags=[Tag("Zone", "Office", "zone-id"), Tag("Building", "HQ", "bldg-id")],
        ),
        AccessPoint(
            vendor="Cisco",
            model="C9130AXI",
            color="Blue",
            floor_name="Floor 2",
            name="AP-03",
            location_x=5.0,
            location_y=10.0,
            mounting_height=4.5,
            azimuth=180.0,
            tilt=15.0,
            antenna_height=4.8,
            enabled=False,
            tags=[Tag("Zone", "Warehouse", "zone-id")],
        ),
        AccessPoint(
            vendor="Aruba",
            model="AP-515",
            color=None,
            floor_name="Floor 1",
            name="AP-04",
            location_x=None,
            location_y=None,
            mounting_height=None,
            azimuth=None,
            tilt=None,
            antenna_height=None,
            enabled=True,
            tags=[],
        ),
    ]


@pytest.fixture
def sample_antennas():
    """Create sample antennas for testing."""
    return [
        Antenna(
            "ANT-2513P4M-N-R",
            "ant1",
            access_point_id="ap1",
            is_external=True,
            spatial_streams=2,
            model_number="ANT-2513P4M-N-R",
        ),
        Antenna(
            "ANT-2513P4M-N-R",
            "ant1",
            access_point_id="ap2",
            is_external=True,
            spatial_streams=2,
            model_number="ANT-2513P4M-N-R",
        ),
        Antenna(
            "ANT-20",
            "ant2",
            access_point_id="ap3",
            is_external=True,
            spatial_streams=1,
            model_number="ANT-20",
        ),
    ]


@pytest.fixture
def sample_radios():
    """Create sample radios for testing."""
    return [
        Radio(
            id="radio-1",
            access_point_id="ap-1",
            frequency_band="5 GHz",
            channel=36,
            channel_width=80,
            tx_power=20.0,
            standard="802.11ax",
        ),
        Radio(
            id="radio-2",
            access_point_id="ap-2",
            frequency_band="2.4 GHz",
            channel=6,
            channel_width=20,
            tx_power=18.0,
            standard="802.11ax",
        ),
        Radio(
            id="radio-3",
            access_point_id="ap-3",
            frequency_band="6 GHz",
            channel=37,
            channel_width=160,
            tx_power=15.0,
            standard="802.11be",
        ),
    ]


@pytest.fixture
def sample_project_data(sample_access_points, sample_antennas, sample_radios):
    """Create sample project data."""
    floors = {"f1": Floor("f1", "Floor 1"), "f2": Floor("f2", "Floor 2")}
    return ProjectData(
        project_name="Test Project",
        access_points=sample_access_points,
        antennas=sample_antennas,
        radios=sample_radios,
        floors=floors,
    )


class TestCSVExporter:
    """Test CSV exporter functionality."""

    def test_format_name(self, output_dir):
        """Test format name property."""
        exporter = CSVExporter(output_dir)
        assert exporter.format_name == "CSV"

    def test_export_creates_all_files(self, output_dir, sample_project_data):
        """Test that export creates all expected CSV files."""
        exporter = CSVExporter(output_dir)
        files = exporter.export(sample_project_data)

        # Should create 4 files: access_points, access_points_detailed, antennas, analytics
        assert len(files) == 4

        # All files should exist
        for file_path in files:
            assert file_path.exists()
            assert file_path.suffix == ".csv"

    def test_export_access_points_file_structure(
        self, output_dir, sample_access_points
    ):
        """Test access points file has correct structure."""
        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(sample_access_points, "Test")

        # Read the file
        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check header - simple BOM with vendor, model, quantity only
        assert rows[0] == ["Vendor", "Model", "Quantity"]

        # Should have aggregated rows (all identical vendor+model combinations are grouped)
        assert len(rows) > 1  # At least header + data

    def test_export_access_points_aggregation(self, output_dir):
        """Test that identical access points are aggregated by vendor and model."""
        # Create duplicate APs with same vendor+model but different color/floor/tags
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                tags=[Tag("Zone", "Office", "zone-id")],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Blue",  # Different color
                floor_name="Floor 2",  # Different floor
                tags=[Tag("Zone", "Lobby", "zone-id")],  # Different tags
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-515",
                color="Blue",
                floor_name="Floor 2",
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(aps, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Header + 2 unique vendor+model combinations
        assert len(rows) == 3

        # Find the Cisco row and check quantity (should be 2 despite different color/floor/tags)
        cisco_row = [row for row in rows[1:] if row[0] == "Cisco"][0]
        assert cisco_row[2] == "2"  # Quantity is now at index 2

    def test_export_access_points_simple_bom(self, output_dir):
        """Test that BOM export only contains vendor, model, quantity (not tags, color, floor)."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                tags=[
                    Tag("Zone", "Office", "zone-id"),
                    Tag("Building", "HQ", "bldg-id"),
                    Tag("Area", "North", "area-id"),
                ],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(aps, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # BOM should only have 3 columns: Vendor, Model, Quantity
        assert len(rows[0]) == 3
        assert rows[0] == ["Vendor", "Model", "Quantity"]
        assert len(rows[1]) == 3  # Data row also has 3 columns
        assert rows[1] == ["Cisco", "C9120AXI", "1"]

    def test_export_access_points_ignores_color_and_tags(self, output_dir):
        """Test that BOM groups by vendor+model only, ignoring color, tags, floor."""
        # Create 3 APs with same vendor+model but different color/tags/floor
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                tags=[Tag("Zone", "Office", "zone-id")],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color=None,  # Different color (None)
                floor_name="Floor 2",  # Different floor
                tags=[],  # No tags
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Blue",  # Different color
                floor_name="Floor 3",  # Different floor
                tags=[Tag("Building", "HQ", "bldg-id")],  # Different tags
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(aps, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Should have header + 1 data row (all 3 APs grouped into one)
        assert len(rows) == 2
        assert rows[1] == ["Cisco", "C9120AXI", "3"]  # Quantity 3

    def test_export_detailed_access_points_structure(
        self, output_dir, sample_access_points
    ):
        """Test detailed access points file has correct structure."""
        exporter = CSVExporter(output_dir)
        output_file = exporter._export_detailed_access_points(
            sample_access_points, [], "Test"
        )

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check header
        expected_headers = [
            "AP Name",
            "Vendor",
            "Model",
            "Floor",
            "Location X (m)",
            "Location Y (m)",
            "Mounting Height (m)",
            "Azimuth (°)",
            "Tilt (°)",
            "Color",
            "Tags",
            "Enabled",
        ]
        assert rows[0] == expected_headers

        # Should have one row per AP (not aggregated)
        assert len(rows) == len(sample_access_points) + 1  # +1 for header

    def test_export_detailed_access_points_number_formatting(self, output_dir):
        """Test number formatting in detailed export."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                name="AP-01",
                location_x=10.567,
                location_y=20.345,
                mounting_height=3.289,
                azimuth=45.67,
                tilt=10.89,
                enabled=True,
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_detailed_access_points(aps, [], "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        data_row = rows[1]
        # Location X/Y and mounting height: 2 decimal places
        assert data_row[4] == "10.57"
        assert data_row[5] == "20.34"  # 20.345 rounds to 20.34 (banker's rounding)
        assert data_row[6] == "3.29"
        # Azimuth and tilt: 1 decimal place
        assert data_row[7] == "45.7"
        assert data_row[8] == "10.9"

    def test_export_detailed_access_points_none_values(self, output_dir):
        """Test handling of None values in detailed export."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color=None,
                floor_name="Floor 1",
                name=None,
                location_x=None,
                location_y=None,
                mounting_height=None,
                azimuth=None,
                tilt=None,
                enabled=True,
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_detailed_access_points(aps, [], "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        data_row = rows[1]
        # All None values should be empty strings
        assert data_row[0] == ""  # AP Name
        assert data_row[4] == ""  # Location X
        assert data_row[5] == ""  # Location Y
        assert data_row[6] == ""  # Mounting Height
        assert data_row[7] == ""  # Azimuth
        assert data_row[8] == ""  # Tilt
        assert data_row[9] == ""  # Color

    def test_export_detailed_access_points_enabled_field(self, output_dir):
        """Test enabled field formatting."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                enabled=True,
                tags=[],
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-515",
                color="Blue",
                floor_name="Floor 2",
                enabled=False,
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_detailed_access_points(aps, [], "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[1][11] == "Yes"
        assert rows[2][11] == "No"

    def test_export_antennas_structure(self, output_dir, sample_antennas):
        """Test antennas file has correct structure."""
        exporter = CSVExporter(output_dir)
        output_file = exporter._export_antennas(sample_antennas, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check header
        assert rows[0] == ["Antenna Model", "Quantity"]

        # Should have aggregated rows
        assert len(rows) > 1

    def test_export_antennas_aggregation(self, output_dir):
        """Test antenna counting with dual-band aggregation."""
        antennas = [
            # Dual-band antenna (2.4GHz + 5GHz) with different spatial streams
            Antenna(
                "Huawei 27013718 2.4GHz 13dBi",
                "ant1",
                access_point_id="ap1",
                is_external=True,
                spatial_streams=4,
                model_number="27013718",
            ),
            Antenna(
                "Huawei 27013718 5GHz 16dBi",
                "ant2",
                access_point_id="ap1",
                is_external=True,
                spatial_streams=6,  # Max spatial streams = physical antenna count
                model_number="27013718",
            ),
            # Single-band antenna
            Antenna(
                "Cisco ANT-20",
                "ant3",
                access_point_id="ap2",
                is_external=True,
                spatial_streams=2,
                model_number="ANT-20",
            ),
            # Integrated antenna (filtered out)
            Antenna("Integrated Antenna", "ant4", is_external=False),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_antennas(antennas, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Header + 2 unique external antenna rows (dual-band aggregated, integrated filtered)
        assert len(rows) == 3

        # Find Huawei dual-band antenna - should show max spatial streams (6)
        huawei_row = [row for row in rows[1:] if "27013718" in row[0]][0]
        assert "Dual-Band" in huawei_row[0]  # Dual-band label
        assert huawei_row[1] == "6"  # Max spatial streams from 5GHz radio

        # Find Cisco single-band antenna
        cisco_row = [row for row in rows[1:] if "ANT-20" in row[0]][0]
        assert cisco_row[1] == "2"

    def test_export_analytics_with_data(
        self, output_dir, sample_access_points, sample_radios
    ):
        """Test analytics export with data."""
        exporter = CSVExporter(output_dir)
        output_file = exporter._export_analytics(
            sample_access_points, sample_radios, "Test"
        )

        assert output_file is not None
        assert output_file.exists()

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for section headers
        assert "=== MOUNTING METRICS ===" in content
        assert "=== HEIGHT DISTRIBUTION ===" in content
        assert "=== INSTALLATION SUMMARY ===" in content
        assert "=== RADIO CONFIGURATION ANALYTICS ===" in content

    def test_export_analytics_no_data(self, output_dir):
        """Test analytics returns None when no data available."""
        # APs with no mounting data
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=None,
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_analytics(aps, [], "Test")

        # Should return None when no analytics data
        assert output_file is None

    def test_export_analytics_mounting_metrics(self, output_dir):
        """Test mounting metrics section in analytics."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=3.0,
                azimuth=45.0,
                tilt=10.0,
                tags=[],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=4.0,
                azimuth=90.0,
                tilt=15.0,
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_analytics(aps, [], "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Find metrics rows
        content = [row for row in rows if row]

        # Should have average height (3.5m)
        height_rows = [
            row
            for row in content
            if len(row) > 0 and "Average Mounting Height" in row[0]
        ]
        assert len(height_rows) == 1
        assert "3.50" in height_rows[0][1]

    def test_export_analytics_height_distribution(self, output_dir):
        """Test height distribution in analytics."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=2.0,  # < 2.5m
                tags=[],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=3.0,  # 2.5-3.5m
                tags=[],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=4.0,  # 3.5-4.5m
                tags=[],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=5.0,  # 4.5-6.0m
                tags=[],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=7.0,  # > 6.0m
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_analytics(aps, [], "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for all height ranges
        assert "< 2.5m" in content
        assert "2.5-3.5m" in content
        assert "3.5-4.5m" in content
        assert "4.5-6.0m" in content
        assert "> 6.0m" in content

    def test_export_analytics_radio_metrics(
        self, output_dir, sample_access_points, sample_radios
    ):
        """Test radio metrics in analytics."""
        exporter = CSVExporter(output_dir)
        output_file = exporter._export_analytics(
            sample_access_points, sample_radios, "Test"
        )

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for radio sections
        assert "=== FREQUENCY BANDS ===" in content
        assert "=== WI-FI STANDARDS ===" in content
        assert "=== CHANNEL WIDTHS ===" in content
        assert "=== TRANSMIT POWER ===" in content

        # Check for specific values from sample_radios
        assert "5 GHz" in content
        assert "2.4 GHz" in content
        assert "6 GHz" in content
        assert "802.11ax" in content
        assert "802.11be" in content

    def test_export_analytics_installation_summary(self, output_dir):
        """Test installation summary section."""
        aps = [
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=2.0,  # Requires adjustment (< 2.5m)
                azimuth=45.0,
                tilt=10.0,
                tags=[],
            ),
            AccessPoint(
                vendor="Cisco",
                model="C9120AXI",
                color="Red",
                floor_name="Floor 1",
                mounting_height=3.0,  # OK
                azimuth=None,
                tilt=15.0,
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_analytics(aps, [], "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        content = [row for row in rows if row]

        # Find summary section
        summary_start = None
        for i, row in enumerate(content):
            if "=== INSTALLATION SUMMARY ===" in row[0]:
                summary_start = i
                break

        assert summary_start is not None

        # Check summary values
        summary_section = content[summary_start:]

        # Total APs
        total_aps_row = [
            row for row in summary_section if len(row) > 0 and "Total APs" in row[0]
        ][0]
        assert total_aps_row[1] == "2"

        # APs with tilt
        tilt_row = [
            row
            for row in summary_section
            if len(row) > 0 and "APs with Tilt Data" in row[0]
        ][0]
        assert tilt_row[1] == "2"

        # APs with azimuth
        azimuth_row = [
            row
            for row in summary_section
            if len(row) > 0 and "APs with Azimuth Data" in row[0]
        ][0]
        assert azimuth_row[1] == "1"

        # APs requiring adjustment
        adjust_row = [
            row
            for row in summary_section
            if len(row) > 0 and "APs Requiring Height Adjustment" in row[0]
        ][0]
        assert adjust_row[1] == "1"

    def test_export_unicode_support(self, output_dir):
        """Test CSV exporter handles unicode characters."""
        aps = [
            AccessPoint(
                vendor="Производитель",  # Russian
                model="模型",  # Chinese
                color="Röt",  # German
                floor_name="étage",  # French
                name="点",  # Chinese
                tags=[Tag("Ключ", "Значение", "key-id")],  # Russian
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(aps, "Test")

        # Should not raise exception
        assert output_file.exists()

        # Read and verify unicode was preserved
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # BOM only contains vendor and model, not color or floor
        assert "Производитель" in content  # Vendor
        assert "模型" in content  # Model

    def test_export_with_empty_lists(self, output_dir):
        """Test export with empty lists doesn't crash."""
        project_data = ProjectData(
            project_name="Empty Project",
            access_points=[],
            antennas=[],
            radios=[],
            floors={},
        )

        exporter = CSVExporter(output_dir)
        # Should not raise exception
        files = exporter.export(project_data)

        # Should still create files (even if empty)
        assert len(files) >= 2  # At least AP and antenna files

    def test_csv_quoting(self, output_dir):
        """Test that CSV files use proper quoting."""
        aps = [
            AccessPoint(
                vendor="Cisco, Inc.",  # Comma in name
                model='Model "X"',  # Quotes in name
                color="Red",
                floor_name="Floor 1",
                tags=[],
            ),
        ]

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(aps, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have quotes around fields with special characters
        assert '"Cisco, Inc."' in content
        # In CSV, double quotes are escaped as double-double-quotes
        assert 'Model ""X""' in content

    def test_export_access_points_with_full_metadata(self, tmp_path):
        """Test CSV export with complete metadata."""
        from ekahau_bom.models import ProjectMetadata

        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-515",
                color="Red",
                floor_name="Floor 1",
                tags=[],
            )
        ]
        metadata = ProjectMetadata(
            name="Enterprise WiFi Project",
            customer="Acme Corporation",
            location="Building A, Floor 3",
            responsible_person="John Doe",
            schema_version="1.0",
        )

        exporter = CSVExporter(output_dir)
        output_file = exporter._export_access_points(aps, "Test", metadata=metadata)

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have metadata as comments
        assert "# Project Name: Enterprise WiFi Project" in content
        assert "# Customer: Acme Corporation" in content
        assert "# Location: Building A, Floor 3" in content
        assert "# Responsible Person: John Doe" in content

    def test_export_detailed_access_points_with_antenna_height_fallback(self, tmp_path):
        """Test detailed CSV export with mounting height from radio antenna_height."""
        from ekahau_bom.models import Radio

        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # AP without mounting_height
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-515",
                color="Red",
                floor_name="Floor 1",
                name="AP-Office-01",
                tags=[],
                mounting_height=None,  # No mounting height on AP
            )
        ]

        # Radio with antenna_height
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_height=2.5,  # Should be used as fallback
            )
        ]

        exporter = CSVExporter(output_dir)
        # Correct signature: _export_detailed_access_points(access_points, radios, project_name)
        output_file = exporter._export_detailed_access_points(aps, radios, "Test")

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have antenna_height as mounting height
        assert "2.50" in content  # Formatted antenna_height
