# EkahauBOM Developer Guide

Guide for contributors and developers working on EkahauBOM.

**English** | [Русский](DEVELOPER_GUIDE.ru.md)

## Table of Contents

- [Getting Started](#getting-started)
- [Project Architecture](#project-architecture)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Adding Features](#adding-features)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- Python 3.7+
- Git
- pip and virtualenv (recommended)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/htechno/EkahauBOM.git
cd EkahauBOM

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

---

## Project Architecture

### Directory Structure

```
ekahau_bom/
├── cli.py              # Command-line interface (Click)
├── parser.py           # .esx file parser (ZIP + JSON)
├── models.py           # Data models (dataclasses)
├── constants.py        # Constants and defaults
├── utils.py            # Utility functions
├── filters.py          # Filtering logic
├── analytics.py        # Analytics and grouping
├── pricing.py          # Cost calculation
├── processors/         # Data processors
│   ├── access_points.py
│   ├── antennas.py
│   ├── radios.py
│   └── tags.py
└── exporters/          # Export formats
    ├── base.py         # Base exporter class
    ├── csv_exporter.py
    ├── excel_exporter.py
    ├── html_exporter.py
    └── json_exporter.py
```

### Key Components

**Parser** (`parser.py`)
- Handles .esx file reading (ZIP archives)
- Parses JSON files inside archive
- Context manager for resource cleanup

**Models** (`models.py`)
- Data classes for AccessPoint, Antenna, Radio, Tag, etc.
- Type-safe data structures
- Immutable where possible

**Processors** (`processors/`)
- Transform raw data into models
- Handle vendor-specific logic
- Tag processing for v10.2+

**Exporters** (`exporters/`)
- Base class with common functionality
- Format-specific implementations
- Consistent interface

**Analytics** (`analytics.py`)
- Grouping functions
- Statistical calculations
- Multi-dimensional analysis

---

## Code Style

### Python Standards

- **PEP 8** compliance
- **Type hints** for all functions
- **Docstrings** for all public APIs (Google style)
- **F-strings** for string formatting

### Example

```python
def process_access_points(
    access_points_data: dict[str, Any],
    floors: dict[str, Floor]
) -> list[AccessPoint]:
    """Process raw access points data into AccessPoint objects.

    Args:
        access_points_data: Raw access points data from parser
        floors: Dictionary mapping floor IDs to Floor objects

    Returns:
        List of processed AccessPoint objects

    Raises:
        ValueError: If data is malformed
    """
    # Implementation
```

### Tools

```bash
# Format code
black ekahau_bom/

# Lint
flake8 ekahau_bom/
pylint ekahau_bom/

# Type checking
mypy ekahau_bom/
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=ekahau_bom --cov-report=html

# Specific file
pytest tests/test_analytics.py -v

# Specific test
pytest tests/test_analytics.py::TestGroupingAnalytics::test_group_by_floor
```

### Writing Tests

**Structure:**
```python
import pytest
from ekahau_bom.models import AccessPoint

@pytest.fixture
def sample_aps():
    """Create sample access points for testing."""
    return [
        AccessPoint("Cisco", "C9120AXI", "Yellow", "Floor 1"),
        AccessPoint("Aruba", "AP-515", "Red", "Floor 2"),
    ]

class TestAnalytics:
    """Test analytics functionality."""

    def test_group_by_vendor(self, sample_aps):
        """Test grouping by vendor."""
        result = GroupingAnalytics.group_by_vendor(sample_aps)
        assert result["Cisco"] == 1
        assert result["Aruba"] == 1
```

**Coverage Goals:**
- New features: 80%+ coverage
- Critical paths: 95%+ coverage
- Current overall: 70%

---

## Adding Features

### Adding a New Exporter

1. **Create exporter class:**

```python
# ekahau_bom/exporters/pdf_exporter.py
from .base import BaseExporter
from ..models import ProjectData

class PDFExporter(BaseExporter):
    @property
    def format_name(self) -> str:
        return "PDF"

    def export(self, project_data: ProjectData) -> list[Path]:
        # Implementation
        pass
```

2. **Register in CLI:**

```python
# ekahau_bom/cli.py
EXPORTERS = {
    'csv': CSVExporter,
    'excel': ExcelExporter,
    'html': HTMLExporter,
    'json': JSONExporter,
    'pdf': PDFExporter,  # Add new exporter
}
```

3. **Add tests:**

```python
# tests/test_pdf_exporter.py
def test_pdf_export(sample_project_data, tmp_path):
    exporter = PDFExporter(tmp_path)
    files = exporter.export(sample_project_data)
    assert len(files) == 1
    assert files[0].suffix == '.pdf'
```

### Adding Analytics

1. **Add method to analytics.py:**

```python
@staticmethod
def analyze_channel_overlap(radios: list[Radio]) -> dict[str, Any]:
    """Analyze channel overlap between radios.

    Args:
        radios: List of radios to analyze

    Returns:
        Dictionary with overlap analysis
    """
    # Implementation
```

2. **Add tests:**

```python
def test_channel_overlap(sample_radios):
    result = RadioAnalytics.analyze_channel_overlap(sample_radios)
    assert "overlap_count" in result
```

3. **Integrate into exporters** (optional)

---

## Contributing

### Workflow

1. **Fork** the repository
2. **Create branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** with tests
4. **Run tests**: `pytest`
5. **Format code**: `black ekahau_bom/`
6. **Commit**: `git commit -m 'Add amazing feature'`
7. **Push**: `git push origin feature/amazing-feature`
8. **Open Pull Request**

### Pull Request Guidelines

**Title:**
- Clear, concise description
- Example: "Add PDF export support"

**Description:**
- What changes were made
- Why they were made
- How to test

**Checklist:**
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests passing
- [ ] Code formatted (black)
- [ ] Type hints added
- [ ] Docstrings added

### Commit Messages

Format:
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `style`: Formatting
- `perf`: Performance improvement

**Example:**
```
feat: Add PDF export support

- Implement PDFExporter class using WeasyPrint
- Add PDF template with custom styling
- Include charts in PDF output
- Add tests for PDF generation

Closes #42
```

---

## Architecture Decisions

### Why Dataclasses?

- Type-safe
- Immutable by default
- Auto-generated __init__, __repr__, etc.
- Easy to serialize

### Why Click for CLI?

- Excellent documentation
- Type validation
- Nested commands support
- Wide adoption

### Why openpyxl for Excel?

- Pure Python (no external dependencies)
- Good chart support
- Active maintenance
- Compatible with Excel 2010+

---

## Performance Considerations

### Memory

- Stream large datasets when possible
- Don't load entire project into memory
- Use generators where appropriate

### Speed

- Lazy loading of optional data
- Caching for expensive operations
- Parallel processing for independent operations (future)

---

## Release Process

1. **Update version** in setup.py and __init__.py
2. **Update CHANGELOG.md** with changes
3. **Run full test suite**: `pytest --cov=ekahau_bom`
4. **Create tag**: `git tag -a v2.5.0 -m "Release v2.5.0"`
5. **Push**: `git push origin v2.5.0`
6. **Create GitHub release** with changelog

---

## Support & Resources

- **Issues**: https://github.com/htechno/EkahauBOM/issues
- **Discussions**: https://github.com/htechno/EkahauBOM/discussions
- **Email**: (add if available)

---

**Version**: 2.4.0  
**Last Updated**: 2024
