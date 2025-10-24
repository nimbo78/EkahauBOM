#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test that all modules can be imported without errors."""

def test_import_main():
    """Test main package import."""
    import ekahau_bom
    assert ekahau_bom.__version__ == "2.2.0"


def test_import_models():
    """Test models import."""
    from ekahau_bom.models import AccessPoint, Antenna, Floor, ProjectData
    assert AccessPoint is not None
    assert Antenna is not None
    assert Floor is not None
    assert ProjectData is not None


def test_import_parser():
    """Test parser import."""
    from ekahau_bom.parser import EkahauParser
    assert EkahauParser is not None


def test_import_processors():
    """Test processors import."""
    from ekahau_bom.processors.access_points import AccessPointProcessor
    from ekahau_bom.processors.antennas import AntennaProcessor
    assert AccessPointProcessor is not None
    assert AntennaProcessor is not None


def test_import_exporters():
    """Test exporters import."""
    from ekahau_bom.exporters.base import BaseExporter
    from ekahau_bom.exporters.csv_exporter import CSVExporter
    assert BaseExporter is not None
    assert CSVExporter is not None


def test_import_cli():
    """Test CLI import."""
    from ekahau_bom.cli import main
    assert main is not None
