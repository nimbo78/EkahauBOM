#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for __main__ entry point."""

from __future__ import annotations


import pytest
import sys
import subprocess
from pathlib import Path


class TestMainEntry:
    """Test __main__ entry point."""

    def test_main_module_imports_correctly(self):
        """Test that __main__ module can be imported without errors."""
        # Import should work without calling main()
        import ekahau_bom.__main__ as main_module

        # Module should have the expected structure
        assert hasattr(main_module, "main")
        assert hasattr(main_module, "sys")

    def test_main_module_has_name_check(self):
        """Test that __main__ module has proper __name__ == '__main__' guard."""
        import ekahau_bom.__main__ as main_module

        # Read the file content
        with open(main_module.__file__, "r", encoding="utf-8") as f:
            content = f.read()

        # Should contain the guard (black formats with double quotes)
        assert 'if __name__ == "__main__":' in content
        assert "sys.exit(main())" in content

    def test_run_as_module_with_help(self):
        """Test running package as module with --help."""
        # Run: python -m ekahau_bom --help
        result = subprocess.run(
            [sys.executable, "-m", "ekahau_bom", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should exit successfully
        assert result.returncode == 0
        # Should show help text
        assert "usage:" in result.stdout.lower() or "ekahau" in result.stdout.lower()

    def test_run_as_module_with_version(self):
        """Test running package as module with --version."""
        result = subprocess.run(
            [sys.executable, "-m", "ekahau_bom", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should exit successfully
        assert result.returncode == 0
        # Should show version
        assert len(result.stdout.strip()) > 0 or len(result.stderr.strip()) > 0
