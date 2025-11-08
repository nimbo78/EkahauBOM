#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Batch processing functionality for EkahauBOM."""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .models import AccessPoint

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of processing a single file in batch."""

    filename: str
    success: bool
    processing_time: float  # seconds
    error_message: str | None = None
    access_points_count: int = 0
    antennas_count: int = 0
    project_data: dict[str, Any] | None = None


@dataclass
class AggregatedReport:
    """Aggregated statistics across all projects in batch."""

    total_projects: int = 0
    successful_projects: int = 0
    failed_projects: int = 0
    total_processing_time: float = 0.0

    # Aggregated BOM
    total_access_points: int = 0
    total_antennas: int = 0
    ap_by_vendor_model: dict[tuple[str, str], int] = field(default_factory=dict)
    antenna_by_model: dict[str, int] = field(default_factory=dict)

    # Per-project data
    project_results: list[BatchResult] = field(default_factory=list)

    # Cost statistics (if pricing enabled)
    total_cost: float | None = None
    cost_by_vendor: dict[str, float] = field(default_factory=dict)

    def add_result(self, result: BatchResult) -> None:
        """Add a batch result and update aggregated statistics."""
        self.project_results.append(result)
        self.total_projects += 1
        self.total_processing_time += result.processing_time

        if result.success:
            self.successful_projects += 1
            self.total_access_points += result.access_points_count
            self.total_antennas += result.antennas_count

            # Aggregate BOM data if available
            if result.project_data:
                access_points = result.project_data.get("access_points", [])
                for ap in access_points:
                    key = (ap.get("vendor", "Unknown"), ap.get("model", "Unknown"))
                    quantity = ap.get("quantity", 1)
                    self.ap_by_vendor_model[key] = self.ap_by_vendor_model.get(key, 0) + quantity

                antennas = result.project_data.get("antennas", [])
                for antenna in antennas:
                    if antenna.get("is_external", False):
                        model = antenna.get("antenna_model", "Unknown")
                        quantity = antenna.get("quantity", 1)
                        self.antenna_by_model[model] = (
                            self.antenna_by_model.get(model, 0) + quantity
                        )
        else:
            self.failed_projects += 1

    def get_summary_table(self) -> Table | None:
        """Generate Rich table with batch summary."""
        if not RICH_AVAILABLE:
            return None

        table = Table(
            title="Batch Processing Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        # Overall statistics
        table.add_row("Total Projects", str(self.total_projects))
        table.add_row("Successful", f"[green]{self.successful_projects}[/green]")

        if self.failed_projects > 0:
            table.add_row("Failed", f"[red]{self.failed_projects}[/red]")

        table.add_row("Total Time", f"{self.total_processing_time:.1f}s")

        if self.successful_projects > 0:
            avg_time = self.total_processing_time / self.successful_projects
            table.add_row("Avg Time/Project", f"{avg_time:.1f}s")

        # BOM statistics
        table.add_row("", "")  # Separator
        table.add_row("[bold]Equipment Totals[/bold]", "")
        table.add_row("Total Access Points", str(self.total_access_points))
        table.add_row("Total Antennas", str(self.total_antennas))

        return table

    def get_bom_table(self) -> Table | None:
        """Generate Rich table with aggregated BOM."""
        if not RICH_AVAILABLE or not self.ap_by_vendor_model:
            return None

        table = Table(
            title="Aggregated BOM - Access Points",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Quantity", justify="right", style="green")
        table.add_column("Vendor", style="cyan")
        table.add_column("Model", style="yellow")

        # Sort by quantity (descending)
        sorted_items = sorted(self.ap_by_vendor_model.items(), key=lambda x: x[1], reverse=True)

        for (vendor, model), count in sorted_items:
            table.add_row(str(count), vendor, model)

        return table

    def generate_text_summary(self, output_path: Path) -> None:
        """Generate text summary file.

        Args:
            output_path: Path to save summary file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("BATCH PROCESSING SUMMARY\n")
            f.write("=" * 70 + "\n\n")

            # Overall statistics
            f.write(f"Total Projects:        {self.total_projects}\n")
            f.write(f"Successful:            {self.successful_projects}\n")
            f.write(f"Failed:                {self.failed_projects}\n")
            f.write(f"Total Processing Time: {self.total_processing_time:.1f}s\n")

            if self.successful_projects > 0:
                avg_time = self.total_processing_time / self.successful_projects
                f.write(f"Avg Time/Project:      {avg_time:.1f}s\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write("AGGREGATED BOM - ACCESS POINTS\n")
            f.write("=" * 70 + "\n\n")

            if self.ap_by_vendor_model:
                f.write(f"{'Quantity':<10} {'Vendor':<20} {'Model':<40}\n")
                f.write("-" * 70 + "\n")

                sorted_items = sorted(
                    self.ap_by_vendor_model.items(), key=lambda x: x[1], reverse=True
                )

                for (vendor, model), count in sorted_items:
                    f.write(f"{count:<10} {vendor:<20} {model:<40}\n")

                f.write("-" * 70 + "\n")
                f.write(f"{'TOTAL':<10} {self.total_access_points}\n")
            else:
                f.write("No access points found\n")

            # External antennas
            if self.antenna_by_model:
                f.write("\n" + "=" * 70 + "\n")
                f.write("AGGREGATED BOM - EXTERNAL ANTENNAS\n")
                f.write("=" * 70 + "\n\n")

                f.write(f"{'Quantity':<10} {'Model':<60}\n")
                f.write("-" * 70 + "\n")

                sorted_antennas = sorted(
                    self.antenna_by_model.items(), key=lambda x: x[1], reverse=True
                )

                for model, count in sorted_antennas:
                    f.write(f"{count:<10} {model:<60}\n")

                f.write("-" * 70 + "\n")
                f.write(f"{'TOTAL':<10} {self.total_antennas}\n")

            # Failed projects
            if self.failed_projects > 0:
                f.write("\n" + "=" * 70 + "\n")
                f.write("FAILED PROJECTS\n")
                f.write("=" * 70 + "\n\n")

                for result in self.project_results:
                    if not result.success:
                        f.write(f"✗ {result.filename}\n")
                        if result.error_message:
                            f.write(f"  Error: {result.error_message}\n")

            f.write("\n" + "=" * 70 + "\n")

    def generate_csv_report(self, output_path: Path) -> None:
        """Generate CSV file with aggregated BOM.

        Args:
            output_path: Path to save CSV file
        """
        import csv

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Access Points BOM
            writer.writerow(["Aggregated BOM - Access Points"])
            writer.writerow(["Quantity", "Vendor", "Model"])

            if self.ap_by_vendor_model:
                sorted_items = sorted(
                    self.ap_by_vendor_model.items(), key=lambda x: x[1], reverse=True
                )

                for (vendor, model), count in sorted_items:
                    writer.writerow([count, vendor, model])

                writer.writerow([])
                writer.writerow(["TOTAL", self.total_access_points, ""])
            else:
                writer.writerow(["No data", "", ""])

            # External Antennas BOM
            if self.antenna_by_model:
                writer.writerow([])
                writer.writerow(["Aggregated BOM - External Antennas"])
                writer.writerow(["Quantity", "Model"])

                sorted_antennas = sorted(
                    self.antenna_by_model.items(), key=lambda x: x[1], reverse=True
                )

                for model, count in sorted_antennas:
                    writer.writerow([count, model])

                writer.writerow([])
                writer.writerow(["TOTAL", self.total_antennas])

            # Batch statistics
            writer.writerow([])
            writer.writerow(["Batch Statistics"])
            writer.writerow(["Total Projects", self.total_projects])
            writer.writerow(["Successful", self.successful_projects])
            writer.writerow(["Failed", self.failed_projects])
            writer.writerow(["Total Time (s)", f"{self.total_processing_time:.1f}"])

            if self.successful_projects > 0:
                avg_time = self.total_processing_time / self.successful_projects
                writer.writerow(["Avg Time/Project (s)", f"{avg_time:.1f}"])

    def generate_reports(self, output_dir: Path) -> list[Path]:
        """Generate all aggregated reports.

        Args:
            output_dir: Base output directory

        Returns:
            List of generated file paths
        """
        summary_dir = output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Text summary
        summary_path = summary_dir / "batch_summary.txt"
        self.generate_text_summary(summary_path)
        generated_files.append(summary_path)
        logger.info(f"Generated text summary: {summary_path}")

        # CSV aggregate BOM
        csv_path = summary_dir / "batch_aggregate.csv"
        self.generate_csv_report(csv_path)
        generated_files.append(csv_path)
        logger.info(f"Generated CSV aggregate: {csv_path}")

        return generated_files


class BatchProcessor:
    """Handles batch processing of multiple .esx files."""

    def __init__(
        self,
        files: list[Path],
        output_dir: Path,
        parallel_workers: int = 1,
        continue_on_error: bool = True,
        console: Console | None = None,
    ):
        """Initialize batch processor.

        Args:
            files: List of .esx files to process
            output_dir: Base output directory for batch results
            parallel_workers: Number of parallel workers (1 = sequential)
            continue_on_error: Continue processing if a file fails
            console: Rich console for output (optional)
        """
        self.files = files
        self.output_dir = output_dir
        self.parallel_workers = max(1, parallel_workers)
        self.continue_on_error = continue_on_error
        self.console = console if RICH_AVAILABLE else None

        self.aggregated_report = AggregatedReport()
        self.error_log_path = output_dir / "summary" / "batch_errors.log"

    def _extract_project_data(self, esx_file: Path, output_dir: Path) -> dict[str, Any]:
        """Extract project data from generated CSV files.

        Args:
            esx_file: Original .esx file path
            output_dir: Output directory where CSV files were generated

        Returns:
            Dictionary with access_points and antennas lists
        """
        import csv
        from pathlib import Path

        project_data = {"access_points": [], "antennas": []}

        # Try to find the CSV file - it might have different name encodings
        csv_files = list(output_dir.glob("*_access_points.csv"))

        if not csv_files:
            logger.warning(f"No CSV files found in {output_dir} for {esx_file.name}")
            return project_data

        # Read the first access points CSV file
        csv_file = csv_files[0]

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                # Skip comment lines that start with #
                lines = [line for line in f if not line.strip().startswith("#")]
                reader = csv.DictReader(lines)
                for row in reader:
                    if row.get("Vendor") and row.get("Model"):
                        # Parse quantity as integer
                        quantity = int(row.get("Quantity", "1"))
                        project_data["access_points"].append(
                            {
                                "vendor": row.get("Vendor", "Unknown"),
                                "model": row.get("Model", "Unknown"),
                                "quantity": quantity,
                            }
                        )
        except Exception as e:
            logger.error(f"Failed to read CSV {csv_file}: {e}")

        # Try to read antennas CSV
        antenna_files = list(output_dir.glob("*_antennas.csv"))
        if antenna_files:
            try:
                with open(antenna_files[0], "r", encoding="utf-8") as f:
                    # Skip comment lines that start with #
                    lines = [line for line in f if not line.strip().startswith("#")]
                    reader = csv.DictReader(lines)
                    for row in reader:
                        # For now, treat all antennas in the CSV as external
                        # (Ekahau only exports external antennas to the antennas.csv)
                        antenna_model = row.get("Antenna Model", "")
                        if antenna_model:
                            quantity = int(row.get("Quantity", "1"))
                            project_data["antennas"].append(
                                {
                                    "antenna_model": antenna_model,
                                    "quantity": quantity,
                                    "is_external": True,
                                }
                            )
            except Exception as e:
                logger.error(f"Failed to read antennas CSV: {e}")

        return project_data

    def process_file(
        self, esx_file: Path, process_function: callable, **process_kwargs
    ) -> BatchResult:
        """Process a single .esx file and return result.

        Args:
            esx_file: Path to .esx file
            process_function: Function to call for processing
            **process_kwargs: Additional kwargs for process_function

        Returns:
            BatchResult with processing outcome
        """
        start_time = time.time()
        result = BatchResult(
            filename=esx_file.name,
            success=False,
            processing_time=0.0,
        )

        try:
            # Create unique subdirectory for this project
            # Use sanitized filename (without .esx extension) as subdirectory name
            project_name = esx_file.stem  # filename without extension
            project_output_dir = self.output_dir / project_name
            project_output_dir.mkdir(parents=True, exist_ok=True)

            # Override output_dir in process_kwargs
            process_kwargs_copy = process_kwargs.copy()
            process_kwargs_copy["output_dir"] = project_output_dir

            # Call the processing function
            exit_code = process_function(esx_file=esx_file, **process_kwargs_copy)

            processing_time = time.time() - start_time
            result.processing_time = processing_time
            result.success = exit_code == 0

            if exit_code == 0:
                # Extract project data from generated files for aggregation
                project_data = self._extract_project_data(esx_file, project_output_dir)
                result.project_data = project_data

                # Sum up quantities for accurate counts
                access_points = project_data.get("access_points", [])
                result.access_points_count = sum(ap.get("quantity", 1) for ap in access_points)

                antennas = project_data.get("antennas", [])
                result.antennas_count = sum(antenna.get("quantity", 1) for antenna in antennas)
            else:
                result.error_message = f"Process returned non-zero exit code: {exit_code}"

        except Exception as e:
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            result.error_message = str(e)
            logger.error(f"Failed to process {esx_file.name}: {e}")

        return result

    def process_sequential(self, process_function: callable, **process_kwargs) -> AggregatedReport:
        """Process files sequentially with progress tracking.

        Args:
            process_function: Function to call for each file
            **process_kwargs: Additional kwargs for process_function

        Returns:
            AggregatedReport with batch results
        """
        total_files = len(self.files)

        if RICH_AVAILABLE and self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("[cyan]Processing projects...", total=total_files)

                for esx_file in self.files:
                    progress.update(task, description=f"[cyan]Processing: {esx_file.name}")

                    result = self.process_file(esx_file, process_function, **process_kwargs)
                    self.aggregated_report.add_result(result)

                    if not result.success:
                        self._log_error(result)
                        if not self.continue_on_error:
                            break

                    progress.advance(task)
        else:
            # Fallback without Rich
            for idx, esx_file in enumerate(self.files, 1):
                logger.info(f"Processing {idx}/{total_files}: {esx_file.name}")

                result = self.process_file(esx_file, process_function, **process_kwargs)
                self.aggregated_report.add_result(result)

                if not result.success:
                    self._log_error(result)
                    if not self.continue_on_error:
                        break

        return self.aggregated_report

    def process_parallel(self, process_function: callable, **process_kwargs) -> AggregatedReport:
        """Process files in parallel with progress tracking.

        Args:
            process_function: Function to call for each file
            **process_kwargs: Additional kwargs for process_function

        Returns:
            AggregatedReport with batch results
        """
        total_files = len(self.files)

        if RICH_AVAILABLE and self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Processing {total_files} projects ({self.parallel_workers} workers)...",
                    total=total_files,
                )

                with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
                    # Submit all tasks
                    future_to_file = {
                        executor.submit(
                            self.process_file, esx_file, process_function, **process_kwargs
                        ): esx_file
                        for esx_file in self.files
                    }

                    # Process results as they complete
                    for future in as_completed(future_to_file):
                        esx_file = future_to_file[future]
                        try:
                            result = future.result()
                            self.aggregated_report.add_result(result)

                            if not result.success:
                                self._log_error(result)
                        except Exception as e:
                            logger.error(f"Unexpected error processing {esx_file.name}: {e}")
                            result = BatchResult(
                                filename=esx_file.name,
                                success=False,
                                processing_time=0.0,
                                error_message=str(e),
                            )
                            self.aggregated_report.add_result(result)
                            self._log_error(result)

                        progress.advance(task)
        else:
            # Fallback without Rich
            with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
                futures = [
                    executor.submit(self.process_file, esx_file, process_function, **process_kwargs)
                    for esx_file in self.files
                ]

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        self.aggregated_report.add_result(result)

                        if not result.success:
                            self._log_error(result)
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")

        return self.aggregated_report

    def process(self, process_function: callable, **process_kwargs) -> AggregatedReport:
        """Process all files (sequential or parallel based on workers).

        Args:
            process_function: Function to call for each file
            **process_kwargs: Additional kwargs for process_function

        Returns:
            AggregatedReport with batch results
        """
        # Ensure output directory exists
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)

        # Choose processing method
        if self.parallel_workers > 1:
            return self.process_parallel(process_function, **process_kwargs)
        else:
            return self.process_sequential(process_function, **process_kwargs)

    def _log_error(self, result: BatchResult) -> None:
        """Log error to batch_errors.log file."""
        try:
            self.error_log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.error_log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n[{timestamp}] {result.filename}\n")
                if result.error_message:
                    f.write(f"  Error: {result.error_message}\n")
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")

    def print_summary(self) -> None:
        """Print batch processing summary."""
        report = self.aggregated_report

        if RICH_AVAILABLE and self.console:
            self.console.print(f"\n[bold blue]{'='*60}[/bold blue]")

            # Summary table
            summary_table = report.get_summary_table()
            if summary_table:
                self.console.print(summary_table)

            # BOM table
            if report.successful_projects > 0:
                self.console.print()
                bom_table = report.get_bom_table()
                if bom_table:
                    self.console.print(bom_table)

            # Failed files
            if report.failed_projects > 0:
                self.console.print(
                    f"\n[bold red]Failed Files ({report.failed_projects}):[/bold red]"
                )
                for result in report.project_results:
                    if not result.success:
                        self.console.print(f"  [red]✗[/red] {result.filename}")
                        if result.error_message:
                            self.console.print(f"    [dim]{result.error_message}[/dim]")

                self.console.print(f"\n[yellow]Errors logged to:[/yellow] {self.error_log_path}")

            self.console.print(f"[bold blue]{'='*60}[/bold blue]\n")
        else:
            # Fallback without Rich
            print(f"\n{'='*60}")
            print(f"Batch Processing Summary")
            print("=" * 60)
            print(f"Total Projects: {report.total_projects}")
            print(f"Successful: {report.successful_projects}")
            print(f"Failed: {report.failed_projects}")
            print(f"Total Time: {report.total_processing_time:.1f}s")

            if report.successful_projects > 0:
                avg_time = report.total_processing_time / report.successful_projects
                print(f"Avg Time/Project: {avg_time:.1f}s")

            print(f"\nTotal Access Points: {report.total_access_points}")
            print(f"Total Antennas: {report.total_antennas}")

            if report.failed_projects > 0:
                print(f"\nFailed files: {report.failed_projects}")
                print(f"Errors logged to: {self.error_log_path}")

            print("=" * 60 + "\n")


def filter_files(
    files: list[Path],
    include_pattern: str | None = None,
    exclude_pattern: str | None = None,
) -> list[Path]:
    """Filter files by include/exclude patterns.

    Args:
        files: List of file paths
        include_pattern: Glob pattern to include (e.g., "*office*.esx")
        exclude_pattern: Glob pattern to exclude (e.g., "*backup*.esx")

    Returns:
        Filtered list of file paths
    """
    import fnmatch

    filtered = files

    # Apply include filter
    if include_pattern:
        filtered = [f for f in filtered if fnmatch.fnmatch(f.name, include_pattern)]
        logger.info(f"Include filter '{include_pattern}': {len(filtered)} files matched")

    # Apply exclude filter
    if exclude_pattern:
        original_count = len(filtered)
        filtered = [f for f in filtered if not fnmatch.fnmatch(f.name, exclude_pattern)]
        excluded_count = original_count - len(filtered)
        logger.info(f"Exclude filter '{exclude_pattern}': {excluded_count} files excluded")

    return filtered
