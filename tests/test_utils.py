#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for utility functions."""

from __future__ import annotations


import logging
import pytest
from pathlib import Path
import yaml

from ekahau_bom.utils import (
    load_color_database,
    get_color_name,
    ensure_output_dir,
    setup_logging,
)
from ekahau_bom.constants import DEFAULT_COLORS


@pytest.fixture
def temp_colors_file(tmp_path):
    """Create a temporary colors YAML file."""

    def _create_colors(colors_dict):
        colors_file = tmp_path / "colors.yaml"
        with open(colors_file, "w", encoding="utf-8") as f:
            yaml.dump(colors_dict, f)
        return colors_file

    return _create_colors


@pytest.fixture
def sample_colors():
    """Sample colors dictionary."""
    return {
        "#FF0000": "Red",
        "#00FF00": "Green",
        "#0000FF": "Blue",
        "#FFE600": "Yellow",
    }


class TestLoadColorDatabase:
    """Test load_color_database function."""

    def test_load_with_valid_file(self, temp_colors_file, sample_colors):
        """Test loading colors from valid YAML file."""
        colors_file = temp_colors_file(sample_colors)
        result = load_color_database(colors_file)

        assert result == sample_colors
        assert len(result) == 4

    def test_load_with_nonexistent_file(self, tmp_path):
        """Test loading with nonexistent file returns defaults."""
        nonexistent = tmp_path / "nonexistent.yaml"
        result = load_color_database(nonexistent)

        assert result == DEFAULT_COLORS
        assert isinstance(result, dict)

    def test_load_with_none_uses_default_path(self):
        """Test loading with None parameter uses default path."""
        # Default path likely doesn't exist in test environment
        result = load_color_database(None)

        # Should fall back to DEFAULT_COLORS
        assert result == DEFAULT_COLORS

    def test_load_with_invalid_yaml_format(self, tmp_path):
        """Test loading with invalid YAML format returns defaults."""
        invalid_file = tmp_path / "invalid.yaml"
        # Write list instead of dict
        with open(invalid_file, "w") as f:
            yaml.dump(["not", "a", "dict"], f)

        result = load_color_database(invalid_file)

        assert result == DEFAULT_COLORS

    def test_load_with_malformed_yaml(self, tmp_path):
        """Test loading with malformed YAML returns defaults."""
        malformed_file = tmp_path / "malformed.yaml"
        with open(malformed_file, "w") as f:
            f.write("this is not: valid: yaml: content:")

        result = load_color_database(malformed_file)

        assert result == DEFAULT_COLORS

    def test_load_with_unicode_colors(self, temp_colors_file):
        """Test loading colors with unicode names."""
        unicode_colors = {
            "#FF0000": "Красный",  # Russian
            "#00FF00": "綠色",  # Chinese
            "#0000FF": "Azul",  # Spanish
        }
        colors_file = temp_colors_file(unicode_colors)
        result = load_color_database(colors_file)

        assert result == unicode_colors
        assert result["#FF0000"] == "Красный"

    def test_load_returns_copy_of_defaults(self, tmp_path):
        """Test that function returns a copy, not the original DEFAULT_COLORS."""
        nonexistent = tmp_path / "nonexistent.yaml"
        result = load_color_database(nonexistent)

        # Modify result
        result["#TEST"] = "Test Color"

        # DEFAULT_COLORS should not be modified
        assert "#TEST" not in DEFAULT_COLORS

    def test_load_empty_yaml_file(self, tmp_path):
        """Test loading empty YAML file."""
        empty_file = tmp_path / "empty.yaml"
        with open(empty_file, "w") as f:
            yaml.dump({}, f)

        result = load_color_database(empty_file)

        assert result == {}
        assert isinstance(result, dict)


class TestGetColorName:
    """Test get_color_name function."""

    def test_get_existing_color(self, sample_colors):
        """Test getting name of existing color."""
        result = get_color_name("#FF0000", sample_colors)
        assert result == "Red"

    def test_get_nonexistent_color_returns_hex(self, sample_colors):
        """Test that nonexistent color returns hex code."""
        result = get_color_name("#ABCDEF", sample_colors)
        assert result == "#ABCDEF"

    def test_get_color_with_empty_database(self):
        """Test getting color with empty database."""
        result = get_color_name("#FF0000", {})
        assert result == "#FF0000"

    def test_get_color_case_sensitive(self, sample_colors):
        """Test that color lookup is case-sensitive."""
        # Lowercase hex code should not match
        result = get_color_name("#ff0000", sample_colors)
        assert result == "#ff0000"  # Returns hex since not found

    def test_get_color_with_unicode_name(self):
        """Test getting color with unicode name."""
        unicode_db = {"#FF0000": "Красный"}
        result = get_color_name("#FF0000", unicode_db)
        assert result == "Красный"


class TestEnsureOutputDir:
    """Test ensure_output_dir function."""

    def test_create_new_directory(self, tmp_path):
        """Test creating new directory."""
        new_dir = tmp_path / "new_output"
        assert not new_dir.exists()

        ensure_output_dir(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_create_nested_directories(self, tmp_path):
        """Test creating nested directories."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        assert not nested_dir.exists()

        ensure_output_dir(nested_dir)

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_existing_directory_no_error(self, tmp_path):
        """Test that existing directory doesn't cause error."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # Should not raise
        ensure_output_dir(existing_dir)

        assert existing_dir.exists()
        assert existing_dir.is_dir()

    def test_path_is_file_raises_error(self, tmp_path):
        """Test that path pointing to file raises OSError."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(OSError, match="not a directory"):
            ensure_output_dir(file_path)

    def test_create_with_unicode_name(self, tmp_path):
        """Test creating directory with unicode name."""
        unicode_dir = tmp_path / "输出目录"  # Chinese
        assert not unicode_dir.exists()

        ensure_output_dir(unicode_dir)

        assert unicode_dir.exists()
        assert unicode_dir.is_dir()


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default(self):
        """Test logging setup with default parameters."""
        # Clear any existing handlers
        logging.root.handlers = []

        setup_logging()

        # Should have at least one handler (StreamHandler)
        assert len(logging.root.handlers) >= 1
        # Default level should be INFO
        assert logging.root.level == logging.INFO

    def test_setup_logging_verbose(self):
        """Test logging setup with verbose=True."""
        logging.root.handlers = []

        setup_logging(verbose=True)

        # Level should be DEBUG
        assert logging.root.level == logging.DEBUG

    def test_setup_logging_with_file(self, tmp_path):
        """Test logging setup with log file."""
        logging.root.handlers = []
        log_file = tmp_path / "test.log"

        setup_logging(log_file=log_file)

        # Should have 2 handlers: StreamHandler and FileHandler
        assert len(logging.root.handlers) == 2
        # Log file should be created
        assert log_file.exists()

    def test_setup_logging_verbose_with_file(self, tmp_path):
        """Test logging setup with both verbose and log file."""
        logging.root.handlers = []
        log_file = tmp_path / "verbose.log"

        setup_logging(verbose=True, log_file=log_file)

        assert logging.root.level == logging.DEBUG
        assert len(logging.root.handlers) == 2
        assert log_file.exists()

    def test_logging_actually_works(self, tmp_path):
        """Test that logging actually writes to file."""
        logging.root.handlers = []
        log_file = tmp_path / "output.log"

        setup_logging(log_file=log_file)

        # Write a log message
        test_logger = logging.getLogger("test")
        test_logger.info("Test message")

        # Check that message was written to file
        log_content = log_file.read_text()
        assert "Test message" in log_content
        assert "INFO" in log_content

    def test_logging_format(self, tmp_path):
        """Test that logging format includes required fields."""
        logging.root.handlers = []
        log_file = tmp_path / "format.log"

        setup_logging(log_file=log_file)

        test_logger = logging.getLogger("test.module")
        test_logger.warning("Warning message")

        log_content = log_file.read_text()
        # Should include timestamp, logger name, level, and message
        assert "test.module" in log_content
        assert "WARNING" in log_content
        assert "Warning message" in log_content
        # Should have timestamp (rough check for date format)
        assert "-" in log_content  # Date separator


class TestIntegration:
    """Integration tests for utility functions."""

    def test_load_and_get_color(self, temp_colors_file, sample_colors):
        """Test loading colors and getting color name."""
        colors_file = temp_colors_file(sample_colors)
        color_db = load_color_database(colors_file)

        red_name = get_color_name("#FF0000", color_db)
        assert red_name == "Red"

        unknown_name = get_color_name("#123456", color_db)
        assert unknown_name == "#123456"

    def test_create_dir_and_verify(self, tmp_path):
        """Test creating directory and verifying it exists."""
        output_dir = tmp_path / "integration_test"

        ensure_output_dir(output_dir)

        assert output_dir.exists()
        assert output_dir.is_dir()

        # Should be able to create files in it
        test_file = output_dir / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()
