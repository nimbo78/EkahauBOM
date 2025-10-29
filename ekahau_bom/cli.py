#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Command-line interface for EkahauBOM."""

from __future__ import annotations


import argparse
import logging
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
    )
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from . import __version__
from .config import Config, ConfigError
from .parser import EkahauParser
from .processors.access_points import AccessPointProcessor
from .processors.antennas import AntennaProcessor
from .processors.tags import TagProcessor
from .processors.radios import RadioProcessor
from .processors.metadata import ProjectMetadataProcessor
from .processors.notes import NotesProcessor
from .filters import APFilter
from .analytics import GroupingAnalytics
from .exporters.csv_exporter import CSVExporter
from .models import Floor, ProjectData
from .constants import DEFAULT_OUTPUT_DIR
from .utils import load_color_database, ensure_output_dir, setup_logging

logger = logging.getLogger(__name__)

# Initialize Rich console if available
console = Console() if RICH_AVAILABLE else None


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="EkahauBOM",
        description="Generate Bill of Materials (BOM) from Ekahau AI project files",
        epilog="Example: python EkahauBOM.py project.esx --output-dir reports/",
    )

    parser.add_argument(
        "esx_file",
        type=Path,
        nargs="?",
        help="Path to Ekahau .esx project file (optional if --batch is used)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for generated files (default: {DEFAULT_OUTPUT_DIR})",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: config/config.yaml)",
    )

    parser.add_argument(
        "--colors-config",
        type=Path,
        help="Path to custom colors configuration file (YAML)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    parser.add_argument("--log-file", type=Path, help="Path to log file (optional)")

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--format",
        type=str,
        default="csv",
        help="Export format(s): csv, excel, html, json, pdf, or combinations like csv,excel,html,json,pdf (default: csv)",
    )

    # Filtering options
    filter_group = parser.add_argument_group("filtering options")

    filter_group.add_argument(
        "--filter-floor",
        type=str,
        help='Filter by floor names (comma-separated): "Floor 1,Floor 2"',
    )

    filter_group.add_argument(
        "--filter-color",
        type=str,
        help='Filter by colors (comma-separated): "Yellow,Red,Blue"',
    )

    filter_group.add_argument(
        "--filter-vendor",
        type=str,
        help='Filter by vendors (comma-separated): "Cisco,Aruba"',
    )

    filter_group.add_argument(
        "--filter-model",
        type=str,
        help='Filter by models (comma-separated): "AP-515,AP-635"',
    )

    filter_group.add_argument(
        "--filter-tag",
        action="append",
        help='Filter by tag (format: "TagKey:TagValue"). Can be used multiple times. Example: --filter-tag "Location:Building A" --filter-tag "Zone:Office"',
    )

    filter_group.add_argument(
        "--exclude-floor", type=str, help="Exclude floor names (comma-separated)"
    )

    filter_group.add_argument(
        "--exclude-color", type=str, help="Exclude colors (comma-separated)"
    )

    filter_group.add_argument(
        "--exclude-vendor", type=str, help="Exclude vendors (comma-separated)"
    )

    # Grouping options
    group_group = parser.add_argument_group("grouping options")

    group_group.add_argument(
        "--group-by",
        type=str,
        choices=["floor", "color", "vendor", "model", "tag"],
        help="Group results by specified dimension and display statistics",
    )

    group_group.add_argument(
        "--tag-key",
        type=str,
        help="Tag key name to use when --group-by tag is selected",
    )

    # Pricing options
    pricing_group = parser.add_argument_group("pricing options")

    pricing_group.add_argument(
        "--enable-pricing",
        action="store_true",
        help="Enable cost calculations and include pricing in reports",
    )

    pricing_group.add_argument(
        "--pricing-file", type=Path, help="Path to custom pricing database (YAML file)"
    )

    pricing_group.add_argument(
        "--discount",
        type=float,
        default=0.0,
        help="Additional discount percentage to apply (0-100, default: 0)",
    )

    pricing_group.add_argument(
        "--no-volume-discounts",
        action="store_true",
        help="Disable automatic volume-based discounts",
    )

    # Batch processing options
    batch_group = parser.add_argument_group("batch processing options")

    batch_group.add_argument(
        "--batch", type=Path, help="Process all .esx files in the specified directory"
    )

    batch_group.add_argument(
        "--recursive",
        action="store_true",
        help="Search for .esx files recursively in subdirectories (use with --batch)",
    )

    # Visualization options
    viz_group = parser.add_argument_group("visualization options")

    viz_group.add_argument(
        "--visualize-floor-plans",
        action="store_true",
        help="Generate floor plan images with AP placements overlaid (requires Pillow library)",
    )

    viz_group.add_argument(
        "--ap-circle-radius",
        type=int,
        default=15,
        help="Radius of AP marker circles in pixels (default: 15)",
    )

    viz_group.add_argument(
        "--no-ap-names",
        action="store_true",
        help="Hide AP names on floor plan visualizations",
    )

    viz_group.add_argument(
        "--show-azimuth-arrows",
        action="store_true",
        help="Show azimuth direction arrows on AP markers (useful for wall-mounted and directional APs)",
    )

    viz_group.add_argument(
        "--ap-opacity",
        type=float,
        default=0.6,
        help="Opacity for AP markers (0.0-1.0, default: 0.6 = 60%% for better floor plan visibility)",
    )

    return parser


def print_header():
    """Print application header with Rich."""
    if RICH_AVAILABLE and console:
        console.print(
            Panel.fit(
                "[bold blue]EkahauBOM[/bold blue] - Bill of Materials Generator\n"
                f"[dim]Version {__version__}[/dim]",
                border_style="blue",
            )
        )
    else:
        logger.info(f"EkahauBOM - Version {__version__}")


def print_summary_table(
    access_points,
    antennas,
    radios,
    floors,
    notes=None,
    cable_notes=None,
    picture_notes=None,
):
    """Print summary statistics table with Rich."""
    if not RICH_AVAILABLE or not console:
        return

    table = Table(
        title="Project Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="green")

    table.add_row("Access Points", str(len(access_points)))
    table.add_row("Antennas", str(len(antennas)))
    table.add_row("Radios", str(len(radios)))
    table.add_row("Floors", str(len(floors)))

    # Unique vendors
    unique_vendors = len(set(ap.vendor for ap in access_points))
    table.add_row("Unique Vendors", str(unique_vendors))

    # Notes counts
    if notes is not None:
        table.add_row("Text Notes", str(len(notes)))
    if cable_notes is not None:
        table.add_row("Cable Notes", str(len(cable_notes)))
    if picture_notes is not None:
        table.add_row("Picture Notes", str(len(picture_notes)))

    console.print(table)


def print_grouping_table(title, data_dict):
    """Print grouping statistics with Rich."""
    if not RICH_AVAILABLE or not console or not data_dict:
        return

    total = sum(data_dict.values())
    table = Table(
        title=title, box=box.SIMPLE, show_header=True, header_style="bold magenta"
    )
    table.add_column("Name", style="yellow")
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Percentage", justify="right", style="green")

    for name, count in sorted(data_dict.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        table.add_row(str(name), str(count), f"{percentage:.1f}%")

    console.print(table)


def print_analytics_table(analytics_data):
    """Print analytics data as table."""
    if not RICH_AVAILABLE or not console or not analytics_data:
        return

    table = Table(
        title="Analytics", box=box.ROUNDED, show_header=True, header_style="bold yellow"
    )
    table.add_column("Metric", style="yellow")
    table.add_column("Value", justify="right", style="cyan")

    for key, value in analytics_data.items():
        if isinstance(value, float):
            table.add_row(key, f"{value:.2f}")
        else:
            table.add_row(key, str(value))

    console.print(table)


def print_cost_summary(cost_summary):
    """Print cost summary with Rich."""
    if not RICH_AVAILABLE or not console or not cost_summary:
        return

    table = Table(
        title="💰 Cost Summary",
        box=box.DOUBLE,
        show_header=True,
        header_style="bold green",
    )
    table.add_column("Item", style="cyan")
    table.add_column("Amount", justify="right", style="green")

    table.add_row("Access Points", f"${cost_summary.grand_total:,.2f}")
    if hasattr(cost_summary, "total_discount") and cost_summary.total_discount > 0:
        table.add_row(
            "Total Savings", f"[red]-${cost_summary.total_discount:,.2f}[/red]"
        )
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold green]${cost_summary.grand_total:,.2f}[/bold green]",
    )

    console.print(table)


def print_export_summary(exported_files):
    """Print exported files summary."""
    if not RICH_AVAILABLE or not console:
        return

    table = Table(
        title="📄 Generated Files",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold blue",
    )
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right", style="yellow")

    for file_path in exported_files:
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            table.add_row(file_path.name, f"{size_kb:.1f} KB")

    console.print(table)
    console.print(
        f"\n[bold green]✓[/bold green] Reports saved to: [cyan]{exported_files[0].parent if exported_files else 'output/'}[/cyan]"
    )


def find_esx_files(directory: Path, recursive: bool = False) -> list[Path]:
    """Find all .esx files in the specified directory.

    Args:
        directory: Directory to search for .esx files
        recursive: If True, search recursively in subdirectories

    Returns:
        List of paths to .esx files

    Raises:
        FileNotFoundError: If directory doesn't exist
        NotADirectoryError: If path is not a directory
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    if recursive:
        # Recursive search using rglob
        esx_files = list(directory.rglob("*.esx"))
    else:
        # Non-recursive search using glob
        esx_files = list(directory.glob("*.esx"))

    # Sort files by name for consistent processing order
    esx_files.sort()

    logger.info(
        f"Found {len(esx_files)} .esx file(s) in {directory}"
        + (" (recursive)" if recursive else "")
    )

    return esx_files


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
    tag_key: str | None = None,
    enable_pricing: bool = False,
    pricing_file: Path | None = None,
    discount: float = 0.0,
    no_volume_discounts: bool = False,
    visualize_floor_plans: bool = False,
    ap_circle_radius: int = 15,
    show_ap_names: bool = True,
    show_azimuth_arrows: bool = False,
    ap_opacity: float = 0.6,
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
        enable_pricing: Enable cost calculations
        pricing_file: Custom pricing database file
        discount: Additional discount percentage (0-100)
        no_volume_discounts: Disable volume-based discounts
        visualize_floor_plans: Generate floor plan visualizations with APs
        ap_circle_radius: Radius of AP marker circles in pixels
        show_ap_names: Whether to show AP names on visualizations
        show_azimuth_arrows: Whether to show azimuth direction arrows on AP markers
        ap_opacity: Opacity for AP markers (0.0-1.0, 0.6 = 60%)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Print header
        print_header()

        # Ensure output directory exists
        ensure_output_dir(output_dir)

        # Load color database
        color_db = load_color_database(colors_config)

        # Parse .esx file with progress
        if RICH_AVAILABLE and console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Processing project: {esx_file.name}", total=None
                )
                parser_context = EkahauParser(esx_file)
                progress.update(task, completed=True)
        else:
            logger.info(f"Processing project: {esx_file}")
            parser_context = EkahauParser(esx_file)

        with parser_context as parser:
            # Get raw data
            access_points_data = parser.get_access_points()
            floor_plans_data = parser.get_floor_plans()
            simulated_radios_data = parser.get_simulated_radios()
            antenna_types_data = parser.get_antenna_types()
            tag_keys_data = parser.get_tag_keys()
            project_metadata_data = parser.get_project_metadata()
            notes_data = parser.get_notes()
            cable_notes_data = parser.get_cable_notes()
            picture_notes_data = parser.get_picture_notes()

            # Build floor lookup dictionary (optimized for O(1) access)
            floors = {
                floor["id"]: Floor(id=floor["id"], name=floor["name"])
                for floor in floor_plans_data.get("floorPlans", [])
            }
            logger.info(f"Found {len(floors)} floors")

            # Process project metadata
            metadata_processor = ProjectMetadataProcessor()
            project_metadata = metadata_processor.process(project_metadata_data)

            # Process tags
            tag_processor = TagProcessor(tag_keys_data)
            if tag_processor.tag_keys:
                logger.info(
                    f"Found {len(tag_processor.tag_keys)} tag types: {', '.join(tag_processor.get_tag_key_names())}"
                )

            # Process access points
            ap_processor = AccessPointProcessor(color_db, tag_processor)
            access_points = ap_processor.process(
                access_points_data, floors, simulated_radios_data
            )

            # Apply filters if specified
            if any(
                [
                    filter_floors,
                    filter_colors,
                    filter_vendors,
                    filter_models,
                    filter_tags,
                    exclude_floors,
                    exclude_colors,
                    exclude_vendors,
                ]
            ):
                logger.info(
                    f"Applying filters to {len(access_points)} access points..."
                )
                access_points = APFilter.apply_filters(
                    access_points,
                    include_floors=filter_floors,
                    include_colors=filter_colors,
                    include_vendors=filter_vendors,
                    include_models=filter_models,
                    include_tags=filter_tags,
                    exclude_floors=exclude_floors,
                    exclude_colors=exclude_colors,
                    exclude_vendors=exclude_vendors,
                )

            # Apply grouping if specified
            if group_by:
                logger.info(
                    f"Grouping {len(access_points)} access points by: {group_by}"
                )

                if group_by == "floor":
                    grouped = GroupingAnalytics.group_by_floor(access_points)
                elif group_by == "color":
                    grouped = GroupingAnalytics.group_by_color(access_points)
                elif group_by == "vendor":
                    grouped = GroupingAnalytics.group_by_vendor(access_points)
                elif group_by == "model":
                    grouped = GroupingAnalytics.group_by_model(access_points)
                elif group_by == "tag":
                    if not tag_key:
                        logger.error("--tag-key is required when using --group-by tag")
                        return 1
                    grouped = GroupingAnalytics.group_by_tag(access_points, tag_key)
                else:
                    logger.error(f"Unknown group-by dimension: {group_by}")
                    return 1

                # Display grouped results
                GroupingAnalytics.print_grouped_results(
                    grouped, title=f"Access Points Grouped by {group_by.capitalize()}"
                )

            # Process antennas (with access_points_data for external antenna detection)
            antenna_processor = AntennaProcessor()
            antennas = antenna_processor.process(
                simulated_radios_data, antenna_types_data, access_points_data
            )

            # Process radios
            radio_processor = RadioProcessor()
            radios = radio_processor.process(simulated_radios_data)

            # Process notes
            notes_processor = NotesProcessor()
            notes = notes_processor.process_notes(notes_data)
            cable_notes = notes_processor.process_cable_notes(cable_notes_data, floors)
            picture_notes = notes_processor.process_picture_notes(
                picture_notes_data, floors
            )
            logger.info(
                f"Found {len(notes)} text notes, {len(cable_notes)} cable notes, {len(picture_notes)} picture notes"
            )

            # Process network settings
            from .processors.network_settings import NetworkSettingsProcessor

            network_settings_data = parser.get_network_capacity_settings()
            network_settings = NetworkSettingsProcessor.process_network_settings(
                network_settings_data
            )

            # Create project data container
            project_data = ProjectData(
                access_points=access_points,
                antennas=antennas,
                floors=floors,
                project_name=esx_file.stem,
                radios=radios,
                metadata=project_metadata,
                notes=notes,
                cable_notes=cable_notes,
                picture_notes=picture_notes,
                network_settings=network_settings,
                group_by=group_by,
                tag_key=tag_key,
            )

            # Display advanced analytics
            from .analytics import CoverageAnalytics, MountingAnalytics, RadioAnalytics

            # Coverage analytics
            try:
                measured_areas_data = parser.get_measured_areas()
                if measured_areas_data and measured_areas_data.get("measuredAreas"):
                    logger.info("=" * 60)
                    logger.info("Coverage Analytics")
                    logger.info("=" * 60)
                    coverage_metrics = CoverageAnalytics.calculate_coverage_metrics(
                        access_points, measured_areas_data
                    )
                    # Metrics are logged by the analytics class
            except Exception as e:
                logger.debug(f"Could not load coverage analytics: {e}")

            # Mounting analytics
            if any(ap.mounting_height is not None for ap in access_points):
                logger.info("=" * 60)
                logger.info("Installation & Mounting Analytics")
                logger.info("=" * 60)
                mounting_metrics = MountingAnalytics.calculate_mounting_metrics(
                    access_points
                )
                # Display height distribution
                height_dist = MountingAnalytics.group_by_height_range(access_points)
                logger.info("Height Distribution:")
                for range_label, count in sorted(height_dist.items()):
                    if count > 0:
                        logger.info(f"  {range_label}: {count} APs")

            # Radio analytics
            if radios:
                logger.info("=" * 60)
                logger.info("Radio & Wi-Fi Configuration Analytics")
                logger.info("=" * 60)
                radio_metrics = RadioAnalytics.calculate_radio_metrics(radios)

                # Frequency bands
                logger.info("Frequency Band Distribution:")
                for band, count in sorted(radio_metrics.band_distribution.items()):
                    percentage = (
                        (count / radio_metrics.total_radios * 100)
                        if radio_metrics.total_radios > 0
                        else 0
                    )
                    logger.info(f"  {band}: {count} radios ({percentage:.1f}%)")

                # Wi-Fi standards
                if radio_metrics.standard_distribution:
                    logger.info("Wi-Fi Standards:")
                    for standard, count in sorted(
                        radio_metrics.standard_distribution.items()
                    ):
                        percentage = (
                            (count / radio_metrics.total_radios * 100)
                            if radio_metrics.total_radios > 0
                            else 0
                        )
                        logger.info(f"  {standard}: {count} radios ({percentage:.1f}%)")

                # Channel widths
                if radio_metrics.channel_width_distribution:
                    logger.info("Channel Width Distribution:")
                    for width, count in sorted(
                        radio_metrics.channel_width_distribution.items(),
                        key=lambda x: x[0] if x[0] else 0,
                    ):
                        logger.info(f"  {width} MHz: {count} radios")

                # Channel distribution
                if radio_metrics.channel_distribution:
                    logger.info("Channel Distribution:")
                    # Show top 10 most used channels
                    top_channels = sorted(
                        radio_metrics.channel_distribution.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:10]
                    for channel, count in top_channels:
                        logger.info(f"  Channel {channel}: {count} radios")

                # TX Power
                if radio_metrics.avg_tx_power:
                    logger.info(
                        f"TX Power: avg={radio_metrics.avg_tx_power:.1f} dBm, "
                        + f"min={radio_metrics.min_tx_power:.1f} dBm, "
                        + f"max={radio_metrics.max_tx_power:.1f} dBm"
                    )

            # Network settings (SSID, rates, etc.)
            if network_settings:
                logger.info("")  # Empty line for readability
                logger.info("Network Configuration:")

                # SSID summary
                ssid_summary = NetworkSettingsProcessor.get_ssid_summary(
                    network_settings
                )
                if ssid_summary:
                    logger.info("  SSID Configuration:")
                    if ssid_summary.get("ssids_2_4ghz"):
                        logger.info(
                            f"    2.4 GHz: {ssid_summary['ssids_2_4ghz']} SSID(s), max {ssid_summary['max_clients_2_4ghz']} clients"
                        )
                    if ssid_summary.get("ssids_5ghz"):
                        logger.info(
                            f"    5 GHz: {ssid_summary['ssids_5ghz']} SSID(s), max {ssid_summary['max_clients_5ghz']} clients"
                        )

            # Cable infrastructure analytics
            if cable_notes:
                from .cable_analytics import CableAnalytics

                logger.info("=" * 60)
                logger.info("Cable Infrastructure Analytics")
                logger.info("=" * 60)
                cable_metrics = CableAnalytics.calculate_cable_metrics(
                    cable_notes, floors
                )

                # Cable counts by floor
                if cable_metrics.cables_by_floor:
                    logger.info("Cable Routes by Floor:")
                    for floor_name, count in sorted(
                        cable_metrics.cables_by_floor.items()
                    ):
                        length = cable_metrics.length_by_floor.get(floor_name, 0.0)
                        logger.info(
                            f"  {floor_name}: {count} routes ({length:.1f} units)"
                        )

                # Cable BOM
                cable_bom = CableAnalytics.generate_cable_bom(cable_metrics)
                logger.info("Cable Bill of Materials:")
                for item in cable_bom:
                    logger.info(
                        f"  {item['description']}: {item['quantity']} {item['unit']}"
                    )

            # Calculate costs if enabled
            cost_summary = None
            if enable_pricing:
                from .pricing import PricingDatabase, CostCalculator

                logger.info("Calculating project costs...")
                pricing_db = PricingDatabase(pricing_file)
                calculator = CostCalculator(
                    pricing_db,
                    custom_discount=discount,
                    apply_volume_discounts=not no_volume_discounts,
                )

                ap_costs, antenna_costs, total_costs = calculator.calculate_total_cost(
                    access_points, antennas
                )

                logger.info(f"Cost Summary:")
                logger.info(f"  Access Points: ${ap_costs.grand_total:,.2f}")
                logger.info(f"  Antennas: ${antenna_costs.grand_total:,.2f}")
                logger.info(
                    f"  Total: ${total_costs.grand_total:,.2f} {total_costs.currency}"
                )
                if total_costs.total_discount > 0:
                    logger.info(f"  Total Savings: ${total_costs.total_discount:,.2f}")

                cost_summary = total_costs

            # Default to CSV if no format specified
            if not export_formats:
                export_formats = ["csv"]

            # Export to requested formats
            from .exporters.excel_exporter import ExcelExporter
            from .exporters.html_exporter import HTMLExporter
            from .exporters.json_exporter import JSONExporter

            exporters = {
                "csv": CSVExporter(output_dir),
                "excel": ExcelExporter(output_dir),
                "html": HTMLExporter(output_dir),
                "json": JSONExporter(output_dir),
            }

            # Import PDF exporter only if needed (WeasyPrint may not be installed)
            if "pdf" in export_formats:
                try:
                    from .exporters.pdf_exporter import PDFExporter

                    exporters["pdf"] = PDFExporter(output_dir)
                except ImportError as e:
                    logger.warning(f"PDF export not available: {e}")
                    logger.warning(
                        "Install WeasyPrint to enable PDF export: pip install weasyprint"
                    )

            # Export with progress
            exported_files = []
            if RICH_AVAILABLE and console:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    export_task = progress.add_task(
                        "[cyan]Exporting reports...", total=len(export_formats)
                    )
                    for format_name in export_formats:
                        if format_name in exporters:
                            progress.update(
                                export_task,
                                description=f"[cyan]Exporting to {format_name.upper()}...",
                            )
                            exporter = exporters[format_name]
                            files = exporter.export(project_data)
                            exported_files.extend(files)
                            progress.advance(export_task)
                        else:
                            console.print(
                                f"[yellow]⚠[/yellow] Unknown export format: {format_name}"
                            )
                            progress.advance(export_task)
            else:
                for format_name in export_formats:
                    if format_name in exporters:
                        logger.info(f"Exporting to {format_name.upper()}...")
                        exporter = exporters[format_name]
                        files = exporter.export(project_data)
                        exported_files.extend(files)
                    else:
                        logger.warning(f"Unknown export format: {format_name}")

            # Generate floor plan visualizations if requested
            visualization_files = []
            if visualize_floor_plans:
                try:
                    from .visualizers.floor_plan import FloorPlanVisualizer

                    logger.info("=" * 60)
                    logger.info("Generating Floor Plan Visualizations")
                    logger.info("=" * 60)

                    # Create visualizations subdirectory
                    viz_output_dir = output_dir / "visualizations"
                    viz_output_dir.mkdir(parents=True, exist_ok=True)

                    # Create visualizer
                    with FloorPlanVisualizer(
                        esx_path=esx_file,
                        output_dir=viz_output_dir,
                        ap_circle_radius=ap_circle_radius,
                        show_ap_names=show_ap_names,
                        show_azimuth_arrows=show_azimuth_arrows,
                        ap_opacity=ap_opacity,
                    ) as visualizer:
                        visualization_files = visualizer.visualize_all_floors(
                            floors=floors, access_points=access_points, radios=radios
                        )

                    if visualization_files:
                        logger.info(
                            f"Generated {len(visualization_files)} floor plan visualizations:"
                        )
                        for viz_file in visualization_files:
                            logger.info(f"  - {viz_file.name}")
                    else:
                        logger.warning("No floor plan visualizations were generated")

                except ImportError as e:
                    logger.error(
                        f"Floor plan visualization requires Pillow library: {e}"
                    )
                    logger.error("Install with: pip install Pillow")
                except Exception as e:
                    logger.error(f"Error generating floor plan visualizations: {e}")
                    import traceback

                    logger.debug(traceback.format_exc())

            # Print summary with Rich
            if RICH_AVAILABLE and console:
                console.print(
                    "\n[bold green]✓ Processing completed successfully![/bold green]\n"
                )
                print_summary_table(
                    access_points,
                    antennas,
                    radios,
                    floors,
                    notes,
                    cable_notes,
                    picture_notes,
                )
                # Combine exported files and visualization files for summary
                all_files = exported_files + visualization_files
                print_export_summary(all_files)
            else:
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
        if RICH_AVAILABLE and console:
            console.print(f"[bold red]✗ Error:[/bold red] File not found: {e}")
        else:
            logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        if RICH_AVAILABLE and console:
            console.print(f"[bold red]✗ Error:[/bold red] Invalid input: {e}")
        else:
            logger.error(f"Invalid input: {e}")
        return 1
    except KeyError as e:
        if RICH_AVAILABLE and console:
            console.print(
                f"[bold red]✗ Error:[/bold red] Missing required data in .esx file: {e}"
            )
        else:
            logger.error(f"Missing required data in .esx file: {e}")
        return 1
    except ImportError as e:
        if RICH_AVAILABLE and console:
            console.print(f"[bold red]✗ Error:[/bold red] Missing dependency: {e}")
            console.print(
                "[yellow]Hint:[/yellow] Install missing dependencies with: pip install -r requirements.txt"
            )
        else:
            logger.error(f"Missing dependency: {e}")
        return 1
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[bold red]✗ Error:[/bold red] {e}")
            if logger.level == logging.DEBUG:
                console.print_exception()
        else:
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

    # Setup logging (using CLI args for now, will be updated after config merge)
    setup_logging(verbose=parsed_args.verbose, log_file=parsed_args.log_file)

    # Load configuration file
    try:
        config = Config.load(parsed_args.config)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        if RICH_AVAILABLE and console:
            console.print(f"[bold red]✗ Configuration error:[/bold red] {e}")
        return 1

    # Merge configuration with CLI arguments (CLI takes precedence)
    merged_config = config.merge_with_args(parsed_args)

    # Update logging if config changed it
    if merged_config.get("log_level") or merged_config.get("log_file"):
        setup_logging(
            verbose=(merged_config.get("log_level") == "DEBUG"),
            log_file=merged_config.get("log_file"),
        )

    # Extract merged configuration values
    filter_floors = merged_config.get("filter_floors")
    filter_colors = merged_config.get("filter_colors")
    filter_vendors = merged_config.get("filter_vendors")
    filter_models = merged_config.get("filter_models")
    exclude_floors = merged_config.get("exclude_floors")
    exclude_colors = merged_config.get("exclude_colors")
    exclude_vendors = merged_config.get("exclude_vendors")

    # Parse tag filters (format: "TagKey:TagValue")
    filter_tags = None
    raw_filter_tags = merged_config.get("filter_tags")
    if raw_filter_tags:
        filter_tags = {}
        # Handle both list and dict formats
        if isinstance(raw_filter_tags, list):
            for tag_filter in raw_filter_tags:
                if ":" in tag_filter:
                    key, value = tag_filter.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key not in filter_tags:
                        filter_tags[key] = []
                    filter_tags[key].append(value)
                else:
                    logger.warning(
                        f"Invalid tag filter format (expected 'Key:Value'): {tag_filter}"
                    )
        elif isinstance(raw_filter_tags, dict):
            filter_tags = raw_filter_tags

    # Export formats from merged config
    export_formats = merged_config.get("export_formats", ["csv"])

    # Determine files to process
    files_to_process = []

    batch_dir = merged_config.get("batch")
    if batch_dir:
        # Batch mode: find all .esx files in directory
        try:
            files_to_process = find_esx_files(
                batch_dir, merged_config.get("recursive", False)
            )
            if not files_to_process:
                logger.error(f"No .esx files found in {batch_dir}")
                return 1

            if RICH_AVAILABLE and console:
                console.print(f"\n[bold cyan]Batch Processing Mode[/bold cyan]")
                console.print(
                    f"Found [bold green]{len(files_to_process)}[/bold green] project file(s)"
                )
                console.print(f"Directory: [cyan]{batch_dir}[/cyan]")
                if merged_config.get("recursive"):
                    console.print("[yellow]Recursive search enabled[/yellow]")
                console.print()
            else:
                logger.info(f"Batch mode: Processing {len(files_to_process)} file(s)")
        except (FileNotFoundError, NotADirectoryError) as e:
            if RICH_AVAILABLE and console:
                console.print(f"[bold red]✗ Error:[/bold red] {e}")
            else:
                logger.error(str(e))
            return 1
    else:
        # Single file mode
        if not parsed_args.esx_file:
            logger.error("Either provide an .esx file or use --batch option")
            if RICH_AVAILABLE and console:
                console.print(
                    "[bold red]✗ Error:[/bold red] Either provide an .esx file or use --batch option"
                )
            return 1
        files_to_process = [parsed_args.esx_file]

    # Process all files
    total_files = len(files_to_process)
    failed_files = []

    for idx, esx_file in enumerate(files_to_process, 1):
        if total_files > 1:
            if RICH_AVAILABLE and console:
                console.print(f"\n[bold blue]{'='*60}[/bold blue]")
                console.print(
                    f"[bold cyan]Processing file {idx}/{total_files}:[/bold cyan] [yellow]{esx_file.name}[/yellow]"
                )
                console.print(f"[bold blue]{'='*60}[/bold blue]\n")
            else:
                logger.info(f"Processing file {idx}/{total_files}: {esx_file.name}")

        try:
            exit_code = process_project(
                esx_file=esx_file,
                output_dir=merged_config.get("output_dir"),
                colors_config=merged_config.get("colors_config"),
                export_formats=export_formats,
                filter_floors=filter_floors,
                filter_colors=filter_colors,
                filter_vendors=filter_vendors,
                filter_models=filter_models,
                filter_tags=filter_tags,
                exclude_floors=exclude_floors,
                exclude_colors=exclude_colors,
                exclude_vendors=exclude_vendors,
                group_by=merged_config.get("group_by"),
                tag_key=merged_config.get("tag_key"),
                enable_pricing=merged_config.get("enable_pricing"),
                pricing_file=merged_config.get("pricing_file"),
                discount=merged_config.get("discount", 0.0),
                no_volume_discounts=merged_config.get("no_volume_discounts", False),
                visualize_floor_plans=merged_config.get("visualize_floor_plans", False),
                ap_circle_radius=merged_config.get("ap_circle_radius", 15),
                show_ap_names=not merged_config.get("no_ap_names", False),
                show_azimuth_arrows=merged_config.get("show_azimuth_arrows", False),
                ap_opacity=merged_config.get("ap_opacity", 0.6),
            )

            if exit_code != 0:
                failed_files.append(esx_file.name)
        except Exception as e:
            logger.error(f"Failed to process {esx_file.name}: {e}")
            if RICH_AVAILABLE and console:
                console.print(
                    f"[bold red]✗ Failed to process {esx_file.name}:[/bold red] {e}"
                )
            failed_files.append(esx_file.name)

    # Print summary for batch mode
    if total_files > 1:
        if RICH_AVAILABLE and console:
            console.print(f"\n[bold blue]{'='*60}[/bold blue]")
            console.print(f"[bold cyan]Batch Processing Summary[/bold cyan]")
            console.print(f"[bold blue]{'='*60}[/bold blue]\n")

            table = Table(
                title="Results",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Count", justify="right", style="green")

            table.add_row("Total Files", str(total_files))
            table.add_row("Successful", str(total_files - len(failed_files)))
            if failed_files:
                table.add_row("Failed", f"[red]{len(failed_files)}[/red]")

            console.print(table)

            if failed_files:
                console.print("\n[bold red]Failed files:[/bold red]")
                for filename in failed_files:
                    console.print(f"  [red]✗[/red] {filename}")
        else:
            logger.info(
                f"Batch processing complete: {total_files - len(failed_files)}/{total_files} successful"
            )
            if failed_files:
                logger.error(f"Failed files: {', '.join(failed_files)}")

    return 1 if failed_files else 0


if __name__ == "__main__":
    sys.exit(main())
