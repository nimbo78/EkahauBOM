"""Test report generation directly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.batch_service import batch_service
from app.services.storage_service import StorageService
from app.services.report_schedule_service import get_report_schedule_service

# Initialize services
storage_service = StorageService()
report_service = get_report_schedule_service(batch_service, storage_service)

try:
    # Generate report
    print("Generating aggregated report...")
    report_data = report_service.generate_aggregated_report(time_range="last_month")

    print(f"\nReport generated successfully!")
    print(f"Total batches: {report_data.total_batches}")
    print(f"Total projects: {report_data.total_projects}")
    print(f"Total APs: {report_data.total_access_points}")
    print(f"Total antennas: {report_data.total_antennas}")

    print(f"\nVendor/Model distribution:")
    for vendor_model, quantity in list(report_data.ap_by_vendor_model.items())[:5]:
        print(f"  {vendor_model}: {quantity}")

except Exception as e:
    print(f"Error generating report: {e}")
    import traceback

    traceback.print_exc()
