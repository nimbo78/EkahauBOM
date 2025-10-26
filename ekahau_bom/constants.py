#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Constants and configuration for EkahauBOM."""

from pathlib import Path

# Default color database
# This will be loaded from colors.yaml if available
DEFAULT_COLORS = {
    "#FFE600": "Yellow",
    "#FF8500": "Orange",
    "#FF0000": "Red",
    "#FF00FF": "Pink",
    "#C297FF": "Violet",
    "#0068FF": "Blue",
    "#6D6D6D": "Gray",
    "#00FF00": "Green",
    "#C97700": "Brown",
    "#00FFCE": "Mint"
}

# Paths
DEFAULT_OUTPUT_DIR = Path("output")
CONFIG_DIR = Path("config")
COLORS_CONFIG_FILE = CONFIG_DIR / "colors.yaml"

# Ekahau .esx archive file names
ESX_ACCESS_POINTS_FILE = "accessPoints.json"
ESX_FLOOR_PLANS_FILE = "floorPlans.json"
ESX_SIMULATED_RADIOS_FILE = "simulatedRadios.json"
ESX_ANTENNA_TYPES_FILE = "antennaTypes.json"
ESX_TAG_KEYS_FILE = "tagKeys.json"
ESX_PROJECT_FILE = "project.json"
ESX_PROJECT_METADATA_FILE = "projectMetadata.json"  # Legacy/alternative name
ESX_MEASURED_AREAS_FILE = "measuredAreas.json"
ESX_NOTES_FILE = "notes.json"
ESX_CABLE_NOTES_FILE = "cableNotes.json"
ESX_PICTURE_NOTES_FILE = "pictureNotes.json"
ESX_ACCESS_POINT_MODELS_FILE = "accessPointModels.json"

# Export settings
CSV_DIALECT = "excel"
CSV_QUOTING_MODE = "QUOTE_ALL"
