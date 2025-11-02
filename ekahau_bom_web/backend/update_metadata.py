"""Update metadata for existing projects to include new fields."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.storage import storage_service
from app.services.processor import ProcessorService

processor_service = ProcessorService(storage=storage_service)


async def update_project_metadata(project_id: str):
    """Update metadata for a specific project."""
    # Load existing metadata
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        print(f"Project {project_id} not found")
        return

    print(f"Updating metadata for project: {metadata.project_name}")
    print(f"Status: {metadata.processing_status}")

    # Get paths
    project_dir = storage_service.projects_dir / project_id
    original_file = project_dir / "original.esx"

    if not original_file.exists():
        print(f"Original file not found: {original_file}")
        return

    # Extract project metadata from .esx
    print("\nExtracting metadata from .esx file...")
    await processor_service._extract_project_metadata(
        project_id, original_file, metadata
    )

    # Extract summary from JSON report if available
    if metadata.reports_dir:
        reports_dir = storage_service.projects_dir / metadata.reports_dir
        if reports_dir.exists():
            print("Extracting summary from JSON report...")
            await processor_service._extract_report_summary(
                project_id, reports_dir, metadata
            )

    # Save updated metadata
    storage_service.save_metadata(project_id, metadata)

    print("\n[SUCCESS] Metadata updated successfully!")
    print(f"Customer: {metadata.customer}")
    print(f"Location: {metadata.location}")
    print(f"Responsible: {metadata.responsible_person}")
    print(f"Total Antennas: {metadata.total_antennas}")
    print(f"Unique Vendors: {metadata.unique_vendors}")
    print(f"Vendors: {metadata.vendors}")
    print(f"Unique Colors: {metadata.unique_colors}")
    print(f"Floors: {metadata.floors}")


async def update_all_projects():
    """Update metadata for all projects."""
    from app.services.index import index_service

    # Load index
    index_service.load_from_disk()
    projects = index_service.list_all()

    print(f"Found {len(projects)} projects")

    for project in projects:
        print(f"\n{'='*60}")
        await update_project_metadata(str(project.project_id))

        # Update in index
        updated_metadata = storage_service.load_metadata(str(project.project_id))
        if updated_metadata:
            index_service.add(updated_metadata)

    # Save updated index
    index_service.save_to_disk()
    print(f"\n{'='*60}")
    print("[SUCCESS] All projects updated!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Update specific project
        project_id = sys.argv[1]
        asyncio.run(update_project_metadata(project_id))
    else:
        # Update all projects
        asyncio.run(update_all_projects())
