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
from .processors.tags import TagProcessor
from .filters import APFilter
from .analytics import GroupingAnalytics
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

    parser.add_argument(
        '--format',
        type=str,
        default='csv',
        help='Export format(s): csv, excel, html, json, or combinations like csv,excel,html,json (default: csv)'
    )

    # Filtering options
    filter_group = parser.add_argument_group('filtering options')

    filter_group.add_argument(
        '--filter-floor',
        type=str,
        help='Filter by floor names (comma-separated): "Floor 1,Floor 2"'
    )

    filter_group.add_argument(
        '--filter-color',
        type=str,
        help='Filter by colors (comma-separated): "Yellow,Red,Blue"'
    )

    filter_group.add_argument(
        '--filter-vendor',
        type=str,
        help='Filter by vendors (comma-separated): "Cisco,Aruba"'
    )

    filter_group.add_argument(
        '--filter-model',
        type=str,
        help='Filter by models (comma-separated): "AP-515,AP-635"'
    )

    filter_group.add_argument(
        '--filter-tag',
        action='append',
        help='Filter by tag (format: "TagKey:TagValue"). Can be used multiple times. Example: --filter-tag "Location:Building A" --filter-tag "Zone:Office"'
    )

    filter_group.add_argument(
        '--exclude-floor',
        type=str,
        help='Exclude floor names (comma-separated)'
    )

    filter_group.add_argument(
        '--exclude-color',
        type=str,
        help='Exclude colors (comma-separated)'
    )

    filter_group.add_argument(
        '--exclude-vendor',
        type=str,
        help='Exclude vendors (comma-separated)'
    )

    # Grouping options
    group_group = parser.add_argument_group('grouping options')

    group_group.add_argument(
        '--group-by',
        type=str,
        choices=['floor', 'color', 'vendor', 'model', 'tag'],
        help='Group results by specified dimension and display statistics'
    )

    group_group.add_argument(
        '--tag-key',
        type=str,
        help='Tag key name to use when --group-by tag is selected'
    )

    return parser


def process_project(
    esx_file: Path,
    output_dir: Path,
    colors_config: Path | None = None,
    export_formats: list[str] | None = None,
    filter_floors: list[str] | None = None,
    filter_colors: list[str] | None = None,
    filter_vendors: list[str] | None = None,
    filter_models: list[str] | None = None,
    filter_tags: dict[str, list[str]] | None = None,
    exclude_floors: list[str] | None = None,
    exclude_colors: list[str] | None = None,
    exclude_vendors: list[str] | None = None,
    group_by: str | None = None,
    tag_key: str | None = None
) -> int:
    """Process Ekahau project and generate BOM.

    Args:
        esx_file: Path to .esx file
        output_dir: Output directory for exports
        colors_config: Optional path to colors configuration
        export_formats: List of export formats (csv, excel, html, json)
        filter_floors: List of floors to include
        filter_colors: List of colors to include
        filter_vendors: List of vendors to include
        filter_models: List of models to include
        filter_tags: Dictionary of tag filters (key -> values)
        exclude_floors: List of floors to exclude
        exclude_colors: List of colors to exclude
        exclude_vendors: List of vendors to exclude
        group_by: Dimension to group by (floor, color, vendor, model, tag)
        tag_key: Tag key name (required when group_by='tag')

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
            tag_keys_data = parser.get_tag_keys()

            # Build floor lookup dictionary (optimized for O(1) access)
            floors = {
                floor["id"]: Floor(id=floor["id"], name=floor["name"])
                for floor in floor_plans_data.get("floorPlans", [])
            }
            logger.info(f"Found {len(floors)} floors")

            # Process tags
            tag_processor = TagProcessor(tag_keys_data)
            if tag_processor.tag_keys:
                logger.info(f"Found {len(tag_processor.tag_keys)} tag types: {', '.join(tag_processor.get_tag_key_names())}")

            # Process access points
            ap_processor = AccessPointProcessor(color_db, tag_processor)
            access_points = ap_processor.process(access_points_data, floors)

            # Apply filters if specified
            if any([filter_floors, filter_colors, filter_vendors, filter_models, filter_tags,
                    exclude_floors, exclude_colors, exclude_vendors]):
                logger.info(f"Applying filters to {len(access_points)} access points...")
                access_points = APFilter.apply_filters(
                    access_points,
                    include_floors=filter_floors,
                    include_colors=filter_colors,
                    include_vendors=filter_vendors,
                    include_models=filter_models,
                    include_tags=filter_tags,
                    exclude_floors=exclude_floors,
                    exclude_colors=exclude_colors,
                    exclude_vendors=exclude_vendors
                )

            # Apply grouping if specified
            if group_by:
                logger.info(f"Grouping {len(access_points)} access points by: {group_by}")

                if group_by == 'floor':
                    grouped = GroupingAnalytics.group_by_floor(access_points)
                elif group_by == 'color':
                    grouped = GroupingAnalytics.group_by_color(access_points)
                elif group_by == 'vendor':
                    grouped = GroupingAnalytics.group_by_vendor(access_points)
                elif group_by == 'model':
                    grouped = GroupingAnalytics.group_by_model(access_points)
                elif group_by == 'tag':
                    if not tag_key:
                        logger.error("--tag-key is required when using --group-by tag")
                        return 1
                    grouped = GroupingAnalytics.group_by_tag(access_points, tag_key)
                else:
                    logger.error(f"Unknown group-by dimension: {group_by}")
                    return 1

                # Display grouped results
                GroupingAnalytics.print_grouped_results(
                    grouped,
                    title=f"Access Points Grouped by {group_by.capitalize()}"
                )

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

            # Default to CSV if no format specified
            if not export_formats:
                export_formats = ['csv']

            # Export to requested formats
            from .exporters.excel_exporter import ExcelExporter
            from .exporters.html_exporter import HTMLExporter
            from .exporters.json_exporter import JSONExporter

            exporters = {
                'csv': CSVExporter(output_dir),
                'excel': ExcelExporter(output_dir),
                'html': HTMLExporter(output_dir),
                'json': JSONExporter(output_dir)
            }

            exported_files = []
            for format_name in export_formats:
                if format_name in exporters:
                    logger.info(f"Exporting to {format_name.upper()}...")
                    exporter = exporters[format_name]
                    files = exporter.export(project_data)
                    exported_files.extend(files)
                else:
                    logger.warning(f"Unknown export format: {format_name}")

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

    # Parse filter arguments
    def parse_comma_separated(value: str | None) -> list[str] | None:
        """Parse comma-separated values into list."""
        if not value:
            return None
        return [v.strip() for v in value.split(',') if v.strip()]

    filter_floors = parse_comma_separated(parsed_args.filter_floor)
    filter_colors = parse_comma_separated(parsed_args.filter_color)
    filter_vendors = parse_comma_separated(parsed_args.filter_vendor)
    filter_models = parse_comma_separated(parsed_args.filter_model)
    exclude_floors = parse_comma_separated(parsed_args.exclude_floor)
    exclude_colors = parse_comma_separated(parsed_args.exclude_color)
    exclude_vendors = parse_comma_separated(parsed_args.exclude_vendor)

    # Parse tag filters (format: "TagKey:TagValue")
    filter_tags = None
    if parsed_args.filter_tag:
        filter_tags = {}
        for tag_filter in parsed_args.filter_tag:
            if ':' in tag_filter:
                key, value = tag_filter.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key not in filter_tags:
                    filter_tags[key] = []
                filter_tags[key].append(value)
            else:
                logger.warning(f"Invalid tag filter format (expected 'Key:Value'): {tag_filter}")

    # Parse export formats
    export_formats = [f.strip().lower() for f in parsed_args.format.split(',')]

    # Process project
    return process_project(
        esx_file=parsed_args.esx_file,
        output_dir=parsed_args.output_dir,
        colors_config=parsed_args.colors_config,
        export_formats=export_formats,
        filter_floors=filter_floors,
        filter_colors=filter_colors,
        filter_vendors=filter_vendors,
        filter_models=filter_models,
        filter_tags=filter_tags,
        exclude_floors=exclude_floors,
        exclude_colors=exclude_colors,
        exclude_vendors=exclude_vendors,
        group_by=parsed_args.group_by,
        tag_key=parsed_args.tag_key
    )


if __name__ == '__main__':
    sys.exit(main())
