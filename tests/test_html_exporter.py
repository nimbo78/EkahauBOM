#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for HTML exporter."""

import pytest
from pathlib import Path
from ekahau_bom.exporters.html_exporter import HTMLExporter
from ekahau_bom.models import ProjectData, AccessPoint, Antenna, Tag, Floor


@pytest.fixture
def sample_project_data():
    """Create sample project data for testing."""
    aps = [
        AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                   tags=[Tag("Location", "Building A", "tag1")]),
        AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                   tags=[Tag("Location", "Building A", "tag1")]),
        AccessPoint("Cisco", "AP-635", "Red", "Floor 2", tags=[]),
        AccessPoint("Aruba", "AP-515", "Yellow", "Floor 1", tags=[]),
        AccessPoint("Aruba", "AP-635", "Blue", "Floor 2",
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
            AccessPoint("Test&Vendor", "Model<123>", None, "Floor \"1\"",
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
