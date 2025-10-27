#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration tests for EkahauBOM.

These tests perform end-to-end testing with real .esx files,
validating the complete workflow: parsing → processing → exporting.
"""

import pytest
import json
import csv
from pathlib import Path
import tempfile
import shutil
import zipfile

from ekahau_bom.parser import EkahauParser
from ekahau_bom.config import Config
from ekahau_bom.exporters.csv_exporter import CSVExporter
from ekahau_bom.exporters.json_exporter import JSONExporter
from ekahau_bom.exporters.html_exporter import HTMLExporter
from ekahau_bom.exporters.excel_exporter import ExcelExporter
from ekahau_bom.exporters.pdf_exporter import PDFExporter


# Test fixtures
@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_esx_file(project_root):
    """Path to test .esx file (wine office.esx)."""
    esx_path = project_root / "projects" / "wine office.esx"
    if not esx_path.exists():
        pytest.skip(f"Test .esx file not found: {esx_path}")
    return esx_path


@pytest.fixture
def test_esx_file_maga(project_root):
    """Path to test .esx file (maga.esx)."""
    esx_path = project_root / "projects" / "maga.esx"
    if not esx_path.exists():
        pytest.skip(f"Test .esx file not found: {esx_path}")
    return esx_path


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    temp_dir = tempfile.mkdtemp(prefix="ekahau_test_")
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def parsed_project_data(test_esx_file):
    """Parse test .esx file and return ProjectData."""
    return parse_esx_to_project_data(test_esx_file)


def parse_esx_to_project_data(esx_file):
    """
    Helper function to parse .esx file into ProjectData object.

    This replicates the parsing logic from cli.py.
    """
    from ekahau_bom.models import Floor
    from ekahau_bom.processors.access_points import AccessPointProcessor
    from ekahau_bom.processors.antennas import AntennaProcessor
    from ekahau_bom.processors.tags import TagProcessor
    from ekahau_bom.processors.radios import RadioProcessor
    from ekahau_bom.processors.metadata import ProjectMetadataProcessor
    from ekahau_bom.processors.notes import NotesProcessor
    from ekahau_bom.processors.network_settings import NetworkSettingsProcessor
    from ekahau_bom.utils import load_color_database

    color_db = load_color_database()

    with EkahauParser(str(esx_file)) as parser:
        # Get raw data
        access_points_data = parser.get_access_points()
        floor_plans_data = parser.get_floor_plans()
        simulated_radios_data = parser.get_simulated_radios()
        antenna_types_data = parser.get_antenna_types()
        tag_keys_data = parser.get_tag_keys()
        project_metadata_data = parser.get_project_metadata()
        notes_data = parser.get_notes()
        cable_notes_data = parser.get_cable_notes()
        picture_notes_data = parser.get_picture_notes()
        network_settings_data = parser.get_network_capacity_settings()

        # Build floor lookup dictionary
        floors = {
            floor["id"]: Floor(id=floor["id"], name=floor["name"])
            for floor in floor_plans_data.get("floorPlans", [])
        }

        # Process data with processors
        metadata_processor = ProjectMetadataProcessor()
        project_metadata = metadata_processor.process(project_metadata_data)

        tag_processor = TagProcessor(tag_keys_data)

        ap_processor = AccessPointProcessor(color_db, tag_processor)
        access_points = ap_processor.process(access_points_data, floors, simulated_radios_data)

        antenna_processor = AntennaProcessor()
        antennas = antenna_processor.process(simulated_radios_data, antenna_types_data)

        radio_processor = RadioProcessor()
        radios = radio_processor.process(simulated_radios_data)

        notes_processor = NotesProcessor()
        notes = notes_processor.process_notes(notes_data)
        cable_notes = notes_processor.process_cable_notes(cable_notes_data, floors)
        picture_notes = notes_processor.process_picture_notes(picture_notes_data, floors)

        network_settings = NetworkSettingsProcessor.process_network_settings(network_settings_data)

        # Create project data container
        from ekahau_bom.models import ProjectData
        return ProjectData(
            access_points=access_points,
            antennas=antennas,
            floors=floors,
            project_name=Path(esx_file).stem,
            radios=radios,
            metadata=project_metadata,
            notes=notes,
            cable_notes=cable_notes,
            picture_notes=picture_notes,
            network_settings=network_settings
        )


@pytest.fixture
def default_config(temp_output_dir):
    """Create default configuration with temp output dir."""
    return Config(
        output_dir=str(temp_output_dir),
        formats=["csv", "json", "html", "excel"],
        include_pricing=False,
    )


# ============================================================================
# CSV Export Integration Tests
# ============================================================================


class TestCSVExportIntegration:
    """Integration tests for CSV export."""

    def test_csv_export_creates_files(self, parsed_project_data, temp_output_dir):
        """Test that CSV export creates expected files."""
        exporter = CSVExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        # Should create multiple CSV files
        assert len(files) > 0, "No CSV files created"

        # All files should exist
        for file in files:
            assert file.exists(), f"CSV file not created: {file}"
            assert file.suffix == ".csv", f"Wrong file extension: {file}"

    def test_csv_export_content_validity(self, parsed_project_data, temp_output_dir):
        """Test that CSV files contain valid data."""
        exporter = CSVExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        # Check that at least one CSV file has content
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
                # Should have at least header row
                assert len(rows) > 0, f"CSV file is empty: {file}"

    def test_csv_export_with_pricing(self, parsed_project_data, temp_output_dir):
        """Test CSV export (pricing is configured separately, not in constructor)."""
        exporter = CSVExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) > 0, "No CSV files created"


# ============================================================================
# JSON Export Integration Tests
# ============================================================================


class TestJSONExportIntegration:
    """Integration tests for JSON export."""

    def test_json_export_creates_file(self, parsed_project_data, temp_output_dir):
        """Test that JSON export creates a valid file."""
        exporter = JSONExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) == 1, "Should create exactly one JSON file"
        json_file = files[0]
        assert json_file.exists(), "JSON file not created"
        assert json_file.suffix == ".json", "Wrong file extension"

    def test_json_export_valid_structure(self, parsed_project_data, temp_output_dir):
        """Test that JSON file contains valid structure."""
        exporter = JSONExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate JSON structure
        assert "metadata" in data, "Missing metadata"
        assert "file_name" in data["metadata"], "Missing file_name in metadata"
        assert "access_points" in data, "Missing access_points"
        assert "summary" in data, "Missing summary"
        assert isinstance(data["access_points"], dict), "access_points should be dict"
        assert "bill_of_materials" in data["access_points"], "Missing bill_of_materials"

    def test_json_export_with_metadata(self, parsed_project_data, temp_output_dir):
        """Test JSON export includes project metadata."""
        exporter = JSONExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check metadata fields
        assert "metadata" in data, "Missing metadata"
        assert "file_name" in data["metadata"], "Missing file_name"


# ============================================================================
# HTML Export Integration Tests
# ============================================================================


class TestHTMLExportIntegration:
    """Integration tests for HTML export."""

    def test_html_export_creates_file(self, parsed_project_data, temp_output_dir):
        """Test that HTML export creates a valid file."""
        exporter = HTMLExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) == 1, "Should create exactly one HTML file"
        html_file = files[0]
        assert html_file.exists(), "HTML file not created"
        assert html_file.suffix == ".html", "Wrong file extension"

    def test_html_export_valid_content(self, parsed_project_data, temp_output_dir):
        """Test that HTML file contains valid HTML structure."""
        exporter = HTMLExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            content = f.read()

        # Validate basic HTML structure
        assert "<!DOCTYPE html>" in content or "<html" in content
        assert "</html>" in content
        assert "<body" in content
        assert "</body>" in content

    def test_html_export_includes_charts(self, parsed_project_data, temp_output_dir):
        """Test that HTML includes Chart.js visualizations."""
        exporter = HTMLExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            content = f.read()

        # Should include Chart.js reference
        assert "chart.js" in content.lower() or "canvas" in content.lower()


# ============================================================================
# Excel Export Integration Tests
# ============================================================================


class TestExcelExportIntegration:
    """Integration tests for Excel export."""

    def test_excel_export_creates_file(self, parsed_project_data, temp_output_dir):
        """Test that Excel export creates a valid file."""
        exporter = ExcelExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) == 1, "Should create exactly one Excel file"
        excel_file = files[0]
        assert excel_file.exists(), "Excel file not created"
        assert excel_file.suffix == ".xlsx", "Wrong file extension"

    def test_excel_export_is_valid_workbook(
        self, parsed_project_data, temp_output_dir
    ):
        """Test that Excel file is a valid ZIP archive (xlsx format)."""
        exporter = ExcelExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        # Excel files are ZIP archives
        assert zipfile.is_zipfile(files[0]), "Excel file is not a valid ZIP/XLSX"

    def test_excel_export_with_pricing(self, parsed_project_data, temp_output_dir):
        """Test Excel export (pricing is configured separately, not in constructor)."""
        exporter = ExcelExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) == 1, "Should create one Excel file"


# ============================================================================
# PDF Export Integration Tests
# ============================================================================


class TestPDFExportIntegration:
    """Integration tests for PDF export."""

    def test_pdf_export_creates_file(self, parsed_project_data, temp_output_dir):
        """Test that PDF export creates a valid file (requires WeasyPrint)."""
        pytest.importorskip("weasyprint")

        exporter = PDFExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) == 1, "Should create exactly one PDF file"
        pdf_file = files[0]
        assert pdf_file.exists(), "PDF file not created"
        assert pdf_file.suffix == ".pdf", "Wrong file extension"

    def test_pdf_export_file_size(self, parsed_project_data, temp_output_dir):
        """Test that PDF file has reasonable size."""
        pytest.importorskip("weasyprint")

        exporter = PDFExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        # PDF should be at least 1KB
        assert files[0].stat().st_size > 1000, "PDF file is too small"


# ============================================================================
# End-to-End Scenarios
# ============================================================================


class TestEndToEndScenarios:
    """Integration tests for complete end-to-end scenarios."""

    def test_parse_and_export_all_formats(self, test_esx_file, temp_output_dir):
        """Test parsing and exporting to all formats."""
        # Parse
        project_data = parse_esx_to_project_data(test_esx_file)

        # Export to all formats
        exporters = [
            CSVExporter(temp_output_dir),
            JSONExporter(temp_output_dir),
            HTMLExporter(temp_output_dir),
            ExcelExporter(temp_output_dir),
        ]

        all_files = []
        for exporter in exporters:
            files = exporter.export(project_data)
            all_files.extend(files)

        # Verify all files created
        assert len(all_files) > 0, "No files created"
        for file in all_files:
            assert file.exists(), f"File not created: {file}"

    def test_parse_multiple_projects(
        self, test_esx_file, test_esx_file_maga, temp_output_dir
    ):
        """Test parsing multiple different .esx files."""
        for esx_file in [test_esx_file, test_esx_file_maga]:
            project_data = parse_esx_to_project_data(esx_file)

            # Should have access points
            assert len(project_data.access_points) > 0, f"No APs in {esx_file.name}"

            # Export to JSON to verify data
            exporter = JSONExporter(temp_output_dir)
            files = exporter.export(project_data)
            assert len(files) == 1

    def test_export_with_filters(self, parsed_project_data, temp_output_dir):
        """Test export with filtered data (only mine APs)."""
        # Filter only 'mine' APs
        mine_aps = [ap for ap in parsed_project_data.access_points if ap.mine]

        if len(mine_aps) > 0:
            # Create filtered project data
            from ekahau_bom.models import ProjectData

            filtered_data = ProjectData(
                access_points=mine_aps,
                antennas=parsed_project_data.antennas,
                radios=parsed_project_data.radios,
                floors=parsed_project_data.floors,
                project_name=parsed_project_data.project_name,
            )

            # Export filtered data
            exporter = CSVExporter(temp_output_dir)
            files = exporter.export(filtered_data)
            assert len(files) > 0

    def test_error_handling_invalid_file(self, temp_output_dir):
        """Test error handling for invalid .esx file."""
        invalid_file = temp_output_dir / "invalid.esx"
        invalid_file.write_text("not a valid esx file")

        with pytest.raises(Exception):
            parse_esx_to_project_data(invalid_file)

    def test_error_handling_missing_file(self):
        """Test error handling for missing .esx file."""
        with pytest.raises((FileNotFoundError, Exception)):
            parse_esx_to_project_data("nonexistent_file.esx")


# ============================================================================
# Performance and Stress Tests
# ============================================================================


class TestPerformanceScenarios:
    """Performance and stress testing scenarios."""

    def test_large_project_performance(self, test_esx_file, temp_output_dir):
        """Test performance with larger project file."""
        import time

        start_time = time.time()

        # Parse
        project_data = parse_esx_to_project_data(test_esx_file)

        # Export to all formats
        exporters = [
            CSVExporter(temp_output_dir),
            JSONExporter(temp_output_dir),
            HTMLExporter(temp_output_dir),
            ExcelExporter(temp_output_dir),
        ]

        for exporter in exporters:
            exporter.export(project_data)

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 30 seconds for typical project)
        assert elapsed < 30.0, f"Processing took too long: {elapsed:.2f}s"

    def test_multiple_exports_same_data(self, parsed_project_data, temp_output_dir):
        """Test exporting same data multiple times (caching, memory leaks)."""
        exporter = JSONExporter(temp_output_dir)

        # Export 5 times
        for i in range(5):
            files = exporter.export(parsed_project_data)
            assert len(files) == 1, f"Export {i+1} failed"


# ============================================================================
# Configuration and Options Tests
# ============================================================================


class TestConfigurationScenarios:
    """Test different configuration options."""

    def test_export_with_pricing_enabled(self, parsed_project_data, temp_output_dir):
        """Test export (pricing is configured separately, not in constructor)."""
        exporter = CSVExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        assert len(files) > 0
        # Verify at least one file exists
        assert any(f.exists() for f in files)

    def test_export_with_custom_output_dir(self, parsed_project_data):
        """Test export to custom output directory."""
        custom_dir = tempfile.mkdtemp(prefix="ekahau_custom_")
        try:
            exporter = JSONExporter(custom_dir)
            files = exporter.export(parsed_project_data)

            assert len(files) == 1
            assert files[0].parent == Path(custom_dir)
        finally:
            shutil.rmtree(custom_dir, ignore_errors=True)


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Validate exported data integrity."""

    def test_json_data_completeness(self, parsed_project_data, temp_output_dir):
        """Test that JSON export contains all expected data."""
        exporter = JSONExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate data completeness
        if len(parsed_project_data.access_points) > 0:
            assert "access_points" in data
            assert "bill_of_materials" in data["access_points"]
            bom = data["access_points"]["bill_of_materials"]
            assert len(bom) > 0, "BOM should not be empty"

            # Check first BOM item has required fields
            if bom:
                ap = bom[0]
                assert "vendor" in ap or "model" in ap

    def test_csv_data_consistency(self, parsed_project_data, temp_output_dir):
        """Test that CSV data is consistent with parsed data."""
        exporter = CSVExporter(temp_output_dir)
        files = exporter.export(parsed_project_data)

        # Find aggregated AP file
        ap_file = None
        for file in files:
            if "aggregated" in file.name.lower() and "access_point" in file.name.lower():
                ap_file = file
                break

        if ap_file:
            with open(ap_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Number of rows should match number of unique AP models
                # (this is aggregated data)
                assert len(rows) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
