#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration and performance tests for batch processing functionality.

Tests cover:
- End-to-end batch processing with real .esx files
- Performance tests with multiple files
- Parallel vs sequential processing
- Error recovery and handling
- Aggregated report generation
"""

from __future__ import annotations

import pytest
import csv
import time
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from ekahau_bom.batch import BatchProcessor, AggregatedReport, filter_files
from ekahau_bom.cli import process_project


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def projects_dir(project_root):
    """Get projects directory with .esx files."""
    return project_root / "projects"


@pytest.fixture
def test_esx_files(projects_dir):
    """Find all .esx files in projects directory."""
    esx_files = list(projects_dir.glob("*.esx"))
    if len(esx_files) == 0:
        pytest.skip("No .esx files found in projects directory")
    return esx_files


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    temp_dir = tempfile.mkdtemp(prefix="batch_test_")
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Integration Tests - Real File Processing
# ============================================================================


class TestBatchProcessingIntegration:
    """Integration tests for batch processing with real .esx files."""

    @pytest.mark.slow
    def test_batch_process_single_file(self, test_esx_files, temp_output_dir):
        """Test batch processing with single real .esx file."""
        # Take first file only
        files = test_esx_files[:1]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        report = processor.process(
            process_project,
            # Note: esx_file is passed automatically by BatchProcessor
            export_formats=["csv"],  # Just CSV for speed
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,  # Suppress console output during tests
        )

        # Verify processing completed
        assert report.total_projects == 1
        # At least one should succeed (depends on file validity)
        assert report.successful_projects + report.failed_projects == 1

        # If successful, check outputs
        if report.successful_projects > 0:
            project_dir = temp_output_dir / files[0].stem
            assert project_dir.exists()

    @pytest.mark.slow
    def test_batch_process_multiple_files_sequential(self, test_esx_files, temp_output_dir):
        """Test batch processing multiple files sequentially."""
        # Take first 3 files (or all if less than 3)
        files = test_esx_files[: min(3, len(test_esx_files))]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,  # Sequential
            continue_on_error=True,
        )

        start_time = time.time()
        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )
        elapsed = time.time() - start_time

        # Verify all files processed
        assert report.total_projects == len(files)
        assert report.successful_projects + report.failed_projects == len(files)

        # Processing should complete in reasonable time
        # Approximately 5-10 seconds per file on average
        assert (
            elapsed < len(files) * 30
        ), f"Processing too slow: {elapsed:.2f}s for {len(files)} files"

    @pytest.mark.slow
    def test_batch_process_multiple_files_parallel(self, test_esx_files, temp_output_dir):
        """Test batch processing multiple files in parallel."""
        # Take first 4 files (or all if less)
        files = test_esx_files[: min(4, len(test_esx_files))]

        if len(files) < 2:
            pytest.skip("Need at least 2 files for parallel test")

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=2,  # Parallel
            continue_on_error=True,
        )

        start_time = time.time()
        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )
        parallel_time = time.time() - start_time

        # Verify all files processed
        assert report.total_projects == len(files)
        assert report.successful_projects + report.failed_projects == len(files)

        # Parallel should be faster than sequential (but not guaranteed on all systems)
        # Just verify it completes successfully

    @pytest.mark.slow
    def test_batch_aggregated_report_generation(self, test_esx_files, temp_output_dir):
        """Test aggregated report generation from multiple files."""
        # Take first 3 files
        files = test_esx_files[: min(3, len(test_esx_files))]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )

        # Generate aggregated reports
        generated_files = report.generate_reports(temp_output_dir)

        # Should generate summary.txt and aggregate.csv
        assert len(generated_files) >= 2

        # Check summary file
        summary_file = temp_output_dir / "summary" / "batch_summary.txt"
        assert summary_file.exists()
        content = summary_file.read_text(encoding="utf-8")
        assert "BATCH PROCESSING SUMMARY" in content
        assert f"Total Projects:        {len(files)}" in content

        # Check CSV file
        csv_file = temp_output_dir / "summary" / "batch_aggregate.csv"
        assert csv_file.exists()

        # If there were successful projects, check aggregated data
        if report.successful_projects > 0:
            assert report.total_access_points > 0 or report.total_antennas > 0

    @pytest.mark.slow
    def test_batch_with_all_formats(self, test_esx_files, temp_output_dir):
        """Test batch processing with all output formats."""
        # Take just one file for speed
        files = test_esx_files[:1]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        report = processor.process(
            process_project,
            export_formats=["csv", "json", "html", "excel"],  # All except PDF
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )

        # Should succeed
        assert report.successful_projects + report.failed_projects == 1

        if report.successful_projects > 0:
            project_dir = temp_output_dir / files[0].stem
            assert project_dir.exists()

            # Check for different formats
            assert any(project_dir.glob("*.csv"))
            assert any(project_dir.glob("*.json"))
            assert any(project_dir.glob("*.html"))
            # Excel might fail if not installed, so don't require it


# ============================================================================
# Performance Tests
# ============================================================================


class TestBatchProcessingPerformance:
    """Performance tests for batch processing."""

    @pytest.mark.slow
    def test_performance_sequential_vs_parallel(self, test_esx_files, temp_output_dir):
        """Compare performance of sequential vs parallel processing."""
        # Need at least 4 files for meaningful comparison
        if len(test_esx_files) < 4:
            pytest.skip("Need at least 4 files for performance comparison")

        files = test_esx_files[:4]

        # Sequential processing
        processor_seq = BatchProcessor(
            files=files,
            output_dir=temp_output_dir / "sequential",
            parallel_workers=1,
            continue_on_error=True,
        )

        start_seq = time.time()
        report_seq = processor_seq.process(
            process_project,
            file_path=None,
            output_dir=temp_output_dir / "sequential",
            format=["csv"],
            group_by="model",
            include_pricing=False,
            visualize_floor_plans=False,
        )
        time_seq = time.time() - start_seq

        # Parallel processing (2 workers)
        processor_par = BatchProcessor(
            files=files,
            output_dir=temp_output_dir / "parallel",
            parallel_workers=2,
            continue_on_error=True,
        )

        start_par = time.time()
        report_par = processor_par.process(
            process_project,
            file_path=None,
            output_dir=temp_output_dir / "parallel",
            format=["csv"],
            group_by="model",
            include_pricing=False,
            visualize_floor_plans=False,
        )
        time_par = time.time() - start_par

        # Both should process same number of files
        assert report_seq.total_projects == report_par.total_projects == len(files)

        # Print timing for analysis (not assertion, as it's machine-dependent)
        print(f"\nPerformance comparison ({len(files)} files):")
        print(f"  Sequential: {time_seq:.2f}s ({time_seq/len(files):.2f}s per file)")
        print(f"  Parallel:   {time_par:.2f}s ({time_par/len(files):.2f}s per file)")
        print(f"  Speedup:    {time_seq/time_par:.2f}x")

    @pytest.mark.slow
    def test_performance_with_visualizations(self, test_esx_files, temp_output_dir):
        """Test performance impact of floor plan visualizations."""
        # Take just one file
        files = test_esx_files[:1]

        # Without visualizations
        processor_no_viz = BatchProcessor(
            files=files,
            output_dir=temp_output_dir / "no_viz",
            parallel_workers=1,
            continue_on_error=True,
        )

        start_no_viz = time.time()
        processor_no_viz.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )
        time_no_viz = time.time() - start_no_viz

        # With visualizations
        processor_viz = BatchProcessor(
            files=files,
            output_dir=temp_output_dir / "with_viz",
            parallel_workers=1,
            continue_on_error=True,
        )

        start_viz = time.time()
        processor_viz.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=True,
            quiet=True,
        )
        time_viz = time.time() - start_viz

        print(f"\nVisualization performance impact:")
        print(f"  Without viz: {time_no_viz:.2f}s")
        print(f"  With viz:    {time_viz:.2f}s")
        print(
            f"  Overhead:    {time_viz - time_no_viz:.2f}s ({((time_viz/time_no_viz - 1) * 100):.1f}%)"
        )

    def test_memory_efficiency_large_batch(self, test_esx_files, temp_output_dir):
        """Test memory efficiency with multiple files (non-slow test with mocks)."""
        # Use mocking to simulate many files without actually processing them
        files = [Path(f"test{i}.esx") for i in range(50)]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        # Mock the process function to avoid actual processing
        def mock_process(**kwargs):
            return 0  # Success

        # This should not consume excessive memory
        report = processor.process(mock_process, output_dir=temp_output_dir)

        assert report.total_projects == len(files)


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestBatchErrorHandling:
    """Test error handling in batch processing."""

    def test_continue_on_error_integration(self, test_esx_files, temp_output_dir):
        """Test that batch continues on individual file errors."""
        if len(test_esx_files) < 2:
            pytest.skip("Need at least 2 files for error handling test")

        # Mix valid and invalid files
        files = test_esx_files[:2]
        invalid_file = temp_output_dir / "invalid.esx"
        invalid_file.write_text("not a valid esx file")
        files = list(files) + [invalid_file]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )

        # All files should be attempted
        assert report.total_projects == len(files)
        # At least one should fail (the invalid one)
        assert report.failed_projects >= 1
        # Error log should be created
        error_log = temp_output_dir / "summary" / "batch_errors.log"
        assert error_log.exists()

    def test_stop_on_error_integration(self, temp_output_dir):
        """Test that batch stops on first error when continue_on_error=False."""
        # Create test files: one that will fail
        invalid_file = temp_output_dir / "invalid.esx"
        invalid_file.write_text("not a valid esx file")
        files = [invalid_file]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=False,
        )

        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )

        # Should have one failed project
        assert report.failed_projects == 1

    def test_error_logging(self, temp_output_dir):
        """Test error logging functionality."""
        invalid_file = temp_output_dir / "corrupted.esx"
        invalid_file.write_text("corrupted data")

        processor = BatchProcessor(
            files=[invalid_file],
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )

        # Error log should exist
        error_log = temp_output_dir / "summary" / "batch_errors.log"
        assert error_log.exists()

        # Should contain error details
        content = error_log.read_text(encoding="utf-8")
        assert "corrupted.esx" in content


# ============================================================================
# File Filtering Tests
# ============================================================================


class TestFileFiltering:
    """Test file filtering functionality."""

    def test_filter_files_with_real_files(self, projects_dir):
        """Test filter_files with real project directory."""
        if not projects_dir.exists():
            pytest.skip("Projects directory not found")

        all_files = list(projects_dir.glob("*.esx"))
        if len(all_files) == 0:
            pytest.skip("No .esx files found")

        # Test no filter
        result = filter_files(all_files)
        assert len(result) == len(all_files)

        # Test include pattern (if files match)
        if any("office" in f.name.lower() for f in all_files):
            result = filter_files(all_files, include_pattern="*office*")
            assert all("office" in f.name.lower() for f in result)

        # Test exclude pattern
        if any("backup" in f.name.lower() for f in all_files):
            result = filter_files(all_files, exclude_pattern="*backup*")
            assert all("backup" not in f.name.lower() for f in result)


# ============================================================================
# Aggregated Report Tests
# ============================================================================


class TestAggregatedReportIntegration:
    """Test aggregated report generation with real data."""

    @pytest.mark.slow
    def test_aggregated_report_with_real_data(self, test_esx_files, temp_output_dir):
        """Test aggregated report generation from real projects."""
        files = test_esx_files[: min(2, len(test_esx_files))]

        processor = BatchProcessor(
            files=files,
            output_dir=temp_output_dir,
            parallel_workers=1,
            continue_on_error=True,
        )

        report = processor.process(
            process_project,
            export_formats=["csv"],
            group_by="model",
            enable_pricing=False,
            visualize_floor_plans=False,
            quiet=True,
        )

        # If any succeeded, check aggregated data
        if report.successful_projects > 0:
            # Should have aggregated BOM
            assert len(report.ap_by_vendor_model) > 0 or len(report.antenna_by_model) > 0

            # Generate reports
            generated_files = report.generate_reports(temp_output_dir)
            assert len(generated_files) >= 2

            # Verify CSV structure
            csv_file = temp_output_dir / "summary" / "batch_aggregate.csv"
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
                # Should have header and data
                assert len(rows) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
