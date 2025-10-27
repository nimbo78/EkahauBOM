#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for base exporter module."""

import pytest
from pathlib import Path
from ekahau_bom.exporters.base import BaseExporter
from ekahau_bom.models import ProjectData


class TestBaseExporter:
    """Test BaseExporter class."""

    class ConcreteExporter(BaseExporter):
        """Concrete implementation of BaseExporter for testing."""

        def export(self, project_data: ProjectData) -> list[Path]:
            """Concrete implementation of export."""
            return [self.output_dir / "test.txt"]

        @property
        def format_name(self) -> str:
            """Concrete implementation of format_name."""
            return "Test Format"

    def test_init(self, tmp_path):
        """Test initialization."""
        exporter = self.ConcreteExporter(tmp_path)
        assert exporter.output_dir == tmp_path

    def test_sanitize_filename_valid(self, tmp_path):
        """Test sanitizing valid filename."""
        exporter = self.ConcreteExporter(tmp_path)
        assert exporter._sanitize_filename("test_file") == "test_file"
        assert exporter._sanitize_filename("my-project") == "my-project"
        assert exporter._sanitize_filename("project123") == "project123"

    def test_sanitize_filename_invalid_characters(self, tmp_path):
        """Test sanitizing filename with invalid characters."""
        exporter = self.ConcreteExporter(tmp_path)
        # Windows reserved characters: < > : " / \ | ? *
        assert exporter._sanitize_filename("test<file") == "test_file"
        assert exporter._sanitize_filename("test>file") == "test_file"
        assert exporter._sanitize_filename("test:file") == "test_file"
        assert exporter._sanitize_filename('test"file') == "test_file"
        assert exporter._sanitize_filename("test/file") == "test_file"
        assert exporter._sanitize_filename("test\\file") == "test_file"
        assert exporter._sanitize_filename("test|file") == "test_file"
        assert exporter._sanitize_filename("test?file") == "test_file"
        assert exporter._sanitize_filename("test*file") == "test_file"

    def test_sanitize_filename_dots_and_spaces(self, tmp_path):
        """Test sanitizing filename with leading/trailing dots and spaces."""
        exporter = self.ConcreteExporter(tmp_path)
        assert exporter._sanitize_filename("  test_file  ") == "test_file"
        assert exporter._sanitize_filename("..test_file..") == "test_file"
        assert exporter._sanitize_filename(". test_file .") == "test_file"

    def test_sanitize_filename_empty_after_sanitization(self, tmp_path):
        """Test sanitizing filename that becomes empty after sanitization."""
        exporter = self.ConcreteExporter(tmp_path)
        # Only dots, spaces, and empty string become "unnamed"
        assert exporter._sanitize_filename("...") == "unnamed"
        assert exporter._sanitize_filename("   ") == "unnamed"
        assert exporter._sanitize_filename("") == "unnamed"
        assert exporter._sanitize_filename(". . .") == "unnamed"
        assert exporter._sanitize_filename(" . ") == "unnamed"

    def test_get_output_filename(self, tmp_path):
        """Test getting output filename."""
        exporter = self.ConcreteExporter(tmp_path)
        result = exporter._get_output_filename("My Project", "access_points")
        assert result == tmp_path / "My Project_access_points"

    def test_get_output_filename_with_invalid_chars(self, tmp_path):
        """Test getting output filename with invalid characters in project name."""
        exporter = self.ConcreteExporter(tmp_path)
        result = exporter._get_output_filename("My<Project>", "access_points")
        assert result == tmp_path / "My_Project__access_points"

    def test_log_export_success(self, tmp_path, caplog):
        """Test logging export success."""
        import logging

        caplog.set_level(logging.INFO)

        exporter = self.ConcreteExporter(tmp_path)
        files = [tmp_path / "file1.csv", tmp_path / "file2.csv"]

        exporter.log_export_success(files)

        # Check that log messages were created
        assert "Test Format export completed: 2 file(s) created" in caplog.text

    def test_concrete_export(self, tmp_path):
        """Test concrete export implementation."""
        exporter = self.ConcreteExporter(tmp_path)
        project_data = ProjectData(access_points=[], antennas=[], floors={}, project_name="Test")

        result = exporter.export(project_data)
        assert len(result) == 1
        assert result[0] == tmp_path / "test.txt"

    def test_format_name_property(self, tmp_path):
        """Test format_name property."""
        exporter = self.ConcreteExporter(tmp_path)
        assert exporter.format_name == "Test Format"

    def test_abstract_methods_must_be_implemented(self, tmp_path):
        """Test that abstract methods must be implemented."""
        # Try to instantiate BaseExporter directly - should fail
        with pytest.raises(TypeError):
            BaseExporter(tmp_path)

    def test_incomplete_implementation_fails(self, tmp_path):
        """Test that incomplete implementation cannot be instantiated."""

        # Class with only export implemented
        class IncompleteExporter(BaseExporter):
            def export(self, project_data: ProjectData) -> list[Path]:
                return []

            # Missing format_name property

        with pytest.raises(TypeError):
            IncompleteExporter(tmp_path)

    def test_abstract_method_pass_statements(self, tmp_path):
        """Test that abstract method pass statements are covered."""
        # Call the abstract methods directly through super() to cover the pass statements
        exporter = self.ConcreteExporter(tmp_path)
        project_data = ProjectData(access_points=[], antennas=[], floors={}, project_name="Test")

        # Call parent's export method (which just has pass)
        result = BaseExporter.export(exporter, project_data)
        assert result is None  # pass returns None

        # Call parent's format_name property (which just has pass)
        # For abstract properties, we need to call the fget directly
        result = BaseExporter.format_name.fget(exporter)
        assert result is None  # pass returns None
