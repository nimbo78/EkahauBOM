# Changelog

All notable changes to EkahauBOM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **GitHub Actions CI/CD** (Phase 9.2 - NEW!)
  - Automated release workflow (`release.yml`)
    - Triggers on version tag push (v*.*.*)
    - Builds Python package (wheel and source distribution)
    - Extracts changelog for the version
    - Creates GitHub release with artifacts
    - Uploads build artifacts
  - PyPI publishing workflow (`publish-pypi.yml`)
    - Triggers on GitHub release publication
    - Supports manual trigger
    - Validates package with twine
    - Publishes to PyPI
  - Continuous testing workflow (`tests.yml`)
    - Runs on push and pull requests to main/develop
    - Tests on multiple OS (Ubuntu, Windows, macOS)
    - Tests Python versions 3.8-3.12
    - Generates coverage reports
    - Uploads to Codecov
  - Code quality workflow (`code-quality.yml`)
    - Checks code formatting with black
    - Lints with flake8
    - Type checks with mypy
  - Comprehensive release process documentation ([RELEASE_PROCESS.md](RELEASE_PROCESS.md))
  - GitHub Actions badges in README.md

- **Unit Tests Coverage Improvements** (Phase 9.1 - NEW!)
  - Added 29 new unit tests (+9% increase)
  - Fixed 16 failing tests (all tests now passing: 367/367)
  - Installed pytest-cov for code coverage measurement
  - Overall code coverage: 60% → 63%
  - New test file: `tests/test_network_settings_processor.py` (15 tests)
  - Module coverage improvements:
    - network_settings.py: 24% → 100% (+76%)
    - json_exporter.py: 74% → 100% (+26%)
    - parser.py: 80% → 99% (+19%)
    - access_points.py: 80% → 95% (+15%)
  - Tests for:
    - Network capacity settings processing
    - JSON export with metadata, radios, cable notes
    - Parser missing file handling
    - Access point processing with radios and error handling

- **Azimuth Direction Arrows** (Phase 8.9 - NEW!)
  - New CLI flag `--show-azimuth-arrows` for displaying directional indicators on AP markers
  - Arrow visualization showing antenna azimuth/direction (particularly useful for wall-mounted APs)
  - Smart arrow color selection for optimal contrast:
    - Red arrows for transparent/light APs
    - Dark gray arrows for light solid colors
    - Yellow arrows for dark solid colors
  - Arrow properties:
    - Length: 2 × ap_circle_radius (default 30px)
    - Arrow head: filled triangle
    - Line width: 2px
  - Only shows arrows when azimuth ≠ 0° (has meaningful direction data)
  - Works with all mounting types (CEILING, WALL, FLOOR)
  - Mathematical implementation with proper coordinate system adjustment
  - Fully backward compatible - arrows disabled by default
  - `_draw_azimuth_arrow()` method in FloorPlanVisualizer

- **Configurable AP Marker Opacity** (Phase 8.10 - NEW!)
  - New CLI flag `--ap-opacity` for controlling AP marker opacity (0.0-1.0)
  - Allows fine-tuning of AP marker visibility on floor plans
  - Default: 1.0 (100% opacity, fully opaque)
  - Examples:
    - `--ap-opacity 0.5` for 50% transparent markers
    - `--ap-opacity 0.3` for 70% transparent markers
  - Applies to all AP markers (both colored and default)
  - Works seamlessly with alpha compositing and transparency features
  - Independent from default AP color transparency

### Fixed
- **Mounting Height in Detailed CSV Export**
  - Fixed missing mounting height values in `_access_points_detailed.csv`
  - Now correctly extracts `antenna_height` from Radio objects
  - Falls back to Radio's antenna_height when AccessPoint.mounting_height is not available
  - Displays actual mounting heights (e.g., 2.40m for ceiling APs, 0.40m for wall APs)
  - Accurate data for installation planning and field verification

## [2.7.0] - 2025-10-26 (Network Settings & Radio Configuration)

### Added
- **Network Settings Support** (Phase 8.4 - NEW!)
  - DataRate, NetworkCapacitySettings dataclasses for network configuration
  - NetworkSettingsProcessor for processing network capacity settings:
    - process_network_settings() - processes frequency band settings (2.4GHz, 5GHz, 6GHz)
    - get_ssid_summary() - SSID count and max client statistics per band
    - get_data_rate_summary() - 802.11 a/b/g data rate configuration (mandatory/disabled/supported)
  - Parser function: get_network_capacity_settings()
  - Constant: ESX_NETWORK_CAPACITY_SETTINGS_FILE
  - Integration into ProjectData with network_settings field
  - CLI integration with "Network Configuration" section:
    - SSID count per frequency band (2.4GHz, 5GHz)
    - Max associated clients per band
    - Channel distribution display (top 10 most used channels)
  - JSON export with complete network_settings section:
    - ssid_configuration: SSID count and max clients per band
    - data_rates: mandatory/disabled rates summary per band
    - bands: detailed configuration for each frequency band with all data rates
  - Support for RTS/CTS settings
  - Frequency band mapping: TWO→2.4GHz, FIVE→5GHz, SIX→6GHz
  - 802.11 data rates (R1, R2, R5.5, R6, R9, R11, R12, R18, R24, R36, R48, R54)

### Improved
- **Floor Plan Visualization Enhancements**
  - Enhanced color name support in floor plan visualizer
    - Now supports standard color names (Red, Blue, Green, Yellow, Orange, Purple, Pink, etc.)
    - Automatic typo correction for duplicate characters (RReedd → Red)
    - Case-insensitive color matching with exact match priority
    - Extended Ekahau color palette (lightblue, darkblue, lightgreen, etc.)
  - Added automatic color legend to all floor plan visualizations
    - Semi-transparent background for better readability
    - Shows color distribution with AP count per color
    - Positioned in top-right corner
    - Matches AP marker style (circles with borders)
    - Includes "Default" entry for APs without assigned colors
  - **Proper transparency support with alpha compositing**
    - Created overlay layer for AP markers with true alpha blending
    - Default AP color changed to pale blue (173, 216, 230) with 50% opacity
    - Transparent APs allow floor plan details to show through
    - Uses Image.alpha_composite() for proper RGBA rendering
  - **Mounting type visualization with different shapes**
    - Ceiling-mounted APs: circles (traditional)
    - Wall-mounted APs: rectangles oriented by azimuth direction
    - Floor-mounted APs: squares
    - Long edge of rectangles points in azimuth direction for wall APs
  - **Fixed wall-mounted AP orientation**
    - Rectangle orientation now correctly aligns long edge with azimuth
    - Proper directional indication for wall-mounted access points
  - No more "Invalid hex color" warnings for standard color names
  - Better visual differentiation between AP types
  - More professional and presentation-ready output

## [2.6.0] - 2025-10-26 (Map Notes, Cable Infrastructure & Floor Plan Visualization)

### Added
- **Floor Plan Visualization** (NEW!)
  - FloorPlanVisualizer class for generating visual floor plans with AP placements
  - Extract floor plan images from .esx project files
  - Overlay AP positions with colored circles matching their Ekahau colors
  - Customizable visualization options:
    - AP circle radius and border width
    - Optional AP name labels with auto-positioning
    - Support for custom colors or default values
  - CLI integration with `--visualize-floor-plans` flag
  - Additional CLI options:
    - `--ap-circle-radius` - Set marker size (default: 15px)
    - `--no-ap-names` - Hide AP names on visualizations
  - Visualizations saved to `output/visualizations/` directory
  - Support for multiple floors with automatic processing
  - PNG format output with floor plan as background
  - Requires Pillow library (optional dependency)
  - 12 comprehensive unit tests

- **Cable Infrastructure Analytics** (Phase 8.5 - NEW!)
  - CableMetrics dataclass with comprehensive cable statistics
  - CableAnalytics class with calculation methods:
    - calculate_cable_length() - Euclidean distance between coordinate points
    - calculate_cable_metrics() - aggregated metrics (total/avg/min/max length)
    - estimate_cable_cost() - cost estimation with material + installation
    - generate_cable_bom() - BOM for cables, connectors, routes
  - Cable length calculation from coordinate points (pixels to units)
  - Support for scale factor conversion to meters
  - Cables grouped by floor with length totals
  - Cable BOM generation:
    - Cat6A UTP cable (in meters, rounded up)
    - RJ45 connectors (quantity = cables × 2)
    - Cable routes/runs (logical count)
  - Cost estimation with customizable prices:
    - Cable material cost with overage factor (default 1.2x = 20%)
    - Installation labor cost
    - Total cost breakdown
  - CLI integration with "Cable Infrastructure Analytics" section
  - JSON export with complete cable_infrastructure section:
    - metrics: total_cables, lengths (units and meters), avg/min/max, by floor
    - bill_of_materials: complete BOM items array
  - 18 new unit tests (tests/test_cable_analytics.py)

- **Map Notes Support** (Phase 8.2 - NEW!)
  - Note, NoteHistory, CableNote, PictureNote, Point, Location dataclasses
  - NotesProcessor for processing all note types:
    - process_notes() - text notes with history (created_at, created_by)
    - process_cable_notes() - cable routing paths with coordinates
    - process_picture_notes() - image markers on floor plans
  - Parser functions: get_notes(), get_cable_notes(), get_picture_notes()
  - Constants: ESX_NOTES_FILE, ESX_CABLE_NOTES_FILE, ESX_PICTURE_NOTES_FILE
  - Integration into ProjectData with notes, cable_notes, picture_notes fields
  - CLI integration with logging: "Found X text notes, Y cable notes, Z picture notes"
  - Updated summary table to display notes counts
  - JSON export with complete notes section:
    - text_notes array with id, text, created_at, created_by, image_ids, status
    - cable_notes array with floor info, path points, color, linked note IDs
    - picture_notes array with location coordinates, linked note IDs
    - notes.summary with totals
  - 15 new unit tests (tests/test_notes_processor.py)

### Fixed
- **PDF Import Error** (Conditional Import)
  - PDF exporter now imports only when 'pdf' format requested
  - Graceful error message if WeasyPrint not installed
  - Prevents import errors when PDF not needed
  - Better UX for users without WeasyPrint

### Changed
- Updated CLI summary table to accept notes parameters
- Updated print_summary_table() to display notes counts

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
