#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Command-line interface for EkahauBOM."""

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .parser import EkahauParser
from .processors.access_points import AccessPointProcessor
from .processors.antennas import AntennaProcessor
from .exporters.csv_exporter import CSVExporter
from .models import Floor, ProjectData
from .constants import DEFAULT_OUTPUT_DIR
from .utils import load_color_database, ensure_output_dir, setup_logging

logger = logging.getLogger(__name__)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='EkahauBOM',
        description='Generate Bill of Materials (BOM) from Ekahau AI project files',
        epilog='Example: python EkahauBOM.py project.esx --output-dir reports/'
    )

    parser.add_argument(
        'esx_file',
        type=Path,
        help='Path to Ekahau .esx project file'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for generated files (default: {DEFAULT_OUTPUT_DIR})'
    )

    parser.add_argument(
        '--colors-config',
        type=Path,
        help='Path to custom colors configuration file (YAML)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    parser.add_argument(
        '--log-file',
        type=Path,
        help='Path to log file (optional)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    return parser


def process_project(
    esx_file: Path,
    output_dir: Path,
    colors_config: Path | None = None
) -> int:
    """Process Ekahau project and generate BOM.

    Args:
        esx_file: Path to .esx file
        output_dir: Output directory for exports
        colors_config: Optional path to colors configuration

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Ensure output directory exists
        ensure_output_dir(output_dir)

        # Load color database
        color_db = load_color_database(colors_config)

        # Parse .esx file
        logger.info(f"Processing project: {esx_file}")

        with EkahauParser(esx_file) as parser:
            # Get raw data
            access_points_data = parser.get_access_points()
            floor_plans_data = parser.get_floor_plans()
            simulated_radios_data = parser.get_simulated_radios()
            antenna_types_data = parser.get_antenna_types()

            # Build floor lookup dictionary (optimized for O(1) access)
            floors = {
                floor["id"]: Floor(id=floor["id"], name=floor["name"])
                for floor in floor_plans_data.get("floorPlans", [])
            }
            logger.info(f"Found {len(floors)} floors")

            # Process access points
            ap_processor = AccessPointProcessor(color_db)
            access_points = ap_processor.process(access_points_data, floors)

            # Process antennas
            antenna_processor = AntennaProcessor()
            antennas = antenna_processor.process(simulated_radios_data, antenna_types_data)

            # Create project data container
            project_data = ProjectData(
                access_points=access_points,
                antennas=antennas,
                floors=floors,
                project_name=esx_file.stem
            )

            # Export to CSV
            exporter = CSVExporter(output_dir)
            exported_files = exporter.export(project_data)

            # Summary
            logger.info("=" * 60)
            logger.info("Processing completed successfully!")
            logger.info(f"Access Points: {len(access_points)}")
            logger.info(f"Antennas: {len(antennas)}")
            logger.info(f"Floors: {len(floors)}")
            logger.info(f"Generated files: {len(exported_files)}")
            for file in exported_files:
                logger.info(f"  - {file}")
            logger.info("=" * 60)

            return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except KeyError as e:
        logger.error(f"Missing required data in .esx file: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


def main(args: list[str] | None = None) -> int:
    """Main entry point for CLI.

    Args:
        args: Command-line arguments (None to use sys.argv)

    Returns:
        Exit code
    """
    parser = create_argument_parser()
    parsed_args = parser.parse_args(args)

    # Setup logging
    setup_logging(
        verbose=parsed_args.verbose,
        log_file=parsed_args.log_file
    )

    # Process project
    return process_project(
        esx_file=parsed_args.esx_file,
        output_dir=parsed_args.output_dir,
        colors_config=parsed_args.colors_config
    )


if __name__ == '__main__':
    sys.exit(main())
