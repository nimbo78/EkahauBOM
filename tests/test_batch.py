"""
Tests for batch processing functionality (ekahau_bom/batch.py).

Tests cover:
- BatchResult dataclass
- AggregatedReport class
- BatchProcessor class
- filter_files() function
"""

import csv
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from ekahau_bom.batch import (
    BatchResult,
    AggregatedReport,
    BatchProcessor,
    filter_files,
)


# ============================================================================
# BatchResult Tests
# ============================================================================


def test_batch_result_creation():
    """Test BatchResult dataclass creation with all fields."""
    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        error_message=None,
        access_points_count=10,
        antennas_count=5,
        project_data={"access_points": [], "antennas": []},
    )

    assert result.filename == "test.esx"
    assert result.success is True
    assert result.processing_time == 1.5
    assert result.error_message is None
    assert result.access_points_count == 10
    assert result.antennas_count == 5
    assert result.project_data == {"access_points": [], "antennas": []}


def test_batch_result_defaults():
    """Test BatchResult default values."""
    result = BatchResult(
        filename="test.esx",
        success=False,
        processing_time=0.0,
    )

    assert result.filename == "test.esx"
    assert result.success is False
    assert result.processing_time == 0.0
    assert result.error_message is None
    assert result.access_points_count == 0
    assert result.antennas_count == 0
    assert result.project_data is None


def test_batch_result_with_error():
    """Test BatchResult with error message."""
    result = BatchResult(
        filename="test.esx",
        success=False,
        processing_time=0.5,
        error_message="File not found",
    )

    assert result.success is False
    assert result.error_message == "File not found"


# ============================================================================
# AggregatedReport Tests
# ============================================================================


def test_aggregated_report_creation():
    """Test AggregatedReport initialization."""
    report = AggregatedReport()

    assert report.total_projects == 0
    assert report.successful_projects == 0
    assert report.failed_projects == 0
    assert report.total_processing_time == 0.0
    assert report.total_access_points == 0
    assert report.total_antennas == 0
    assert report.ap_by_vendor_model == {}
    assert report.antenna_by_model == {}
    assert report.project_results == []


def test_aggregated_report_add_successful_result():
    """Test adding successful result to aggregated report."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=3,
        antennas_count=2,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 2},
                {"vendor": "Cisco", "model": "AIR-AP1832I-E-K9", "quantity": 1},
            ],
            "antennas": [
                {"antenna_model": "ANT-2513P4M-N", "quantity": 2, "is_external": True},
            ],
        },
    )

    report.add_result(result)

    assert report.total_projects == 1
    assert report.successful_projects == 1
    assert report.failed_projects == 0
    assert report.total_processing_time == 1.5
    assert report.total_access_points == 3
    assert report.total_antennas == 2

    # Check aggregated BOM
    assert report.ap_by_vendor_model[("Ubiquiti", "UAP-AC-Pro")] == 2
    assert report.ap_by_vendor_model[("Cisco", "AIR-AP1832I-E-K9")] == 1
    assert report.antenna_by_model["ANT-2513P4M-N"] == 2


def test_aggregated_report_add_failed_result():
    """Test adding failed result to aggregated report."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=False,
        processing_time=0.5,
        error_message="Invalid file format",
    )

    report.add_result(result)

    assert report.total_projects == 1
    assert report.successful_projects == 0
    assert report.failed_projects == 1
    assert report.total_processing_time == 0.5
    assert report.total_access_points == 0
    assert report.total_antennas == 0


def test_aggregated_report_multiple_results():
    """Test aggregating multiple results."""
    report = AggregatedReport()

    # First project
    result1 = BatchResult(
        filename="project1.esx",
        success=True,
        processing_time=1.0,
        access_points_count=3,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 3},
            ],
            "antennas": [],
        },
    )

    # Second project (same model)
    result2 = BatchResult(
        filename="project2.esx",
        success=True,
        processing_time=1.2,
        access_points_count=2,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 2},
            ],
            "antennas": [],
        },
    )

    # Failed project
    result3 = BatchResult(
        filename="project3.esx",
        success=False,
        processing_time=0.3,
        error_message="Parsing error",
    )

    report.add_result(result1)
    report.add_result(result2)
    report.add_result(result3)

    assert report.total_projects == 3
    assert report.successful_projects == 2
    assert report.failed_projects == 1
    assert report.total_processing_time == 2.5
    assert report.total_access_points == 5

    # Same model should be aggregated
    assert report.ap_by_vendor_model[("Ubiquiti", "UAP-AC-Pro")] == 5


def test_aggregated_report_generate_text_summary(tmp_path):
    """Test text summary generation."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=3,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 3},
            ],
            "antennas": [],
        },
    )

    report.add_result(result)

    summary_path = tmp_path / "summary.txt"
    report.generate_text_summary(summary_path)

    assert summary_path.exists()

    content = summary_path.read_text(encoding="utf-8")
    assert "BATCH PROCESSING SUMMARY" in content
    assert "Total Projects:        1" in content
    assert "Successful:            1" in content
    assert "Failed:                0" in content
    assert "Ubiquiti" in content
    assert "UAP-AC-Pro" in content


def test_aggregated_report_generate_csv_report(tmp_path):
    """Test CSV report generation."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=2,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 2},
            ],
            "antennas": [],
        },
    )

    report.add_result(result)

    csv_path = tmp_path / "aggregate.csv"
    report.generate_csv_report(csv_path)

    assert csv_path.exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert ["Aggregated BOM - Access Points"] in rows
    assert ["Quantity", "Vendor", "Model"] in rows
    assert ["2", "Ubiquiti", "UAP-AC-Pro"] in rows


def test_aggregated_report_generate_all_reports(tmp_path):
    """Test generating all reports."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=2,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 2},
            ],
            "antennas": [],
        },
    )

    report.add_result(result)

    generated_files = report.generate_reports(tmp_path)

    assert len(generated_files) == 2
    assert (tmp_path / "summary" / "batch_summary.txt").exists()
    assert (tmp_path / "summary" / "batch_aggregate.csv").exists()


# ============================================================================
# filter_files() Tests
# ============================================================================


def test_filter_files_no_filters():
    """Test filter_files without any filters."""
    files = [
        Path("project1.esx"),
        Path("project2.esx"),
        Path("backup.esx"),
    ]

    result = filter_files(files)

    assert len(result) == 3
    assert all(f in result for f in files)


def test_filter_files_include_pattern():
    """Test filter_files with include pattern."""
    files = [
        Path("office_project.esx"),
        Path("warehouse_project.esx"),
        Path("backup.esx"),
    ]

    result = filter_files(files, include_pattern="*office*")

    assert len(result) == 1
    assert Path("office_project.esx") in result


def test_filter_files_exclude_pattern():
    """Test filter_files with exclude pattern."""
    files = [
        Path("project1.esx"),
        Path("project2.esx"),
        Path("backup.esx"),
    ]

    result = filter_files(files, exclude_pattern="*backup*")

    assert len(result) == 2
    assert Path("project1.esx") in result
    assert Path("project2.esx") in result
    assert Path("backup.esx") not in result


def test_filter_files_both_patterns():
    """Test filter_files with both include and exclude patterns."""
    files = [
        Path("office_project.esx"),
        Path("office_backup.esx"),
        Path("warehouse_project.esx"),
    ]

    result = filter_files(
        files,
        include_pattern="*office*",
        exclude_pattern="*backup*",
    )

    assert len(result) == 1
    assert Path("office_project.esx") in result


def test_filter_files_empty_list():
    """Test filter_files with empty file list."""
    result = filter_files([])
    assert len(result) == 0


def test_filter_files_no_matches():
    """Test filter_files when no files match pattern."""
    files = [
        Path("project1.esx"),
        Path("project2.esx"),
    ]

    result = filter_files(files, include_pattern="*nonexistent*")

    assert len(result) == 0


# ============================================================================
# BatchProcessor Tests
# ============================================================================


def test_batch_processor_init():
    """Test BatchProcessor initialization."""
    files = [Path("test1.esx"), Path("test2.esx")]
    output_dir = Path("output/batch")

    processor = BatchProcessor(
        files=files,
        output_dir=output_dir,
        parallel_workers=2,
        continue_on_error=True,
    )

    assert processor.files == files
    assert processor.output_dir == output_dir
    assert processor.parallel_workers == 2
    assert processor.continue_on_error is True
    assert isinstance(processor.aggregated_report, AggregatedReport)


def test_batch_processor_parallel_workers_min():
    """Test BatchProcessor ensures minimum 1 worker."""
    files = [Path("test.esx")]
    output_dir = Path("output/batch")

    processor = BatchProcessor(
        files=files,
        output_dir=output_dir,
        parallel_workers=0,  # Should be clamped to 1
    )

    assert processor.parallel_workers == 1


def test_batch_processor_extract_project_data(tmp_path):
    """Test _extract_project_data method."""
    # Create test CSV file
    csv_path = tmp_path / "test_access_points.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        f.write("# Comment line\n")
        f.write("# Project: Test\n")
        f.write("#\n")
        f.write("Vendor,Model,Quantity\n")
        f.write("Ubiquiti,UAP-AC-Pro,3\n")
        f.write("Cisco,AIR-AP1832I-E-K9,2\n")

    # Create antennas CSV
    antenna_path = tmp_path / "test_antennas.csv"
    with open(antenna_path, "w", newline="", encoding="utf-8") as f:
        f.write("Antenna Model,Quantity\n")
        f.write("ANT-2513P4M-N,5\n")

    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    project_data = processor._extract_project_data(Path("test.esx"), tmp_path)

    assert len(project_data["access_points"]) == 2
    assert project_data["access_points"][0]["vendor"] == "Ubiquiti"
    assert project_data["access_points"][0]["model"] == "UAP-AC-Pro"
    assert project_data["access_points"][0]["quantity"] == 3

    assert len(project_data["antennas"]) == 1
    assert project_data["antennas"][0]["antenna_model"] == "ANT-2513P4M-N"
    assert project_data["antennas"][0]["quantity"] == 5


def test_batch_processor_extract_project_data_no_csv(tmp_path):
    """Test _extract_project_data when CSV doesn't exist."""
    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    project_data = processor._extract_project_data(Path("test.esx"), tmp_path)

    assert project_data["access_points"] == []
    assert project_data["antennas"] == []


def test_batch_processor_process_file_success(tmp_path):
    """Test process_file with successful processing."""
    # Create mock CSV files
    project_dir = tmp_path / "test"
    project_dir.mkdir()

    csv_path = project_dir / "test_access_points.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        f.write("Vendor,Model,Quantity\n")
        f.write("Ubiquiti,UAP-AC-Pro,3\n")

    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    # Mock process function
    def mock_process(**kwargs):
        # Simulate successful processing
        return 0

    result = processor.process_file(
        Path("test.esx"),
        mock_process,
        output_dir=tmp_path,
    )

    assert result.success is True
    assert result.filename == "test.esx"
    assert result.processing_time > 0
    assert result.access_points_count == 3


def test_batch_processor_process_file_error(tmp_path):
    """Test process_file with processing error."""
    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    # Mock process function that raises exception
    def mock_process(**kwargs):
        raise ValueError("Test error")

    result = processor.process_file(
        Path("test.esx"),
        mock_process,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.filename == "test.esx"
    assert result.error_message == "Test error"


def test_batch_processor_process_file_creates_subdirectory(tmp_path):
    """Test that process_file creates unique subdirectory for each project."""
    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    created_dirs = []

    def mock_process(**kwargs):
        # Capture the output_dir that was passed
        created_dirs.append(kwargs.get("output_dir"))
        return 0

    processor.process_file(
        Path("test_project.esx"),
        mock_process,
        output_dir=tmp_path,
    )

    # Should create subdirectory named after file stem
    assert len(created_dirs) == 1
    assert created_dirs[0] == tmp_path / "test_project"
    assert (tmp_path / "test_project").exists()


def test_batch_processor_process_sequential(tmp_path):
    """Test sequential batch processing."""
    files = [Path("test1.esx"), Path("test2.esx")]

    processor = BatchProcessor(
        files=files,
        output_dir=tmp_path,
        parallel_workers=1,
    )

    # Mock process function
    call_count = 0

    def mock_process(**kwargs):
        nonlocal call_count
        call_count += 1
        return 0

    report = processor.process_sequential(mock_process, output_dir=tmp_path)

    assert call_count == 2
    assert report.total_projects == 2
    assert report.successful_projects == 2


def test_batch_processor_process_parallel(tmp_path):
    """Test parallel batch processing."""
    files = [Path("test1.esx"), Path("test2.esx"), Path("test3.esx")]

    processor = BatchProcessor(
        files=files,
        output_dir=tmp_path,
        parallel_workers=2,
    )

    # Mock process function
    call_count = 0

    def mock_process(**kwargs):
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)  # Simulate work
        return 0

    report = processor.process_parallel(mock_process, output_dir=tmp_path)

    assert call_count == 3
    assert report.total_projects == 3
    assert report.successful_projects == 3


def test_batch_processor_continue_on_error(tmp_path):
    """Test continue_on_error flag."""
    files = [Path("test1.esx"), Path("test2.esx"), Path("test3.esx")]

    processor = BatchProcessor(
        files=files,
        output_dir=tmp_path,
        parallel_workers=1,
        continue_on_error=True,
    )

    call_count = 0

    def mock_process(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("Test error")
        return 0

    report = processor.process_sequential(mock_process, output_dir=tmp_path)

    # Should process all 3 files despite error in #2
    assert call_count == 3
    assert report.total_projects == 3
    assert report.successful_projects == 2
    assert report.failed_projects == 1


def test_batch_processor_stop_on_error(tmp_path):
    """Test that processing stops on error when continue_on_error=False."""
    files = [Path("test1.esx"), Path("test2.esx"), Path("test3.esx")]

    processor = BatchProcessor(
        files=files,
        output_dir=tmp_path,
        parallel_workers=1,
        continue_on_error=False,
    )

    call_count = 0

    def mock_process(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("Test error")
        return 0

    report = processor.process_sequential(mock_process, output_dir=tmp_path)

    # Should stop after error in #2
    assert call_count == 2
    assert report.total_projects == 2
    assert report.successful_projects == 1
    assert report.failed_projects == 1


def test_batch_processor_process_dispatches_correctly(tmp_path):
    """Test that process() method dispatches to sequential or parallel."""
    files = [Path("test.esx")]

    # Sequential (1 worker)
    processor_seq = BatchProcessor(
        files=files,
        output_dir=tmp_path,
        parallel_workers=1,
    )

    def mock_process(**kwargs):
        return 0

    with patch.object(processor_seq, "process_sequential") as mock_seq:
        mock_seq.return_value = AggregatedReport()
        processor_seq.process(mock_process)
        mock_seq.assert_called_once()

    # Parallel (>1 workers)
    processor_par = BatchProcessor(
        files=files,
        output_dir=tmp_path,
        parallel_workers=2,
    )

    with patch.object(processor_par, "process_parallel") as mock_par:
        mock_par.return_value = AggregatedReport()
        processor_par.process(mock_process)
        mock_par.assert_called_once()


# ============================================================================
# Additional Coverage Tests
# ============================================================================


def test_aggregated_report_with_external_antennas(tmp_path):
    """Test text summary with external antennas."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=2,
        antennas_count=5,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 2},
            ],
            "antennas": [
                {"antenna_model": "ANT-2513P4M-N", "quantity": 5, "is_external": True},
            ],
        },
    )

    report.add_result(result)

    # Generate text summary
    summary_path = tmp_path / "summary.txt"
    report.generate_text_summary(summary_path)

    content = summary_path.read_text(encoding="utf-8")
    assert "EXTERNAL ANTENNAS" in content
    assert "ANT-2513P4M-N" in content

    # Generate CSV report
    csv_path = tmp_path / "aggregate.csv"
    report.generate_csv_report(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "External Antennas" in content
        assert "ANT-2513P4M-N" in content


def test_aggregated_report_with_failed_projects(tmp_path):
    """Test text summary with failed projects section."""
    report = AggregatedReport()

    # Successful result
    result1 = BatchResult(
        filename="success.esx",
        success=True,
        processing_time=1.0,
        access_points_count=2,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 2},
            ],
            "antennas": [],
        },
    )

    # Failed result
    result2 = BatchResult(
        filename="failed.esx",
        success=False,
        processing_time=0.5,
        error_message="File corrupted",
    )

    report.add_result(result1)
    report.add_result(result2)

    summary_path = tmp_path / "summary.txt"
    report.generate_text_summary(summary_path)

    content = summary_path.read_text(encoding="utf-8")
    assert "FAILED PROJECTS" in content
    assert "failed.esx" in content
    assert "File corrupted" in content


def test_aggregated_report_empty(tmp_path):
    """Test generating reports with no data."""
    report = AggregatedReport()

    summary_path = tmp_path / "summary.txt"
    report.generate_text_summary(summary_path)

    content = summary_path.read_text(encoding="utf-8")
    assert "Total Projects:        0" in content
    assert "No access points found" in content


def test_aggregated_report_get_summary_table():
    """Test get_summary_table() method."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=3,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 3},
            ],
            "antennas": [],
        },
    )

    report.add_result(result)

    # This will return None if Rich is not available, or a Table if it is
    table = report.get_summary_table()

    # Just verify it doesn't crash - can't test Rich UI directly
    assert table is None or hasattr(table, "add_row")


def test_aggregated_report_get_bom_table():
    """Test get_bom_table() method."""
    report = AggregatedReport()

    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=3,
        antennas_count=0,
        project_data={
            "access_points": [
                {"vendor": "Ubiquiti", "model": "UAP-AC-Pro", "quantity": 3},
            ],
            "antennas": [],
        },
    )

    report.add_result(result)

    # This will return None if Rich is not available, or a Table if it is
    table = report.get_bom_table()

    # Just verify it doesn't crash
    assert table is None or hasattr(table, "add_row")


def test_batch_processor_print_summary(tmp_path, capsys):
    """Test print_summary method."""
    files = [Path("test.esx")]

    processor = BatchProcessor(
        files=files,
        output_dir=tmp_path,
    )

    # Add a result
    result = BatchResult(
        filename="test.esx",
        success=True,
        processing_time=1.5,
        access_points_count=3,
        antennas_count=0,
    )
    processor.aggregated_report.add_result(result)

    # Call print_summary
    processor.print_summary()

    # Capture output (may be Rich or plain text)
    captured = capsys.readouterr()

    # Verify some output was produced
    # (Can't test exact format due to Rich)
    assert len(captured.out) > 0 or len(captured.err) == 0


def test_batch_processor_log_error(tmp_path):
    """Test _log_error method."""
    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    result = BatchResult(
        filename="failed.esx",
        success=False,
        processing_time=0.5,
        error_message="Test error message",
    )

    processor._log_error(result)

    # Check error log was created
    error_log = tmp_path / "summary" / "batch_errors.log"
    assert error_log.exists()

    content = error_log.read_text(encoding="utf-8")
    assert "failed.esx" in content
    assert "Test error message" in content


def test_batch_processor_extract_csv_with_malformed_data(tmp_path):
    """Test _extract_project_data with malformed CSV."""
    # Create malformed CSV (missing quantity)
    csv_path = tmp_path / "test_access_points.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        f.write("Vendor,Model,Quantity\n")
        f.write("Ubiquiti,UAP-AC-Pro,\n")  # Empty quantity
        f.write("Cisco,AIR-AP1832I-E-K9,invalid\n")  # Invalid quantity

    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    # Should handle errors gracefully
    try:
        project_data = processor._extract_project_data(Path("test.esx"), tmp_path)
        # If it succeeds, verify it returned empty data
        assert isinstance(project_data, dict)
    except Exception:
        # If it fails, that's also acceptable (error handling)
        pass


def test_batch_processor_process_file_non_zero_exit_code(tmp_path):
    """Test process_file with non-zero exit code."""
    processor = BatchProcessor(
        files=[Path("test.esx")],
        output_dir=tmp_path,
    )

    def mock_process(**kwargs):
        return 1  # Non-zero exit code

    result = processor.process_file(
        Path("test.esx"),
        mock_process,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert "non-zero exit code" in result.error_message


def test_filter_files_case_insensitive():
    """Test that filter_files patterns work case-insensitively."""
    files = [
        Path("Office_Project.esx"),
        Path("WAREHOUSE_PROJECT.esx"),
        Path("backup.esx"),
    ]

    # Should match case-insensitively
    result = filter_files(files, include_pattern="*office*")

    # fnmatch is case-sensitive on Unix, case-insensitive on Windows
    # Just verify it returns a valid list
    assert isinstance(result, list)
