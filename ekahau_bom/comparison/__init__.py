"""Project version comparison module.

This module provides functionality for comparing two Ekahau project files (.esx)
to identify changes in AP inventory, placement, configuration, and metadata.
"""

from ekahau_bom.comparison.models import (
    APChange,
    ChangeStatus,
    ComparisonResult,
    FieldChange,
    InventoryChange,
    MetadataChange,
)
from ekahau_bom.comparison.engine import ComparisonEngine
from ekahau_bom.comparison.visual_diff import VisualDiffGenerator
from ekahau_bom.comparison.exporters import (
    export_comparison,
    CSVComparisonExporter,
    ExcelComparisonExporter,
    HTMLComparisonExporter,
    JSONComparisonExporter,
    PDFComparisonExporter,
)

__all__ = [
    # Models
    "APChange",
    "ChangeStatus",
    "ComparisonResult",
    "FieldChange",
    "InventoryChange",
    "MetadataChange",
    # Engine
    "ComparisonEngine",
    # Visual diff
    "VisualDiffGenerator",
    # Exporters
    "export_comparison",
    "CSVComparisonExporter",
    "ExcelComparisonExporter",
    "HTMLComparisonExporter",
    "JSONComparisonExporter",
    "PDFComparisonExporter",
]
