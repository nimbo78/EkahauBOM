# Changelog

All notable changes to EkahauBOM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.5.0] - 2025-10-26 (Production Ready Release)

### Added
- **Project Metadata Support** (Phase 8.1 - NEW!)
  - ProjectMetadata dataclass with comprehensive project information
  - Extraction of project name, customer, location, responsible person
  - Schema version tracking for Ekahau compatibility
  - Note IDs and project ancestors support
  - ProjectMetadataProcessor for data processing and validation
  - Integration into all export formats:
    - CSV: Project info in header comments
    - Excel: "Project Information" section in Summary sheet
    - HTML: Formatted metadata card with project details
    - PDF: Professional project information box
    - JSON: Structured metadata.project_info object
  - 10 new unit tests (tests/test_metadata_processor.py)

- **PDF Export** (Phase 3 - Iteration 5)
  - Professional print-ready PDF reports using WeasyPrint
  - Print-optimized layout (A4 page size, proper margins)
  - All sections included: Summary, Distribution, Analytics, AP tables
  - Grouping statistics (vendor, floor, color, model)
  - Radio and mounting analytics integration
  - CLI argument `--format pdf`
  - 14 unit tests for PDF exporter

- **Interactive CLI with Rich** (Phase 4 - Iteration 5)
  - Rich library integration for enhanced terminal output
  - Progress bars for parsing and export operations
  - Styled tables for summary statistics
  - Enhanced error messages with colors and hints
  - Helper functions: print_header(), print_summary_table(), print_export_summary()
  - Graceful degradation if Rich not installed

- **Batch Processing** (Phase 5 - Iteration 5)
  - `--batch` CLI argument for processing multiple .esx files
  - `--recursive` option for subdirectory search
  - Batch progress display with Rich integration
  - Batch summary table showing successful/failed files
  - Error handling for individual file failures
  - Support for all export formats in batch mode

### Enhanced
- **Documentation** (Phase 2 - Iteration 5)
  - Complete README.md overhaul with professional structure
  - User guide (docs/USER_GUIDE.md) with examples
  - Developer guide (docs/DEVELOPER_GUIDE.md) for contributors
  - Complete CHANGELOG.md with version history
  - Russian translations for all documentation

### Fixed
- **Radio Processing Bug** (Critical)
  - Fixed ERROR: `'>=' not supported between instances of 'list' and 'int'`
  - Ekahau sends channel/channelWidth as lists (e.g., `[11]`), not integers
  - Added `_extract_value()` method to handle list/int/float formats
  - Updated `_determine_wifi_standard()` with channel_width parameter
  - Added support for `technology` field from Ekahau data
  - Result: 6/6 radios processed successfully (was 0/6)
  - 14 new tests in tests/test_radio_processor.py

- **Tilt/Azimuth Extraction Bug** (Critical)
  - Fixed missing tilt, azimuth, and antenna_height in exports
  - Data is in simulatedRadios.json, not accessPoints.json
  - Updated AccessPointProcessor to accept simulated_radios_data
  - Created radio lookup dictionary for O(1) access by accessPointId
  - Proper extraction of antennaTilt, antennaDirection, antennaHeight
  - Backward compatibility with old format maintained
  - Verified with real projects (maga.esx: 4/7 APs with tilt = -10.0°)

- **Windows Filename Sanitization** (Platform-specific)
  - Fixed OSError on Windows with special characters in project names
  - Windows doesn't allow `<>:"/\|?*` in filenames
  - Added `_sanitize_filename()` method to BaseExporter
  - Invalid characters replaced with underscores
  - Leading/trailing dots and spaces removed
  - All 295 tests now pass on Windows

- **Test Compatibility Fixes**
  - test_excel_exporter.py: Updated for new Summary sheet structure
  - test_imports.py: Version updated to 2.5.0
  - test_json_exporter.py: Fixed project_name → file_name
  - test_processors.py: Updated _determine_wifi_standard() signature

- **Testing & Quality** (Phase 1 - Iteration 5)
  - All 295 tests passing (was 258, +37 new tests)
  - Test coverage maintained at 70%
  - Fixed AccessPoint model edge cases
  - Enhanced error handling in analytics modules
  - Fixed height range boundaries in mounting analytics

### Changed
- Version bumped to 2.5.0
- Production-ready status achieved

## [2.4.0] - 2024 (Advanced Analytics & Installation Export)

### Added
- **Radio Analytics** (Part 3)
  - Frequency band distribution (2.4/5/6 GHz)
  - Channel allocation analysis
  - Wi-Fi standards detection (802.11a/b/g/n/ac/ax/be)
  - TX power distribution and statistics
  - Channel width analysis
  - Integration into all export formats

- **Installation Parameters Export** (Part 4)
  - Detailed AP installation data for field technicians
  - Mounting height, azimuth, tilt for each AP
  - Location coordinates (X, Y) on floor plans
  - Enabled/disabled status
  - New files: `access_points_detailed.csv`
  - New Excel sheet: "AP Installation Details"
  - Enhanced HTML tables with installation parameters
  - JSON export with installation object

- **Cost Calculation & Pricing** (Part 1)
  - Equipment pricing database (config/pricing.yaml)
  - Volume discount tiers (5%-25%)
  - Cost breakdown by vendor, equipment type, floor
  - Custom discount support via CLI
  - --calculate-cost, --discount, --no-volume-discounts options
  - Integration into Excel export (Cost Breakdown sheet)

- **Coverage Analytics** (Part 2)
  - AP density calculations (APs per 1000 m²)
  - Coverage area per AP estimations
  - Measured areas support from Ekahau
  - Floor-level density metrics

### Enhanced
- **Excel Export**:
  - Radio Analytics sheet with frequency/standard charts
  - Mounting Analytics sheet with height distribution
  - Cost Breakdown sheet (when --calculate-cost used)
  - AP Installation Details sheet
  - Professional number formatting

- **HTML Export**:
  - Radio configuration visualizations
  - Mounting statistics tables
  - Detailed AP installation table
  - Right-aligned numeric columns

- **CSV Export**:
  - New detailed CSV with individual AP data
  - Analytics CSV with mounting & radio metrics
  - TX power distribution
  - Height range grouping

- **JSON Export**:
  - Installation object in AP details
  - Location coordinates
  - Enabled status
  - Complete radio analytics

### Fixed
- AccessPoint model: added location_x, location_y, name, enabled fields
- Test suite: fixed all 37 failing tests
- Edge cases in analytics (None values, malformed data)
- Height range boundary (6.0m now included in 4.5-6.0m range)

## [2.3.0] - 2024 (HTML & JSON Export)

### Added
- **HTML Export** (`--format html`)
  - Interactive web-based reports
  - Chart.js visualizations (pie, bar charts)
  - Responsive design for mobile/tablet
  - Modern styling with gradients
  - Sortable, filterable tables
  - Standalone file (no external dependencies)

- **JSON Export** (`--format json`)
  - Machine-readable format
  - Complete project data with metadata
  - Analytics and grouping information
  - Pretty-printed for readability
  - Ideal for API integrations

### Enhanced
- Multi-format export support
- `--format` option accepts multiple formats (csv,excel,html,json)
- Unified exporter architecture

## [2.2.0] - 2024 (Excel Export)

### Added
- **Excel Export** (`--format excel`)
  - Professional multi-sheet workbooks
  - Summary sheet with project overview
  - Access Points and Antennas sheets
  - Grouping sheets (By Floor, Color, Vendor, Model)
  - Charts and visualizations
  - Professional formatting
  - Auto-filters and frozen headers

### Enhanced
- Improved CSV export with better formatting
- Tag support in all export formats

## [2.1.0] - 2024 (Grouping & Analytics)

### Added
- **Grouping Analytics**
  - Group by floor, color, vendor, model
  - **Tag-based grouping** (`--group-by tag`)
  - Percentage distributions
  - Multi-dimensional grouping support
  - `--tag-key` option for tag grouping

- **Tag Support** (Ekahau v10.2+)
  - Parse tagKeys.json from projects
  - Link tags to access points
  - Filter by tags (`--filter-tag`)
  - Group by tag values
  - Tag processor module

- **Analytics Module**
  - GroupingAnalytics class
  - CoverageAnalytics class (basic)
  - Percentage calculations
  - Summary statistics

### Enhanced
- Improved filtering logic
- Better error handling for missing tags
- Tag integration in all exports

## [2.0.0] - 2024 (Filtering & Multi-vendor)

### Added
- **Filtering System**
  - Filter by floor (`--filter-floor`)
  - Filter by color (`--filter-color`)
  - Filter by vendor (`--filter-vendor`)
  - Filter by model (`--filter-model`)
  - Exclude filters (`--exclude-floor`, `--exclude-color`, etc.)
  - Combined filters with AND logic

- Multi-vendor support (Cisco, Aruba, Ruckus, etc.)
- Color support with configurable mappings
- Custom colors via YAML configuration

### Enhanced
- Improved data models (AccessPoint, Antenna, Tag)
- Better project structure
- Type hints throughout codebase

## [1.0.0] - 2024 (Initial Release)

### Added
- Parse Ekahau .esx project files
- Extract access points data (vendor, model, quantity)
- Extract antennas data with quantities
- CSV export (access_points.csv, antennas.csv)
- Basic grouping by floor
- Command-line interface
- Logging support
- Configuration file support

### Features
- Support for .esx format (ZIP archives)
- JSON parsing for project data
- Access point counting and aggregation
- Antenna extraction and counting
- Floor-based organization

---

## Version History Summary

| Version | Date | Key Features |
|---------|------|-------------|
| **2.5.0** | 2025-01-25 | Production Ready: PDF Export, Interactive CLI, Batch Processing |
| **2.4.0** | 2024 | Radio Analytics, Installation Export, Cost Calculation |
| **2.3.0** | 2024 | HTML & JSON Export |
| **2.2.0** | 2024 | Excel Export with Charts |
| **2.1.0** | 2024 | Grouping, Analytics, Tag Support |
| **2.0.0** | 2024 | Filtering, Multi-vendor |
| **1.0.0** | 2024 | Initial Release |

---

## Upgrade Notes

### From 2.4.x to 2.5.0
- No breaking changes
- New CLI options: `--batch`, `--recursive` for batch processing
- New export format: `--format pdf` (requires WeasyPrint>=60.0)
- Rich library integration for enhanced CLI output (optional dependency)
- All existing functionality remains backward compatible

### From 2.3.x to 2.4.0
- New CLI options: `--calculate-cost`, `--discount`, `--no-volume-discounts`
- New output files: `*_detailed.csv`, `*_analytics.csv`
- Excel export now includes up to 11 sheets (vs 8 previously)
- config/pricing.yaml required for cost calculation features

### From 2.2.x to 2.3.0
- No breaking changes
- HTML and JSON exports are additive features
- `--format` now accepts comma-separated list

### From 2.1.x to 2.2.0
- No breaking changes
- Excel export requires openpyxl >= 3.0.0
- New `--format` option (defaults to csv for backward compatibility)

### From 2.0.x to 2.1.0
- No breaking changes
- Tag features work only with Ekahau v10.2+ projects
- Older projects continue to work without tags

### From 1.x to 2.0.0
- **Breaking**: Command-line interface updated
- Filter options added (optional, backward compatible)
- Color configuration moved to config/colors.yaml
- Update any automation scripts to use new filter options

---

## Migration Guide

### From v1.x to v2.x

**Old:**
```bash
python EkahauBOM.py project.esx
```

**New (with filtering):**
```bash
python EkahauBOM.py project.esx --filter-floor "Floor 1"
```

**Note**: Basic usage remains the same. New features are opt-in.

---

## Roadmap

### Future Releases

**v2.5.0** - PDF Export
- PDFExporter with WeasyPrint
- Professional PDF reports
- Print-optimized layouts

**v2.6.0** - Interactive CLI
- Rich library integration
- Progress bars
- Interactive menus
- Color output

**v2.7.0** - Batch Processing
- Multiple project processing
- Project comparison
- Aggregated reports

**v3.0.0** - API & Web UI
- REST API
- Web interface
- Database integration
- User authentication

---

## Contributors

- **Pavel Semenischev** (@htechno) - Creator and maintainer

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
