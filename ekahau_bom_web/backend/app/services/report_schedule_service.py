"""
Report Schedule Service - Generate scheduled aggregated reports for management.

This service provides functionality to:
- Generate aggregated BOM reports across all batches
- Time-based filtering (last week/month/quarter/year)
- Vendor/model distribution analysis
- Cost trends over time
- Export to PDF/Excel formats
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
from uuid import UUID
import csv
import io

from ..models import BatchMetadata, BatchStatus
from .batch_service import BatchService
from .storage_service import StorageService

logger = logging.getLogger(__name__)


class TimeRange:
    """Time range for report filtering."""

    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class AggregatedReportData:
    """Aggregated report data across multiple batches."""

    def __init__(self):
        self.total_batches: int = 0
        self.total_projects: int = 0
        self.successful_projects: int = 0
        self.failed_projects: int = 0
        self.total_access_points: int = 0
        self.total_antennas: int = 0

        # Aggregated BOM: vendor|model -> quantity
        self.ap_by_vendor_model: Dict[str, int] = defaultdict(int)
        self.antenna_by_model: Dict[str, int] = defaultdict(int)

        # Time-based metrics
        self.batches_by_date: Dict[str, int] = defaultdict(int)  # date -> count
        self.aps_by_date: Dict[str, int] = defaultdict(int)  # date -> total APs

        # Date range
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_batches": self.total_batches,
                "total_projects": self.total_projects,
                "successful_projects": self.successful_projects,
                "failed_projects": self.failed_projects,
                "total_access_points": self.total_access_points,
                "total_antennas": self.total_antennas,
            },
            "equipment": {
                "access_points_by_vendor_model": dict(self.ap_by_vendor_model),
                "antennas_by_model": dict(self.antenna_by_model),
            },
            "trends": {
                "batches_by_date": dict(self.batches_by_date),
                "access_points_by_date": dict(self.aps_by_date),
            },
            "date_range": {
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
            },
        }


class ReportScheduleService:
    """
    Service for generating scheduled aggregated reports.

    This service analyzes multiple batches and generates comprehensive
    reports for management with vendor/model distribution, cost trends,
    and time-based analytics.
    """

    def __init__(self, batch_service: BatchService, storage_service: StorageService):
        self.batch_service = batch_service
        self.storage_service = storage_service

    def get_date_range(
        self,
        time_range: str,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> tuple[datetime, datetime]:
        """
        Calculate date range based on time range parameter.

        Args:
            time_range: Time range identifier (last_week, last_month, etc.)
            custom_start: Custom start date (for custom range)
            custom_end: Custom end date (for custom range)

        Returns:
            Tuple of (start_date, end_date) as timezone-aware datetimes
        """
        from datetime import UTC

        now = datetime.now(UTC)

        if time_range == TimeRange.LAST_WEEK:
            start_date = now - timedelta(days=7)
            end_date = now
        elif time_range == TimeRange.LAST_MONTH:
            start_date = now - timedelta(days=30)
            end_date = now
        elif time_range == TimeRange.LAST_QUARTER:
            start_date = now - timedelta(days=90)
            end_date = now
        elif time_range == TimeRange.LAST_YEAR:
            start_date = now - timedelta(days=365)
            end_date = now
        elif time_range == TimeRange.CUSTOM and custom_start and custom_end:
            start_date = custom_start
            end_date = custom_end
        else:
            # Default to last month
            start_date = now - timedelta(days=30)
            end_date = now

        return start_date, end_date

    def generate_aggregated_report(
        self,
        time_range: str = TimeRange.LAST_MONTH,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
        status_filter: Optional[List[BatchStatus]] = None,
    ) -> AggregatedReportData:
        """
        Generate aggregated report across all batches.

        Args:
            time_range: Time range for filtering batches
            custom_start: Custom start date (for custom range)
            custom_end: Custom end date (for custom range)
            status_filter: Optional list of batch statuses to include

        Returns:
            AggregatedReportData with all metrics
        """
        logger.info(
            f"[ReportScheduleService] Generating aggregated report for time range: {time_range}"
        )

        start_date, end_date = self.get_date_range(time_range, custom_start, custom_end)
        report_data = AggregatedReportData()
        report_data.start_date = start_date
        report_data.end_date = end_date

        # Get all batches
        all_batches = self.batch_service.list_batches()

        # Filter by date range and status
        filtered_batches: List[BatchMetadata] = []
        for batch in all_batches:
            # batch.created_date is already a datetime object
            batch_date = (
                batch.created_date
                if isinstance(batch.created_date, datetime)
                else datetime.fromisoformat(batch.created_date)
            )

            # Check date range
            if not (start_date <= batch_date <= end_date):
                continue

            # Check status filter
            if status_filter and batch.status not in status_filter:
                continue

            filtered_batches.append(batch)

        logger.info(f"[ReportScheduleService] Found {len(filtered_batches)} batches in date range")

        # Aggregate data from filtered batches
        for batch in filtered_batches:
            report_data.total_batches += 1

            # Aggregate batch statistics
            if batch.statistics:
                report_data.total_projects += batch.statistics.total_projects
                report_data.successful_projects += batch.statistics.successful_projects
                report_data.failed_projects += batch.statistics.failed_projects
                report_data.total_access_points += batch.statistics.total_access_points
                report_data.total_antennas += batch.statistics.total_antennas

                # Aggregate equipment by vendor/model
                for vendor_model, quantity in batch.statistics.ap_by_vendor_model.items():
                    report_data.ap_by_vendor_model[vendor_model] += quantity

                for model, quantity in batch.statistics.antenna_by_model.items():
                    report_data.antenna_by_model[model] += quantity

            # Track batches and APs by date
            batch_date_obj = (
                batch.created_date
                if isinstance(batch.created_date, datetime)
                else datetime.fromisoformat(batch.created_date)
            )
            batch_date_str = batch_date_obj.strftime("%Y-%m-%d")
            report_data.batches_by_date[batch_date_str] += 1
            if batch.statistics:
                report_data.aps_by_date[batch_date_str] += batch.statistics.total_access_points

        logger.info(
            f"[ReportScheduleService] Report generated: {report_data.total_batches} batches, "
            f"{report_data.total_projects} projects, {report_data.total_access_points} APs"
        )

        return report_data

    def export_to_csv(self, report_data: AggregatedReportData) -> str:
        """
        Export aggregated report to CSV format.

        Args:
            report_data: Aggregated report data

        Returns:
            CSV content as string
        """
        output = io.StringIO()

        # Summary section
        output.write("AGGREGATED BOM REPORT\n")
        output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write(
            f"Date Range: {report_data.start_date.strftime('%Y-%m-%d')} to {report_data.end_date.strftime('%Y-%m-%d')}\n"
        )
        output.write("\n")

        output.write("SUMMARY\n")
        output.write(f"Total Batches,{report_data.total_batches}\n")
        output.write(f"Total Projects,{report_data.total_projects}\n")
        output.write(f"Successful Projects,{report_data.successful_projects}\n")
        output.write(f"Failed Projects,{report_data.failed_projects}\n")
        output.write(f"Total Access Points,{report_data.total_access_points}\n")
        output.write(f"Total Antennas,{report_data.total_antennas}\n")
        output.write("\n")

        # Access Points by Vendor/Model
        output.write("ACCESS POINTS BY VENDOR/MODEL\n")
        output.write("Vendor|Model,Quantity\n")
        for vendor_model, quantity in sorted(
            report_data.ap_by_vendor_model.items(), key=lambda x: x[1], reverse=True
        ):
            output.write(f"{vendor_model},{quantity}\n")
        output.write("\n")

        # Antennas by Model
        output.write("ANTENNAS BY MODEL\n")
        output.write("Model,Quantity\n")
        for model, quantity in sorted(
            report_data.antenna_by_model.items(), key=lambda x: x[1], reverse=True
        ):
            output.write(f"{model},{quantity}\n")
        output.write("\n")

        # Trends by date
        output.write("BATCHES BY DATE\n")
        output.write("Date,Batches,Access Points\n")
        for date in sorted(report_data.batches_by_date.keys()):
            batches = report_data.batches_by_date[date]
            aps = report_data.aps_by_date.get(date, 0)
            output.write(f"{date},{batches},{aps}\n")

        return output.getvalue()

    def export_to_text(self, report_data: AggregatedReportData) -> str:
        """
        Export aggregated report to text format.

        Args:
            report_data: Aggregated report data

        Returns:
            Text content as string
        """
        lines = []

        lines.append("=" * 80)
        lines.append("AGGREGATED BOM REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(
            f"Date Range: {report_data.start_date.strftime('%Y-%m-%d')} to {report_data.end_date.strftime('%Y-%m-%d')}"
        )
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Batches:         {report_data.total_batches:>10}")
        lines.append(f"Total Projects:        {report_data.total_projects:>10}")
        lines.append(f"Successful Projects:   {report_data.successful_projects:>10}")
        lines.append(f"Failed Projects:       {report_data.failed_projects:>10}")
        lines.append(f"Total Access Points:   {report_data.total_access_points:>10}")
        lines.append(f"Total Antennas:        {report_data.total_antennas:>10}")
        lines.append("")

        lines.append("ACCESS POINTS BY VENDOR/MODEL")
        lines.append("-" * 80)
        for vendor_model, quantity in sorted(
            report_data.ap_by_vendor_model.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"{vendor_model:<50} {quantity:>10}")
        lines.append("")

        lines.append("ANTENNAS BY MODEL")
        lines.append("-" * 80)
        for model, quantity in sorted(
            report_data.antenna_by_model.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"{model:<50} {quantity:>10}")
        lines.append("")

        lines.append("TRENDS BY DATE")
        lines.append("-" * 80)
        lines.append(f"{'Date':<15} {'Batches':>10} {'Access Points':>15}")
        lines.append("-" * 80)
        for date in sorted(report_data.batches_by_date.keys()):
            batches = report_data.batches_by_date[date]
            aps = report_data.aps_by_date.get(date, 0)
            lines.append(f"{date:<15} {batches:>10} {aps:>15}")

        lines.append("=" * 80)

        return "\n".join(lines)


# Global instance (singleton)
_report_schedule_service_instance: Optional[ReportScheduleService] = None


def get_report_schedule_service(
    batch_service: BatchService, storage_service: StorageService
) -> ReportScheduleService:
    """Get or create the global report schedule service instance."""
    global _report_schedule_service_instance
    if _report_schedule_service_instance is None:
        _report_schedule_service_instance = ReportScheduleService(batch_service, storage_service)
    return _report_schedule_service_instance
