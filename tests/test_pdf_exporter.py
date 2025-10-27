#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for PDF exporter."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ekahau_bom.models import ProjectData, AccessPoint, Antenna, Tag, Floor, Radio


@pytest.fixture
def sample_project_data():
    """Create sample project data for testing."""
    aps = [
        AccessPoint(
            "Cisco",
            "AP-515",
            "Yellow",
            "Floor 1",
            tags=[Tag("Location", "Building A", "tag1")],
            location_x=10.5,
            location_y=20.3,
            mounting_height=3.2,
            azimuth=45.0,
            tilt=10.0,
        ),
        AccessPoint(
            "Cisco",
            "AP-515",
            "Yellow",
            "Floor 1",
            tags=[Tag("Location", "Building A", "tag1")],
            location_x=15.7,
            location_y=25.8,
            mounting_height=3.0,
            azimuth=90.0,
            tilt=5.0,
        ),
        AccessPoint(
            "Cisco",
            "AP-635",
            "Red",
            "Floor 2",
            tags=[],
            location_x=12.0,
            location_y=18.5,
            mounting_height=3.5,
            azimuth=180.0,
            tilt=15.0,
        ),
        AccessPoint(
            "Aruba",
            "AP-515",
            "Yellow",
            "Floor 1",
            tags=[],
            location_x=8.3,
            location_y=22.1,
            mounting_height=2.8,
            azimuth=270.0,
            tilt=8.0,
        ),
        AccessPoint(
            "Aruba",
            "AP-635",
            "Blue",
            "Floor 2",
            tags=[Tag("Location", "Building B", "tag2")],
            location_x=20.0,
            location_y=30.0,
            mounting_height=3.3,
            azimuth=0.0,
            tilt=12.0,
        ),
    ]
    antennas = [
        Antenna("ANT-2513P4M-N-R", "ant1"),
        Antenna("ANT-2513P4M-N-R", "ant1"),
        Antenna("ANT-20", "ant2"),
    ]
    radios = [
        Radio("radio1", "ap1", "2.4 GHz", 6, 20, 15.0, "802.11n"),
        Radio("radio2", "ap2", "5 GHz", 36, 80, 20.0, "802.11ac"),
        Radio("radio3", "ap3", "5 GHz", 100, 80, 18.0, "802.11ax"),
    ]
    floors = {
        "floor1": Floor("floor1", "Floor 1"),
        "floor2": Floor("floor2", "Floor 2"),
    }
    return ProjectData(
        access_points=aps,
        antennas=antennas,
        radios=radios,
        floors=floors,
        project_name="Test Project",
    )


class TestPDFExporterAvailable:
    """Test PDFExporter when WeasyPrint is available."""

    def test_export_creates_file(self, sample_project_data, tmp_path):
        """Test that export creates PDF file."""
        # Skip if WeasyPrint not installed
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()
        assert files[0].suffix == ".pdf"
        assert "Test Project" in files[0].name

    def test_format_name(self, tmp_path):
        """Test format_name property."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        assert exporter.format_name == "PDF"

    def test_pdf_file_is_valid(self, sample_project_data, tmp_path):
        """Test that generated file is a valid PDF."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        files = exporter.export(sample_project_data)

        # Read first bytes to check PDF signature
        with open(files[0], "rb") as f:
            header = f.read(5)

        assert header == b"%PDF-", "File should start with PDF signature"

    def test_pdf_file_not_empty(self, sample_project_data, tmp_path):
        """Test that PDF file is not empty."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        files = exporter.export(sample_project_data)

        # PDF should be at least a few KB
        file_size = files[0].stat().st_size
        assert file_size > 1000, "PDF file should be larger than 1KB"

    def test_export_with_empty_radios(self, sample_project_data, tmp_path):
        """Test export with no radios."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        # Remove radios from project data
        sample_project_data.radios = []

        exporter = PDFExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()

    def test_export_with_no_mounting_data(self, tmp_path):
        """Test export with APs without mounting data."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        # Create APs without mounting data
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1", tags=[]),
            AccessPoint("Aruba", "AP-635", "Blue", "Floor 2", tags=[]),
        ]
        antennas = [Antenna("ANT-20", "ant1")]
        floors = {"floor1": Floor("floor1", "Floor 1")}

        project_data = ProjectData(
            access_points=aps,
            antennas=antennas,
            radios=[],
            floors=floors,
            project_name="Minimal Project",
        )

        exporter = PDFExporter(tmp_path)
        files = exporter.export(project_data)

        assert len(files) == 1
        assert files[0].exists()

    def test_html_generation_has_required_sections(self, sample_project_data, tmp_path):
        """Test that generated HTML has all required sections."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(sample_project_data)

        # Check for key sections
        assert "<h1>Ekahau BOM Report</h1>" in html_content
        assert "Test Project" in html_content
        assert "<h3>Summary</h3>" in html_content
        assert "<h3>Distribution Statistics</h3>" in html_content
        assert "<h3>Analytics</h3>" in html_content
        assert "<h3>Access Points</h3>" in html_content

    def test_html_has_css_styles(self, sample_project_data, tmp_path):
        """Test that HTML includes CSS styles."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(sample_project_data)

        # Check for CSS
        assert "<style>" in html_content
        assert "@page" in html_content  # PDF-specific CSS
        assert "font-family" in html_content
        assert "</style>" in html_content

    def test_grouping_tables_generated(self, sample_project_data, tmp_path):
        """Test that grouping tables are generated."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(sample_project_data)

        # Check for grouping tables
        assert "<h4>By Vendor</h4>" in html_content
        assert "<h4>By Floor</h4>" in html_content
        assert "<h4>By Color</h4>" in html_content
        assert "<h4>By Model</h4>" in html_content

    def test_analytics_section_with_mounting_data(self, sample_project_data, tmp_path):
        """Test analytics section includes mounting statistics."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(sample_project_data)

        # Check for mounting analytics
        assert "Mounting Statistics" in html_content
        assert "Average Height" in html_content

    def test_analytics_section_with_radio_data(self, sample_project_data, tmp_path):
        """Test analytics section includes radio statistics."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(sample_project_data)

        # Check for radio analytics
        assert (
            "Radio Configuration" in html_content
            or "2.4 GHz" in html_content
            or "5 GHz" in html_content
        )

    def test_detailed_aps_table_includes_installation_params(self, sample_project_data, tmp_path):
        """Test detailed APs table includes installation parameters."""
        pytest.importorskip("weasyprint")

        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(sample_project_data)

        # Check for installation parameters in detailed table
        assert "Access Points Installation Details" in html_content
        assert "Height (m)" in html_content
        assert "Azimuth (°)" in html_content
        assert "Tilt (°)" in html_content

    def test_export_with_full_metadata(self, tmp_path):
        """Test export with complete project metadata."""
        from ekahau_bom.models import ProjectMetadata
        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        pytest.importorskip("weasyprint")

        metadata = ProjectMetadata(
            name="Enterprise WiFi Project",
            customer="Acme Corporation",
            location="Building A, Floor 1-3",
            responsible_person="John Doe",
            schema_version="1.0",
        )

        aps = [AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1")]
        project_data = ProjectData(
            access_points=aps, antennas=[], floors={}, project_name="Test", metadata=metadata
        )

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(project_data)

        # Check that all metadata fields are present
        assert "Project Information" in html_content
        assert "Enterprise WiFi Project" in html_content
        assert "Acme Corporation" in html_content
        assert "Building A, Floor 1-3" in html_content
        assert "John Doe" in html_content
        assert "Schema Version" in html_content

    def test_generate_grouping_table_empty_data(self, tmp_path):
        """Test _generate_grouping_table with empty data."""
        pytest.importorskip("weasyprint")
        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        result = exporter._generate_grouping_table("Test Title", {})

        # Should return empty string for empty data
        assert result == ""

    def test_export_with_wifi_standards(self, tmp_path):
        """Test export with radios containing Wi-Fi standards."""
        pytest.importorskip("weasyprint")
        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1", mine=True, floor_id="f1"),
            AccessPoint("Aruba", "AP-635", "Red", "Floor 2", mine=True, floor_id="f2"),
        ]

        radios = [
            Radio("radio1", "ap1", "5 GHz", 36, 80, 20.0, standard="802.11ax"),
            Radio("radio2", "ap1", "2.4 GHz", 6, 20, 15.0, standard="802.11ax"),
            Radio("radio3", "ap2", "5 GHz", 100, 80, 18.0, standard="802.11ac"),
            Radio("radio4", "ap2", "2.4 GHz", 11, 20, 14.0, standard="802.11n"),
        ]

        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            radios=radios,
            floors={},
            project_name="WiFi Standards Test",
        )

        exporter = PDFExporter(tmp_path)
        html_content = exporter._generate_pdf_html(project_data)

        # Check for Wi-Fi Standards section
        assert "Wi-Fi Standards" in html_content
        assert "802.11ax" in html_content or "802.11ac" in html_content

    def test_generate_detailed_aps_table_empty(self, tmp_path):
        """Test _generate_detailed_aps_table with empty access points list."""
        pytest.importorskip("weasyprint")
        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        result = exporter._generate_detailed_aps_table([])

        # Should return empty string for empty list
        assert result == ""

    def test_generate_antennas_table_empty(self, tmp_path):
        """Test _generate_antennas_table with empty antennas list."""
        pytest.importorskip("weasyprint")
        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        result = exporter._generate_antennas_table([])

        # Should return empty string for empty list
        assert result == ""

    def test_export_creates_valid_pdf_file(self, sample_project_data, tmp_path):
        """Test that export creates a valid PDF file with correct structure."""
        pytest.importorskip("weasyprint")
        from ekahau_bom.exporters.pdf_exporter import PDFExporter

        exporter = PDFExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        pdf_file = files[0]

        # Check file exists and is not empty
        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 1000  # PDF should be at least 1KB

        # Check file extension
        assert pdf_file.suffix == ".pdf"

        # Check filename contains project name
        assert "Test Project" in pdf_file.stem or "Test_Project" in pdf_file.stem


class TestPDFExporterUnavailable:
    """Test PDFExporter when WeasyPrint is not available."""

    def test_import_error_when_weasyprint_missing(self, sample_project_data, tmp_path):
        """Test that ImportError is raised when WeasyPrint is not installed."""
        # Mock the import to fail
        with patch("ekahau_bom.exporters.pdf_exporter.WEASYPRINT_AVAILABLE", False):
            from ekahau_bom.exporters.pdf_exporter import PDFExporter

            exporter = PDFExporter(tmp_path)

            with pytest.raises(ImportError, match="WeasyPrint is required"):
                exporter.export(sample_project_data)

    def test_format_name_available_without_weasyprint(self, tmp_path):
        """Test that format_name works even without WeasyPrint."""
        with patch("ekahau_bom.exporters.pdf_exporter.WEASYPRINT_AVAILABLE", False):
            from ekahau_bom.exporters.pdf_exporter import PDFExporter

            exporter = PDFExporter(tmp_path)
            assert exporter.format_name == "PDF"
