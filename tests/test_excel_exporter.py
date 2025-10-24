#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for Excel exporter."""

import pytest
from pathlib import Path
from ekahau_bom.exporters.excel_exporter import ExcelExporter
from ekahau_bom.models import ProjectData, AccessPoint, Antenna, Tag, Floor


@pytest.fixture
def sample_project_data():
    """Create sample project data."""
    aps = [
        AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                   tags=[Tag("Location", "Building A", "1")]),
        AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                   tags=[Tag("Location", "Building A", "1")]),
        AccessPoint("Cisco", "AP-635", "Red", "Floor 2", tags=[]),
        AccessPoint("Aruba", "AP-515", "Yellow", "Floor 1", tags=[]),
        AccessPoint("Aruba", "AP-635", "Blue", "Floor 2",
                   tags=[Tag("Location", "Building B", "1")]),
    ]
    antennas = [
        Antenna("ANT-2513P4M-N-R", "ant1"),
        Antenna("ANT-2513P4M-N-R", "ant1"),
        Antenna("ANT-20", "ant2"),
    ]
    floors = {
        "f1": Floor("f1", "Floor 1"),
        "f2": Floor("f2", "Floor 2")
    }
    return ProjectData(
        project_name="Test Project",
        access_points=aps,
        antennas=antennas,
        floors=floors
    )


class TestExcelExporter:
    """Test ExcelExporter class."""

    def test_export_creates_file(self, sample_project_data, tmp_path):
        """Test that export creates Excel file."""
        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()
        assert files[0].suffix == '.xlsx'
        assert "Test Project" in files[0].name

    def test_export_has_required_sheets(self, sample_project_data, tmp_path):
        """Test that Excel file has all required sheets."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])
        sheet_names = wb.sheetnames

        assert "Summary" in sheet_names
        assert "Access Points" in sheet_names
        assert "Antennas" in sheet_names
        assert "By Floor" in sheet_names
        assert "By Color" in sheet_names
        assert "By Vendor" in sheet_names
        assert "By Model" in sheet_names

    def test_summary_sheet_content(self, sample_project_data, tmp_path):
        """Test Summary sheet has correct data."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])
        ws = wb["Summary"]

        # Check title
        assert ws['A1'].value == "Project Summary"

        # Check project name
        assert ws['A3'].value == "Project Name:"
        assert ws['B3'].value == "Test Project"

        # Check counts
        assert ws['A4'].value == "Total Access Points:"
        assert ws['B4'].value == 5

        assert ws['A5'].value == "Total Antennas:"
        assert ws['B5'].value == 3

    def test_access_points_sheet_content(self, sample_project_data, tmp_path):
        """Test Access Points sheet has correct data."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])
        ws = wb["Access Points"]

        # Check headers
        headers = [cell.value for cell in ws[1]]
        assert "Vendor" in headers
        assert "Model" in headers
        assert "Floor" in headers
        assert "Color" in headers
        assert "Tags" in headers
        assert "Quantity" in headers

        # Check we have data rows (header + data)
        assert ws.max_row > 1

    def test_antennas_sheet_content(self, sample_project_data, tmp_path):
        """Test Antennas sheet has correct data."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])
        ws = wb["Antennas"]

        # Check headers
        headers = [cell.value for cell in ws[1]]
        assert "Antenna Model" in headers
        assert "Quantity" in headers

        # Check we have data rows
        assert ws.max_row > 1

    def test_grouped_sheets_have_charts(self, sample_project_data, tmp_path):
        """Test grouped sheets have charts."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])

        # Check that grouped sheets have charts
        for sheet_name in ["By Floor", "By Color", "By Vendor", "By Model"]:
            ws = wb[sheet_name]
            # openpyxl stores charts in _charts attribute
            assert len(ws._charts) > 0, f"{sheet_name} should have at least one chart"

    def test_format_name(self):
        """Test format name property."""
        exporter = ExcelExporter(Path("."))
        assert exporter.format_name == "Excel"

    def test_empty_project_data(self, tmp_path):
        """Test export with empty project data."""
        empty_data = ProjectData(
            project_name="Empty Project",
            access_points=[],
            antennas=[],
            floors={}
        )
        exporter = ExcelExporter(tmp_path)
        files = exporter.export(empty_data)

        assert len(files) == 1
        assert files[0].exists()

    def test_tags_in_access_points_export(self, sample_project_data, tmp_path):
        """Test that tags are correctly exported in Access Points sheet."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])
        ws = wb["Access Points"]

        # Find Tags column
        headers = [cell.value for cell in ws[1]]
        tags_col_idx = headers.index("Tags") + 1

        # Check that some rows have tags
        has_tags = False
        for row_idx in range(2, ws.max_row + 1):
            tags_cell = ws.cell(row=row_idx, column=tags_col_idx)
            if tags_cell.value and "Location" in tags_cell.value:
                has_tags = True
                # Verify format is "Key:Value"
                assert ":" in tags_cell.value
                break

        assert has_tags, "At least one AP should have tags exported"
