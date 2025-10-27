# Contributing to EkahauBOM

First off, thank you for considering contributing to EkahauBOM! It's people like you that make EkahauBOM such a great tool for the Wi-Fi community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project and everyone participating in it is governed by the [EkahauBOM Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

---

## Getting Started

### Prerequisites

- **Python 3.7+** (recommended: Python 3.10+)
- **Git** for version control
- **GitHub account** for pull requests
- **Basic knowledge** of:
  - Python programming
  - Command-line tools
  - Git workflows

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/EkahauBOM.git
   cd EkahauBOM
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

5. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. **Verify installation**:
   ```bash
   ekahau-bom --version
   pytest tests/ -v
   ```

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**When submitting a bug report, include:**
- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment details**:
  - OS and version
  - Python version
  - EkahauBOM version
  - Ekahau project file version (if applicable)
- **Error messages** or logs (use code blocks)
- **Sample .esx file** (if not sensitive)

**Bug Report Template:**
```markdown
**Description:**
Brief description of the bug

**To Reproduce:**
1. Step one
2. Step two
3. See error

**Expected Behavior:**
What you expected to happen

**Environment:**
- OS: Windows 10 / macOS 12 / Ubuntu 22.04
- Python: 3.10.5
- EkahauBOM: 2.7.0

**Additional Context:**
Any other relevant information
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**When suggesting an enhancement, include:**
- **Clear use case** - why is this needed?
- **Proposed solution** - how should it work?
- **Alternatives considered**
- **Impact on existing functionality**
- **Mockups or examples** (if applicable)

### Contributing Code

We welcome code contributions! Here are some areas where help is appreciated:

**Good First Issues:**
- Documentation improvements
- Adding test cases
- Fixing typos or formatting
- Small bug fixes

**Areas for Contribution:**
- New export formats (e.g., XML, Markdown)
- Additional processors (e.g., network settings, cable infrastructure)
- Enhanced visualizations
- Performance optimizations
- CLI improvements
- Configuration options

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

**Branch Naming Convention:**
- `feature/feature-name` - New features
- `fix/bug-name` - Bug fixes
- `docs/topic` - Documentation
- `refactor/component` - Code refactoring
- `test/component` - Test improvements

### 2. Make Your Changes

- Write clear, readable code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=ekahau_bom --cov-report=html

# Run specific test file
pytest tests/test_parser.py -v

# Run code quality checks
black ekahau_bom/ tests/
flake8 ekahau_bom/
mypy ekahau_bom/
```

### 4. Commit Your Changes

Pre-commit hooks will automatically:
- Format code with Black
- Check for trailing whitespace
- Fix line endings
- Check for large files

```bash
git add .
git commit -m "Add feature: your feature description"
```

See [Commit Guidelines](#commit-guidelines) below.

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings (Black will enforce)
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

**Example:**
```python
from typing import List, Optional

def process_access_points(
    aps: List[dict],
    filter_vendor: Optional[str] = None
) -> List[AccessPoint]:
    """Process access point data from Ekahau project.

    Args:
        aps: List of access point dictionaries
        filter_vendor: Optional vendor filter

    Returns:
        List of processed AccessPoint objects

    Raises:
        ValueError: If aps is empty or invalid
    """
    if not aps:
        raise ValueError("Access points list cannot be empty")

    # Processing logic here
    pass
```

### Code Organization

- **Imports**: Organize in groups (stdlib, third-party, local)
- **Functions**: Keep functions small and focused
- **Classes**: Use dataclasses for data models
- **Constants**: Use UPPER_CASE for constants
- **Private**: Prefix with underscore (_private_function)

### Naming Conventions

```python
# Variables and functions: snake_case
access_points = []
def get_vendor_name():
    pass

# Classes: PascalCase
class AccessPoint:
    pass

# Constants: UPPER_CASE
DEFAULT_OUTPUT_DIR = "output"

# Private: _leading_underscore
def _internal_helper():
    pass
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── test_parser.py           # Parser tests
├── test_exporters/          # Exporter tests
│   ├── test_csv_exporter.py
│   └── test_excel_exporter.py
├── test_processors/         # Processor tests
├── test_integration.py      # End-to-end tests
└── fixtures/                # Test data
```

### Writing Tests

**Test Function Naming:**
```python
def test_parser_opens_esx_file():
    """Test that parser successfully opens valid .esx files."""
    pass

def test_csv_exporter_handles_empty_data():
    """Test CSV exporter gracefully handles empty data."""
    pass
```

**Use Fixtures:**
```python
import pytest

@pytest.fixture
def sample_access_point():
    """Fixture providing a sample AccessPoint for testing."""
    return AccessPoint(
        vendor="Cisco",
        model="AIR-AP3802I-B-K9",
        quantity=1
    )

def test_access_point_vendor(sample_access_point):
    """Test access point vendor attribute."""
    assert sample_access_point.vendor == "Cisco"
```

**Test Coverage:**
- Aim for **80%+ coverage** for new code
- Test **happy paths** and **edge cases**
- Test **error handling**
- Use **mocks** for external dependencies

**Example Test:**
```python
def test_parser_handles_missing_file():
    """Test parser raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        parser = EkahauParser("nonexistent.esx")
        parser.parse()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_parser.py

# Run specific test
pytest tests/test_parser.py::test_parser_opens_esx_file

# Run with coverage
pytest --cov=ekahau_bom --cov-report=html

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

---

## Commit Guidelines

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style/formatting (no functional changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

**Good commit messages:**
```
feat: Add XML export format

Implements XML exporter with schema validation.
Includes unit tests and documentation.

Closes #42
```

```
fix: Handle missing mounting height in CSV export

Previously, mounting height was empty when not explicitly set.
Now falls back to radio antenna_height.

Fixes #89
```

**Bad commit messages:**
```
update stuff
fixed bug
more changes
```

### Commit Best Practices

- **Atomic commits**: One logical change per commit
- **Clear messages**: Explain why, not just what
- **Reference issues**: Use "Fixes #123" or "Closes #123"
- **Sign commits**: Use `-s` flag for sign-off
- **Small commits**: Easier to review and revert

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated (docstrings, README, etc.)
- [ ] CHANGELOG.md updated (if applicable)
- [ ] No merge conflicts with main branch

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No warnings or errors

## Related Issues
Fixes #(issue number)
```

### PR Review Process

1. **Automated checks** run (tests, code quality)
2. **Maintainer review** (usually within 48 hours)
3. **Discussion and changes** if needed
4. **Approval** from maintainer
5. **Merge** to main branch

### After PR is Merged

- Delete your feature branch
- Pull latest main branch
- Celebrate! 🎉

---

## Additional Resources

- **Developer Guide**: [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
- **User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **Project Architecture**: See Developer Guide
- **Issue Tracker**: [GitHub Issues](https://github.com/nimbo78/EkahauBOM/issues)

---

## Questions?

- **GitHub Discussions**: [Ask questions](https://github.com/nimbo78/EkahauBOM/discussions)
- **GitHub Issues**: [Report bugs or suggest features](https://github.com/nimbo78/EkahauBOM/issues)

---

**Thank you for contributing to EkahauBOM!** ❤️
