# Extending EkahauBOM

Comprehensive guide for extending EkahauBOM with new exporters, processors, and features.

**English** | [Русский](EXTENDING.ru.md)

## Table of Contents

- [Adding a New Exporter](#adding-a-new-exporter)
- [Adding a New Processor](#adding-a-new-processor)
- [Adding New Analytics](#adding-new-analytics)
- [Adding CLI Options](#adding-cli-options)
- [Best Practices](#best-practices)

---

## Adding a New Exporter

Exporters convert `ProjectData` into various output formats (CSV, Excel, HTML, JSON, PDF, etc.).

### Architecture Overview

```
ekahau_bom/exporters/
├── base.py              # BaseExporter abstract class
├── csv_exporter.py      # CSV implementation
├── excel_exporter.py    # Excel implementation
├── html_exporter.py     # HTML implementation
├── json_exporter.py     # JSON implementation
└── pdf_exporter.py      # PDF implementation
```

**BaseExporter** (`base.py`) provides:
- Abstract `export()` method
- Abstract `format_name` property
- Filename sanitization (`_sanitize_filename`)
- Output filename generation (`_get_output_filename`)

### Step-by-Step Guide

#### 1. Create Exporter Class

Create a new file `ekahau_bom/exporters/xml_exporter.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""XML exporter for Ekahau project data."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from .base import BaseExporter
from ..models import ProjectData, AccessPoint

logger = logging.getLogger(__name__)


class XMLExporter(BaseExporter):
    """Export project data to XML format."""

    @property
    def format_name(self) -> str:
        """Return human-readable format name."""
        return "XML"

    def export(self, project_data: ProjectData) -> list[Path]:
        """Export project data to XML file.

        Args:
            project_data: Processed project data to export

        Returns:
            List containing path to created XML file

        Raises:
            IOError: If file write fails
        """
        logger.info(f"Exporting to {self.format_name} format...")

        # Create XML structure
        root = ET.Element("ekahau_project")

        # Add metadata
        if project_data.metadata:
            metadata_elem = ET.SubElement(root, "metadata")
            ET.SubElement(metadata_elem, "name").text = project_data.metadata.project_name
            ET.SubElement(metadata_elem, "customer").text = project_data.metadata.customer_name

        # Add access points
        aps_elem = ET.SubElement(root, "access_points")
        for ap in project_data.access_points:
            ap_elem = ET.SubElement(aps_elem, "access_point")
            ET.SubElement(ap_elem, "vendor").text = ap.vendor
            ET.SubElement(ap_elem, "model").text = ap.model
            ET.SubElement(ap_elem, "floor").text = ap.floor
            ET.SubElement(ap_elem, "color").text = ap.color
            ET.SubElement(ap_elem, "quantity").text = str(ap.quantity)

        # Create XML tree
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")  # Pretty print (Python 3.9+)

        # Write to file
        output_file = self._get_output_filename(
            project_data.metadata.project_name if project_data.metadata else "project",
            ".xml"
        )
        tree.write(output_file, encoding="utf-8", xml_declaration=True)

        logger.info(f"XML export completed: {output_file}")
        return [output_file]
```

#### 2. Update __init__.py

Add your exporter to `ekahau_bom/exporters/__init__.py`:

```python
from .base import BaseExporter
from .csv_exporter import CSVExporter
from .excel_exporter import ExcelExporter
from .html_exporter import HTMLExporter
from .json_exporter import JSONExporter
from .pdf_exporter import PDFExporter
from .xml_exporter import XMLExporter  # Add new exporter

__all__ = [
    "BaseExporter",
    "CSVExporter",
    "ExcelExporter",
    "HTMLExporter",
    "JSONExporter",
    "PDFExporter",
    "XMLExporter",  # Add to exports
]
```

#### 3. Register in CLI

Update `ekahau_bom/cli.py` to include the new exporter:

```python
# Import at the top
from ekahau_bom.exporters import (
    CSVExporter,
    ExcelExporter,
    HTMLExporter,
    JSONExporter,
    PDFExporter,
    XMLExporter,  # Add import
)

# Register in EXPORTERS dictionary
EXPORTERS = {
    "csv": CSVExporter,
    "excel": ExcelExporter,
    "html": HTMLExporter,
    "json": JSONExporter,
    "pdf": PDFExporter,
    "xml": XMLExporter,  # Register exporter
}

# Add CLI option
@click.option(
    "--xml",
    "export_xml",
    is_flag=True,
    help="Export to XML format",
)
def main(
    esx_file: str,
    output_dir: str,
    export_csv: bool,
    export_excel: bool,
    export_html: bool,
    export_json: bool,
    export_pdf: bool,
    export_xml: bool,  # Add parameter
    # ... other parameters
):
    # In the export logic:
    if export_xml:
        exporter = XMLExporter(output_dir_path)
        xml_files = exporter.export(project_data)
        all_files.extend(xml_files)
```

#### 4. Write Tests

Create `tests/test_xml_exporter.py`:

```python
import pytest
from pathlib import Path
from xml.etree import ElementTree as ET

from ekahau_bom.exporters.xml_exporter import XMLExporter
from ekahau_bom.models import ProjectData, AccessPoint, Metadata


@pytest.fixture
def sample_project_data():
    """Create sample project data for testing."""
    return ProjectData(
        metadata=Metadata(
            project_name="Test Project",
            customer_name="Test Customer"
        ),
        access_points=[
            AccessPoint(
                vendor="Cisco",
                model="AIR-AP3802I-B-K9",
                floor="Floor 1",
                color="Yellow",
                quantity=2
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-515",
                floor="Floor 2",
                color="Red",
                quantity=1
            ),
        ],
        antennas=[],
        radios=[]
    )


class TestXMLExporter:
    """Test XMLExporter functionality."""

    def test_export_creates_file(self, sample_project_data, tmp_path):
        """Test that XML export creates a file."""
        exporter = XMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()
        assert files[0].suffix == ".xml"

    def test_xml_structure(self, sample_project_data, tmp_path):
        """Test that XML has correct structure."""
        exporter = XMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        # Parse XML
        tree = ET.parse(files[0])
        root = tree.getroot()

        assert root.tag == "ekahau_project"
        assert root.find("metadata") is not None
        assert root.find("access_points") is not None

    def test_xml_content(self, sample_project_data, tmp_path):
        """Test that XML contains correct data."""
        exporter = XMLExporter(tmp_path)
        files = exporter.export(sample_project_data)

        tree = ET.parse(files[0])
        root = tree.getroot()

        # Check metadata
        metadata = root.find("metadata")
        assert metadata.find("name").text == "Test Project"
        assert metadata.find("customer").text == "Test Customer"

        # Check access points
        aps = root.find("access_points").findall("access_point")
        assert len(aps) == 2

        ap1 = aps[0]
        assert ap1.find("vendor").text == "Cisco"
        assert ap1.find("model").text == "AIR-AP3802I-B-K9"
        assert ap1.find("quantity").text == "2"

    def test_format_name(self, tmp_path):
        """Test format_name property."""
        exporter = XMLExporter(tmp_path)
        assert exporter.format_name == "XML"

    def test_empty_project_data(self, tmp_path):
        """Test export with empty project data."""
        empty_data = ProjectData(
            metadata=None,
            access_points=[],
            antennas=[],
            radios=[]
        )

        exporter = XMLExporter(tmp_path)
        files = exporter.export(empty_data)

        assert len(files) == 1
        assert files[0].exists()
```

#### 5. Update Documentation

Add to README.md under "Multi-Format Export":
```markdown
- **XML**: Machine-readable XML format with schema validation
```

Add usage example:
```bash
ekahau-bom project.esx --xml
```

### Advanced Exporter Features

#### Adding Configuration Options

```python
class XMLExporter(BaseExporter):
    """Export with custom configuration."""

    def __init__(self, output_dir: Path, pretty_print: bool = True):
        """Initialize exporter with options.

        Args:
            output_dir: Output directory
            pretty_print: Whether to format XML with indentation
        """
        super().__init__(output_dir)
        self.pretty_print = pretty_print

    def export(self, project_data: ProjectData) -> list[Path]:
        # ... create tree

        if self.pretty_print:
            ET.indent(tree, space="  ")

        # ... write file
```

#### Handling Optional Dependencies

```python
try:
    import xmlschema
    HAS_SCHEMA_VALIDATION = True
except ImportError:
    HAS_SCHEMA_VALIDATION = False
    logger.warning("xmlschema not installed. Schema validation disabled.")

class XMLExporter(BaseExporter):
    def export(self, project_data: ProjectData) -> list[Path]:
        # ... create XML

        if HAS_SCHEMA_VALIDATION:
            self._validate_schema(output_file)

        return [output_file]
```

#### Multiple Output Files

```python
def export(self, project_data: ProjectData) -> list[Path]:
    """Export to multiple XML files."""
    files = []

    # Export access points
    ap_file = self._export_access_points(project_data.access_points)
    files.append(ap_file)

    # Export antennas
    antenna_file = self._export_antennas(project_data.antennas)
    files.append(antenna_file)

    return files
```

---

## Adding a New Processor

Processors extract and transform data from Ekahau .esx files into model objects.

### Architecture Overview

```
ekahau_bom/processors/
├── __init__.py
├── access_points.py      # AccessPoint processor
├── antennas.py           # Antenna processor
├── radios.py             # Radio processor
├── tags.py               # Tag processor
├── notes.py              # Notes processor
├── metadata.py           # Project metadata
└── network_settings.py   # Network settings
```

### Step-by-Step Guide

#### 1. Define Data Model

First, add your model to `ekahau_bom/models.py`:

```python
@dataclass
class Floor:
    """Floor plan information."""

    id: str
    name: str
    building_id: str
    image_path: str = ""
    width: float = 0.0
    height: float = 0.0
    scale: float = 1.0
```

#### 2. Create Processor Class

Create `ekahau_bom/processors/floors.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Floor processor for Ekahau project data."""

from __future__ import annotations

import logging
from typing import Any

from ..models import Floor

logger = logging.getLogger(__name__)


class FloorProcessor:
    """Process floor plan data from Ekahau project."""

    @staticmethod
    def process(
        floor_plans_data: list[dict[str, Any]],
        buildings_data: list[dict[str, Any]] = None,
        images_data: list[dict[str, Any]] = None
    ) -> list[Floor]:
        """Process floor plans into Floor objects.

        Args:
            floor_plans_data: Raw floor plans data from floorPlans.json
            buildings_data: Raw buildings data from buildings.json (optional)
            images_data: Raw images data from images.json (optional)

        Returns:
            List of processed Floor objects
        """
        logger.info(f"Processing {len(floor_plans_data)} floor plans...")

        floors = []

        # Create image ID to path mapping
        image_map = {}
        if images_data:
            for image in images_data:
                image_map[image.get("id")] = image.get("file_name", "")

        for floor_data in floor_plans_data:
            try:
                floor = FloorProcessor._process_single_floor(
                    floor_data,
                    image_map
                )
                floors.append(floor)
            except Exception as e:
                logger.error(f"Error processing floor: {e}")
                continue

        logger.info(f"Successfully processed {len(floors)} floors")
        return floors

    @staticmethod
    def _process_single_floor(
        floor_data: dict[str, Any],
        image_map: dict[str, str]
    ) -> Floor:
        """Process a single floor plan.

        Args:
            floor_data: Raw floor plan data
            image_map: Mapping of image IDs to file paths

        Returns:
            Processed Floor object
        """
        floor_id = floor_data.get("id", "")
        name = floor_data.get("name", "Unknown Floor")
        building_id = floor_data.get("buildingId", "")

        # Get image information
        image_id = floor_data.get("imageId")
        image_path = image_map.get(image_id, "") if image_id else ""

        # Get dimensions
        width = floor_data.get("width", 0.0)
        height = floor_data.get("height", 0.0)

        # Calculate scale (meters per pixel)
        scale_info = floor_data.get("scale", {})
        scale = scale_info.get("metersPerPixel", 1.0)

        return Floor(
            id=floor_id,
            name=name,
            building_id=building_id,
            image_path=image_path,
            width=width,
            height=height,
            scale=scale
        )
```

#### 3. Update CLI Integration

In `ekahau_bom/cli.py`, add floor processing:

```python
# Import processor
from ekahau_bom.processors import (
    AccessPointProcessor,
    AntennaProcessor,
    RadioProcessor,
    FloorProcessor,  # Add import
)

# In main function, process floors
def main(...):
    # ... existing code

    # Process floors
    floor_plans_data = parser.get_data("floorPlans")
    images_data = parser.get_data("images")
    floors = FloorProcessor.process(floor_plans_data, images_data=images_data)

    # Add to project data
    project_data = ProjectData(
        # ... existing fields
        floors=floors,  # Add floors
    )
```

#### 4. Write Tests

Create `tests/test_floors_processor.py`:

```python
import pytest
from ekahau_bom.processors.floors import FloorProcessor
from ekahau_bom.models import Floor


@pytest.fixture
def sample_floor_plans_data():
    """Sample floor plans data."""
    return [
        {
            "id": "floor-1",
            "name": "Floor 1",
            "buildingId": "building-1",
            "imageId": "image-1",
            "width": 1000.0,
            "height": 800.0,
            "scale": {"metersPerPixel": 0.05}
        },
        {
            "id": "floor-2",
            "name": "Floor 2",
            "buildingId": "building-1",
            "imageId": "image-2",
            "width": 1200.0,
            "height": 900.0,
            "scale": {"metersPerPixel": 0.04}
        }
    ]


@pytest.fixture
def sample_images_data():
    """Sample images data."""
    return [
        {"id": "image-1", "file_name": "floor1.png"},
        {"id": "image-2", "file_name": "floor2.png"}
    ]


class TestFloorProcessor:
    """Test FloorProcessor functionality."""

    def test_process_floors(self, sample_floor_plans_data, sample_images_data):
        """Test processing floor plans."""
        floors = FloorProcessor.process(
            sample_floor_plans_data,
            images_data=sample_images_data
        )

        assert len(floors) == 2
        assert all(isinstance(f, Floor) for f in floors)

    def test_floor_attributes(self, sample_floor_plans_data, sample_images_data):
        """Test floor attributes are correctly extracted."""
        floors = FloorProcessor.process(
            sample_floor_plans_data,
            images_data=sample_images_data
        )

        floor1 = floors[0]
        assert floor1.id == "floor-1"
        assert floor1.name == "Floor 1"
        assert floor1.building_id == "building-1"
        assert floor1.image_path == "floor1.png"
        assert floor1.width == 1000.0
        assert floor1.height == 800.0
        assert floor1.scale == 0.05

    def test_process_without_images(self, sample_floor_plans_data):
        """Test processing without images data."""
        floors = FloorProcessor.process(sample_floor_plans_data)

        assert len(floors) == 2
        assert floors[0].image_path == ""

    def test_process_empty_data(self):
        """Test processing empty floor plans data."""
        floors = FloorProcessor.process([])
        assert len(floors) == 0

    def test_process_malformed_data(self):
        """Test processing with malformed data."""
        malformed = [{"invalid": "data"}]
        floors = FloorProcessor.process(malformed)

        # Should handle gracefully, may return empty or partial results
        assert isinstance(floors, list)
```

---

## Adding New Analytics

Analytics functions provide statistical analysis and insights from the data.

### Example: Channel Overlap Analysis

Add to `ekahau_bom/analytics.py`:

```python
@staticmethod
def analyze_channel_overlap(radios: list[Radio]) -> dict[str, Any]:
    """Analyze channel overlap between radios.

    Identifies radios on the same or overlapping channels that might
    interfere with each other.

    Args:
        radios: List of Radio objects to analyze

    Returns:
        Dictionary with overlap analysis:
        - total_overlaps: Number of overlapping channel pairs
        - overlap_details: List of overlapping radio pairs
        - recommendations: Suggested channel changes
    """
    overlaps = []

    # Group radios by band
    radios_2ghz = [r for r in radios if r.band == "2.4 GHz"]
    radios_5ghz = [r for r in radios if r.band == "5 GHz"]

    # Check for overlaps in 2.4 GHz
    # Channels 1, 6, 11 don't overlap
    for i, radio1 in enumerate(radios_2ghz):
        for radio2 in radios_2ghz[i+1:]:
            if abs(radio1.channel - radio2.channel) < 5:
                overlaps.append({
                    "radio1": radio1.ap_name,
                    "radio2": radio2.ap_name,
                    "channel1": radio1.channel,
                    "channel2": radio2.channel,
                    "band": "2.4 GHz"
                })

    # Generate recommendations
    recommendations = []
    if overlaps:
        recommendations.append(
            "Consider using non-overlapping channels: 1, 6, 11 for 2.4 GHz"
        )

    return {
        "total_overlaps": len(overlaps),
        "overlap_details": overlaps,
        "recommendations": recommendations
    }
```

---

## Adding CLI Options

### Adding a Simple Flag

```python
@click.option(
    "--show-warnings",
    "show_warnings",
    is_flag=True,
    help="Display channel overlap warnings",
)
def main(..., show_warnings: bool):
    if show_warnings:
        # Perform overlap analysis
        overlap_data = RadioAnalytics.analyze_channel_overlap(radios)
        if overlap_data["total_overlaps"] > 0:
            click.echo(click.style(
                f"⚠️  Found {overlap_data['total_overlaps']} channel overlaps",
                fg="yellow"
            ))
```

### Adding an Option with Value

```python
@click.option(
    "--min-channel",
    "min_channel",
    type=int,
    default=1,
    help="Minimum 2.4 GHz channel to use (default: 1)",
)
def main(..., min_channel: int):
    # Use min_channel in analytics
    pass
```

---

## Best Practices

### Code Quality

1. **Type Hints**: Always use type hints
   ```python
   def process(data: dict[str, Any]) -> list[AccessPoint]:
       pass
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   def function(arg1: str, arg2: int) -> bool:
       """Short description.

       Longer description if needed.

       Args:
           arg1: Description of arg1
           arg2: Description of arg2

       Returns:
           Description of return value

       Raises:
           ValueError: When validation fails
       """
   ```

3. **Logging**: Use appropriate log levels
   ```python
   logger.debug("Detailed information for debugging")
   logger.info("General information")
   logger.warning("Warning message")
   logger.error("Error occurred but handled")
   ```

4. **Error Handling**: Handle exceptions gracefully
   ```python
   try:
       result = process_data(data)
   except KeyError as e:
       logger.error(f"Missing required field: {e}")
       return default_value
   except Exception as e:
       logger.exception(f"Unexpected error: {e}")
       raise
   ```

### Testing

1. **Test Coverage**: Aim for 80%+ on new code
2. **Test Organization**: Group related tests in classes
3. **Fixtures**: Use fixtures for common test data
4. **Edge Cases**: Test empty data, malformed data, None values

### Performance

1. **Avoid Loading Everything**: Process data as streams when possible
2. **Use Generators**: For large datasets
3. **Cache Expensive Operations**: Use `@lru_cache` where appropriate
4. **Profile Before Optimizing**: Use `cProfile` to identify bottlenecks

---

## Questions?

- **GitHub Discussions**: [Ask questions](https://github.com/nimbo78/EkahauBOM/discussions)
- **GitHub Issues**: [Report bugs](https://github.com/nimbo78/EkahauBOM/issues)
- **Developer Guide**: [docs/DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

---

**Happy coding!** 🚀
