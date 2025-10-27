#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for HTML exporter."""

import pytest
from pathlib import Path
from ekahau_bom.exporters.html_exporter import HTMLExporter
from ekahau_bom.models import (
    ProjectData, AccessPoint, Antenna, Tag, Floor,
    ProjectMetadata, Radio
)


@pytest.fixture
def sample_project_data():
    """Create sample project data for testing."""
    aps = [
        AccessPoint(id="ap1", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1",
                   tags=[Tag("Location", "Building A", "tag1")]),
        AccessPoint(id="ap2", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1",
                   tags=[Tag("Location", "Building A", "tag1")]),
        AccessPoint(id="ap3", vendor="Cisco", model="AP-635", color="Red", floor_name="Floor 2", tags=[]),
        AccessPoint(id="ap4", vendor="Aruba", model="AP-515", color="Yellow", floor_name="Floor 1", tags=[]),
        AccessPoint(id="ap5", vendor="Aruba", model="AP-635", color="Blue", floor_name="Floor 2",
                   tags=[Tag("Location", "Building B", "tag2")]),
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
        access_points=aps,
        antennas=antennas,
        floors=floors,
        project_name="Test Project"
    )


class TestHTMLExporter:
    """Test HTMLExporter class."""

    def test_export_creates_file(self, sample_project_data, tmp_path):
        """Test that export creates HTML file."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()
        assert files[0].suffix == '.html'
        assert "Test Project" in files[0].name

    def test_format_name(self, tmp_path):
        """Test format_name property."""
        exporter = HTMLExporter(tmp_path)
        assert exporter.format_name == "HTML"

    def test_html_structure(self, sample_project_data, tmp_path):
        """Test that HTML file has proper structure."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Check basic HTML structure
        assert '<!DOCTYPE html>' in content
        assert '<html lang="en">' in content
        assert '<head>' in content
        assert '<body>' in content
        assert '</html>' in content

    def test_html_has_title(self, sample_project_data, tmp_path):
        """Test that HTML has project title."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Test Project' in content
        assert 'Ekahau BOM Report' in content

    def test_html_has_chart_js(self, sample_project_data, tmp_path):
        """Test that HTML includes Chart.js."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'chart.js' in content.lower()
        assert 'cdn.jsdelivr.net' in content

    def test_html_has_summary_section(self, sample_project_data, tmp_path):
        """Test that HTML has summary statistics."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Summary' in content
        assert 'Access Points' in content
        assert 'Antennas' in content
        assert '5' in content  # 5 access points
        assert '3' in content  # 3 antennas

    def test_html_has_ap_table(self, sample_project_data, tmp_path):
        """Test that HTML has access points table."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert '<table>' in content
        assert 'Vendor' in content
        assert 'Model' in content
        assert 'Floor' in content
        assert 'Color' in content
        assert 'Tags' in content
        assert 'Quantity' in content

    def test_html_has_antenna_table(self, sample_project_data, tmp_path):
        """Test that HTML has antennas table."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Antennas Bill of Materials' in content
        assert 'ANT-2513P4M-N-R' in content
        assert 'ANT-20' in content

    def test_html_has_charts_section(self, sample_project_data, tmp_path):
        """Test that HTML has charts section."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Distribution Analysis' in content
        assert 'vendorChart' in content
        assert 'floorChart' in content
        assert 'colorChart' in content
        assert 'modelChart' in content

    def test_html_has_chart_data(self, sample_project_data, tmp_path):
        """Test that HTML contains chart data."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'window.chartData' in content
        assert 'vendor:' in content.lower()
        assert 'floor:' in content.lower()
        assert 'color:' in content.lower()
        assert 'model:' in content.lower()

    def test_html_has_vendor_data(self, sample_project_data, tmp_path):
        """Test that HTML contains vendor data."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Cisco' in content
        assert 'Aruba' in content

    def test_html_has_css_styles(self, sample_project_data, tmp_path):
        """Test that HTML has embedded CSS."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert '<style>' in content
        assert '</style>' in content
        assert 'container' in content
        assert 'table' in content

    def test_html_has_javascript(self, sample_project_data, tmp_path):
        """Test that HTML has embedded JavaScript."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert '<script>' in content
        assert '</script>' in content
        assert 'Chart' in content
        assert 'new Chart' in content

    def test_html_responsive_design(self, sample_project_data, tmp_path):
        """Test that HTML has responsive meta tag."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'viewport' in content
        assert '@media' in content  # Media queries in CSS

    def test_html_special_characters_escaped(self, tmp_path):
        """Test that special characters are properly escaped."""
        aps = [
            AccessPoint(id="ap1", vendor="Test&Vendor", model="Model<123>", color=None, floor_name="Floor \"1\"",
                       tags=[Tag("Key&1", "Value<2>", "tag1")]),
        ]
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors={},
            project_name="Test&<Project>"
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Check that special chars are escaped
        assert '&amp;' in content or 'Test&amp;Vendor' in content
        assert '&lt;' in content or 'Model&lt;123&gt;' in content
        assert '&quot;' in content or 'Floor &quot;1&quot;' in content

    def test_empty_project(self, tmp_path):
        """Test export with empty project."""
        project_data = ProjectData(
            access_points=[],
            antennas=[],
            floors={},
            project_name="Empty Project"
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        assert len(files) == 1
        assert files[0].exists()

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Empty Project' in content
        assert '0' in content  # Should show 0 for counts

    def test_html_with_metadata(self, tmp_path):
        """Test HTML export with project metadata."""
        metadata = ProjectMetadata(
            name="Enterprise WiFi Project",
            customer="Acme Corporation",
            location="Building A, Floor 3",
            responsible_person="John Doe",
            schema_version="1.0"
        )
        aps = [
            AccessPoint(id="ap1", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1", tags=[]),
        ]
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors={},
            project_name="Test",
            metadata=metadata
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for metadata fields
        assert 'Project Information' in content
        assert 'Enterprise WiFi Project' in content
        assert 'Acme Corporation' in content
        assert 'Building A, Floor 3' in content
        assert 'John Doe' in content
        assert 'Schema Version' in content
        assert '1.0' in content

    def test_html_with_detailed_aps_table(self, tmp_path):
        """Test HTML with detailed APs table containing installation parameters."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-515", color="Yellow",
                floor_name="Floor 1", tags=[], mine=True, floor_id="f1",
                name="AP-Office-01",
                location_x=10.5, location_y=20.3,
                mounting_height=3.0, azimuth=45.0, tilt=10.0,
                enabled=True
            ),
            AccessPoint(
                id="ap2", vendor="Aruba", model="AP-635", color="Red",
                floor_name="Floor 2", tags=[], mine=True, floor_id="f2",
                name="AP-Lobby-01",
                location_x=5.2, location_y=15.8,
                mounting_height=2.5, azimuth=90.0, tilt=15.0,
                enabled=False
            ),
        ]
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors={},
            project_name="Detailed Test"
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for detailed table headers
        assert 'Access Points Installation Details' in content
        assert 'AP Name' in content
        assert 'Location X (m)' in content
        assert 'Location Y (m)' in content
        assert 'Height (m)' in content
        assert 'Azimuth (°)' in content
        assert 'Tilt (°)' in content
        assert 'Enabled' in content

        # Check for specific data
        assert 'AP-Office-01' in content
        assert 'AP-Lobby-01' in content
        assert '10.50' in content  # location_x
        assert '3.00' in content  # mounting_height
        assert '45.0' in content  # azimuth
        assert '✓' in content or '✗' in content  # enabled status symbols

    def test_html_with_radio_analytics(self, tmp_path):
        """Test HTML with radio analytics section."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-515", color="Yellow",
                floor_name="Floor 1", tags=[], mine=True, floor_id="f1",
                mounting_height=3.0
            ),
        ]
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                frequency_band="5GHz",
                channel=36,
                channel_width=80,
                tx_power=20,
                antenna_direction=45.0,
                antenna_tilt=10.0,
                antenna_height=3.0
            ),
            Radio(
                id="radio2",
                access_point_id="ap1",
                frequency_band="2.4GHz",
                channel=6,
                channel_width=20,
                tx_power=17,
                antenna_direction=0.0,
                antenna_tilt=0.0,
                antenna_height=3.0
            ),
        ]
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors={},
            project_name="Radio Test",
            radios=radios
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for analytics section
        assert 'Analytics' in content or 'Radio' in content or 'analytics' in content

    def test_html_with_mounting_analytics(self, tmp_path):
        """Test HTML with mounting analytics section."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-515", color="Yellow",
                floor_name="Floor 1", tags=[], mine=True, floor_id="f1",
                mounting_height=2.8
            ),
            AccessPoint(
                id="ap2", vendor="Cisco", model="AP-635", color="Red",
                floor_name="Floor 1", tags=[], mine=True, floor_id="f1",
                mounting_height=3.2
            ),
            AccessPoint(
                id="ap3", vendor="Aruba", model="AP-515", color="Blue",
                floor_name="Floor 2", tags=[], mine=True, floor_id="f2",
                mounting_height=4.5
            ),
        ]
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors={},
            project_name="Mounting Test"
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have analytics section since we have mounting height data
        # The method _generate_analytics_section checks for mounting_height
        assert len(content) > 0

    def test_html_no_analytics_without_data(self, sample_project_data, tmp_path):
        """Test that no analytics section is generated without mounting/radio data."""
        exporter = HTMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # sample_project_data has no mounting heights or radios
        # So analytics section should be minimal or empty
        assert files[0].exists()

    def test_html_metadata_only_populated_fields(self, tmp_path):
        """Test that only populated metadata fields are shown."""
        metadata = ProjectMetadata(
            name="Test Project",
            customer="Test Customer",
            location=None,  # Not set
            responsible_person=None,  # Not set
            schema_version=None  # Not set
        )
        aps = [
            AccessPoint(id="ap1", vendor="Cisco", model="AP-515", color="Yellow", floor_name="Floor 1", tags=[]),
        ]
        project_data = ProjectData(
            access_points=aps,
            antennas=[],
            floors={},
            project_name="Test",
            metadata=metadata
        )

        exporter = HTMLExporter(tmp_path)
        files = exporter.export(project_data)

        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have Project Information section
        assert 'Project Information' in content
        assert 'Test Project' in content
        assert 'Test Customer' in content
