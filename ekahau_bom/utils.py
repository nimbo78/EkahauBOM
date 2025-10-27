#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility functions for EkahauBOM."""

from __future__ import annotations


import logging
from pathlib import Path
from typing import Optional
import yaml

from .constants import DEFAULT_COLORS, COLORS_CONFIG_FILE

logger = logging.getLogger(__name__)


def load_color_database(config_file: Optional[Path] = None) -> dict[str, str]:
    """Load color database from YAML configuration file.

    Args:
        config_file: Path to colors configuration file.
                    If None, uses default path.

    Returns:
        Dictionary mapping hex color codes to color names.
        Falls back to DEFAULT_COLORS if file not found.
    """
    if config_file is None:
        config_file = COLORS_CONFIG_FILE

    if not config_file.exists():
        logger.info(f"Color config file not found at {config_file}, using defaults")
        return DEFAULT_COLORS.copy()

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            colors = yaml.safe_load(f)
            if not isinstance(colors, dict):
                logger.warning(
                    f"Invalid color config format in {config_file}, using defaults"
                )
                return DEFAULT_COLORS.copy()
            logger.info(f"Loaded {len(colors)} colors from {config_file}")
            return colors
    except Exception as e:
        logger.error(f"Error loading color config from {config_file}: {e}")
        return DEFAULT_COLORS.copy()


def get_color_name(hex_code: str, color_db: dict[str, str]) -> str:
    """Get human-readable color name from hex code.

    Args:
        hex_code: Hex color code (e.g., "#FFE600")
        color_db: Color database dictionary

    Returns:
        Color name if found, otherwise the hex code itself
    """
    return color_db.get(hex_code, hex_code)


def ensure_output_dir(output_dir: Path) -> None:
    """Ensure output directory exists, create if necessary.

    Args:
        output_dir: Path to output directory

    Raises:
        OSError: If directory cannot be created
    """
    if not output_dir.exists():
        logger.info(f"Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
    elif not output_dir.is_dir():
        raise OSError(f"Output path exists but is not a directory: {output_dir}")


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """Configure logging for the application.

    Args:
        verbose: If True, set log level to DEBUG, otherwise INFO
        log_file: Optional path to log file
    """
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
