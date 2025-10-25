# Release Notes: EkahauBOM v2.5.0 - Production Ready

## 🎉 Production Ready Release

EkahauBOM v2.5.0 completes **Iteration 5** with all 6 phases, achieving production-ready status!

---

## 📦 Installation

### From Source Distribution

```bash
# Download the tar.gz from GitHub Releases
pip install ekahau-bom-2.5.0.tar.gz
```

### From Wheel Distribution

```bash
# Download the .whl from GitHub Releases
pip install ekahau_bom-2.5.0-py3-none-any.whl
```

### Editable Install (Developers)

```bash
git clone https://github.com/nimbo78/EkahauBOM.git
cd EkahauBOM
git checkout v2.5.0
pip install -e .
```

---

## ✨ What's New in v2.5.0

### 📄 PDF Export (Phase 3)
- Professional print-ready PDF reports using **WeasyPrint**
- Print-optimized layout (A4 page size, proper margins)
- All sections included: Summary, Distribution, Analytics, AP tables
- Grouping statistics (vendor, floor, color, model)
- Radio and mounting analytics integration
- CLI argument: `--format pdf`
- 14 unit tests for PDF exporter

**Example:**
```bash
ekahau-bom project.esx --format pdf
```

### 🎨 Interactive CLI with Rich (Phase 4)
- **Rich library** integration for enhanced terminal output
- Progress bars for parsing and export operations
- Styled tables for summary statistics
- Enhanced error messages with colors and hints
- Graceful degradation if Rich not installed

**Example output:**
```
╭─────────────────────────────────────────╮
│ EkahauBOM - Bill of Materials Generator │
│ Version 2.5.0                           │
╰─────────────────────────────────────────╯

Processing project: project.esx ✓

✓ Processing completed successfully!
```

### 📦 Batch Processing (Phase 5)
- `--batch` CLI argument for processing multiple .esx files
- `--recursive` option for subdirectory search
- Batch progress display with Rich integration
- Batch summary table showing successful/failed files
- Error handling for individual file failures
- Support for all export formats in batch mode

**Example:**
```bash
# Process all .esx files in a directory
ekahau-bom --batch /path/to/projects/

# Recursive search
ekahau-bom --batch /path/to/projects/ --recursive

# With export formats
ekahau-bom --batch ./projects/ --format excel,pdf
```

### 📚 Documentation Overhaul (Phase 2)
- Complete **README.md** overhaul with professional structure
- **User Guide** (docs/USER_GUIDE.md) with examples
- **Developer Guide** (docs/DEVELOPER_GUIDE.md) for contributors
- Complete CHANGELOG.md with version history
- Russian translations for all documentation

### ✅ Testing & Quality (Phase 1)
- **258 tests passing** (100% pass rate)
- Test coverage increased from 40% to **70%**
- Fixed AccessPoint model edge cases
- Enhanced error handling in analytics modules
- Fixed height range boundaries in mounting analytics

### 📦 Modern Packaging (Phase 6)
- Created **pyproject.toml** for modern Python packaging (PEP 517/518)
- Build system configuration with setuptools
- Project metadata and dependencies
- Optional dependencies: pdf, rich, all, dev
- Tool configurations: pytest, coverage, black, mypy, pylint
- **MANIFEST.in** for including config files in distribution

---

## 📊 Complete Feature Set

### Export Formats (5)
- ✅ **CSV** - Simple, universally compatible
- ✅ **Excel** - Professional multi-sheet workbooks with charts
- ✅ **HTML** - Interactive web reports with Chart.js
- ✅ **JSON** - Machine-readable with complete metadata
- ✅ **PDF** - Print-ready professional reports ⭐ NEW

### Analytics
- 📡 **Radio Analytics**: Frequency bands, channels, Wi-Fi standards, TX power
- 🔧 **Mounting Analytics**: Height distribution, azimuth, tilt statistics
- 💰 **Cost Calculation**: Volume discounts, cost breakdowns
- 📈 **Coverage Analytics**: AP density, coverage per AP

### Filtering & Grouping
- Filter by: Floor, Color, Vendor, Model, Tags
- Group by: Floor, Color, Vendor, Model, Tag
- Multi-dimensional grouping with percentages

### CLI Features
- 🎨 Interactive CLI with Rich library ⭐ NEW
- 📦 Batch processing with progress bars ⭐ NEW
- 🔍 Filtering and grouping options
- 💰 Cost calculation with discounts
- 📁 Multiple output formats simultaneously

---

## 🎯 Production Ready Checklist

- ✅ All 258 tests passing (70% coverage)
- ✅ Complete documentation (README, user/developer guides)
- ✅ 5 export formats (CSV, Excel, HTML, JSON, PDF)
- ✅ Advanced analytics (radio, mounting, cost calculation)
- ✅ Interactive CLI with progress bars
- ✅ Batch processing support
- ✅ Modern packaging with pyproject.toml
- ✅ GitHub Releases with distributions

---

## 📋 Requirements

### Runtime
- **Python** 3.7+
- **PyYAML** >= 6.0
- **openpyxl** >= 3.0.0 (for Excel export)

### Optional
- **WeasyPrint** >= 60.0 (for PDF export)
- **rich** >= 13.0.0 (for enhanced terminal output)

### Development
- **pytest** >= 7.0.0
- **pytest-cov** >= 4.0.0
- **pytest-mock** >= 3.10.0
- **black** >= 22.0.0 (code formatting)
- **flake8** >= 5.0.0 (linting)
- **mypy** >= 0.990 (type checking)

---

## 🔗 Links

- **Repository**: https://github.com/nimbo78/EkahauBOM
- **Documentation**: https://github.com/nimbo78/EkahauBOM/tree/main/docs
- **Changelog**: https://github.com/nimbo78/EkahauBOM/blob/main/CHANGELOG.md
- **Issues**: https://github.com/nimbo78/EkahauBOM/issues

---

## 👤 Credits

**Author**: Pavel Semenischev (@nimbo78)

**Contributors**: The Wi-Fi engineering community

---

## 📝 Full Changelog

See [CHANGELOG.md](https://github.com/nimbo78/EkahauBOM/blob/main/CHANGELOG.md) for complete version history.

### From 2.4.0 to 2.5.0
- PDF Export functionality
- Interactive CLI with Rich library
- Batch processing support
- Documentation overhaul
- Testing improvements (40% → 70% coverage)
- Modern packaging with pyproject.toml

---

**Made with ❤️ for the Wi-Fi community**
