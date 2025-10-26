# EkahauBOM

> **Professional Bill of Materials (BOM) generator for Ekahau AI project files**

EkahauBOM extracts equipment data from Ekahau .esx project files and generates comprehensive, professional reports for Wi-Fi engineers, procurement teams, and installation crews.

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Coverage](https://img.shields.io/badge/coverage-70%25-brightgreen.svg)](tests/)
[![Tests](https://img.shields.io/badge/tests-295%20passing-brightgreen.svg)](tests/)

**English** | [Русский](README.ru.md)

---

## 🌟 Key Features

### 📊 **Multi-Format Export**
- **CSV**: Simple, universally compatible format with aggregated and detailed views
- **Excel**: Professional reports with multiple sheets, charts, formulas, and formatting
- **HTML**: Interactive web reports with Chart.js visualizations and responsive design
- **JSON**: Machine-readable format with complete metadata for API integrations
- **PDF**: Print-ready professional reports with tables and statistics (requires WeasyPrint)

### 📡 **Advanced Radio Analytics**
- **Frequency band distribution** (2.4 GHz / 5 GHz / 6 GHz)
- **Channel allocation** analysis with usage patterns
- **Wi-Fi standards** detection (802.11a/b/g/n/ac/ax/be)
- **TX power distribution** and recommendations
- **Channel width** analysis (20/40/80/160 MHz)

### 🔧 **Installation Parameters Export**
- **Mounting height** for each access point
- **Azimuth** (horizontal direction) for directional APs
- **Tilt** (vertical angle) for optimal coverage
- **Location coordinates** (X, Y) on floor plans
- **Installation summary** with height recommendations

### 💰 **Cost Calculation & Pricing**
- Equipment pricing database (YAML configuration)
- **Volume discounts** (5%-25% based on quantity)
- Cost breakdown by:
  - Vendor (Cisco, Aruba, etc.)
  - Equipment type (APs, antennas)
  - Floor/building
- Custom discount support
- Professional cost summary reports

### 📄 **Project Metadata** _(New in v2.5.0)_
- **Project information** extraction (name, customer, location, responsible person)
- **Schema version** tracking
- Metadata displayed in all export formats:
  - CSV: Header comments with project info
  - Excel: Dedicated "Project Information" section
  - HTML: Formatted metadata card
  - PDF: Professional cover page section
  - JSON: Structured metadata object

### 🏷️ **Tag Support & Filtering**
- Full support for **Ekahau v10.2+ tags**
- Filter by tags (Location, Zone, Building, etc.)
- Group and analyze by tag values
- Tag-based multi-dimensional grouping

### 📈 **Coverage & Mounting Analytics**
- **AP density** calculations (APs per 1000 m²)
- **Mounting height statistics** (avg, min, max, variance)
- **Height distribution** by ranges (< 2.5m, 2.5-3.5m, etc.)
- **Azimuth & tilt** statistics for directional antennas
- **Coverage area** estimations per AP

### 🎯 **Flexible Filtering**
Filter access points by:
- Floor names
- Colors (Ekahau color coding)
- Vendors (Cisco, Aruba, Ruckus, etc.)
- Models (specific AP models)
- Tags (custom metadata)
- Combinations with AND/OR logic

### 📋 **Grouping & Statistics**
- Group by floor, color, vendor, model, or tag
- **Multi-dimensional grouping** (e.g., floor + color)
- Percentage distributions
- Count summaries
- Pivot table-style reports in Excel

---

## 📦 Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/htechno/EkahauBOM.git
cd EkahauBOM

# Install dependencies
pip install -r requirements.txt

# Optional: Install as package
pip install -e .
```

### As Package

```bash
pip install -e .
```

After installation, use the `ekahau-bom` command globally:

```bash
ekahau-bom project.esx
```

---

## 🚀 Quick Start

### Basic Usage

```bash
# Generate BOM in CSV format (default)
python EkahauBOM.py project.esx

# Or using installed command
ekahau-bom project.esx
```

Output (with Rich library installed):
```
╭─────────────────────────────────────────╮
│ EkahauBOM - Bill of Materials Generator │
│ Version 2.4.0                           │
╰─────────────────────────────────────────╯

Processing project: project.esx ✓

✓ Processing completed successfully!

Project Summary
┌────────────────┬───────┐
│ Metric         │ Count │
├────────────────┼───────┤
│ Access Points  │   45  │
│ Antennas       │   90  │
│ Radios         │   90  │
│ Floors         │    3  │
│ Unique Vendors │    2  │
└────────────────┴───────┘

✓ Reports saved to: output/
```

### Multi-Format Export

```bash
# Export to Excel (recommended for full features)
ekahau-bom project.esx --format excel

# Export to HTML (interactive web report)
ekahau-bom project.esx --format html

# Export to PDF (print-ready report)
ekahau-bom project.esx --format pdf

# Export to all formats at once
ekahau-bom project.esx --format csv,excel,html,json,pdf
```

### With Options

```bash
# Specify output directory
ekahau-bom project.esx --output-dir reports/

# Enable verbose logging
ekahau-bom project.esx --verbose

# Save logs to file
ekahau-bom project.esx --log-file processing.log

# Use custom colors configuration
ekahau-bom project.esx --colors-config my_colors.yaml
```

---

## 📖 Usage Examples

### 1. Filter by Floor

Generate BOM only for specific floors:

```bash
ekahau-bom project.esx --filter-floor "Floor 1,Floor 2"
```

### 2. Filter by Vendor

Extract only Cisco equipment:

```bash
ekahau-bom project.esx --filter-vendor "Cisco"
```

### 3. Filter by Tags

Filter by custom tags (Ekahau v10.2+):

```bash
ekahau-bom project.esx --filter-tag "Location:Building A"
```

### 4. Combine Filters

Use multiple filters together:

```bash
ekahau-bom project.esx \
  --filter-floor "Floor 1,Floor 2" \
  --filter-vendor "Cisco,Aruba" \
  --filter-color "Yellow"
```

### 5. Exclude Specific Items

Exclude certain floors or colors:

```bash
ekahau-bom project.esx \
  --exclude-floor "Basement" \
  --exclude-color "Gray"
```

### 6. Grouping & Analytics

Group access points and display statistics:

```bash
# Group by vendor
ekahau-bom project.esx --group-by vendor

# Group by floor with chart in Excel
ekahau-bom project.esx --group-by floor --format excel

# Group by custom tag
ekahau-bom project.esx --group-by tag --tag-key "Location"
```

### 7. Cost Calculation

Generate cost estimates with pricing:

```bash
# Use default pricing database
ekahau-bom project.esx --calculate-cost

# Apply custom discount
ekahau-bom project.esx --calculate-cost --discount 15

# Disable volume discounts
ekahau-bom project.esx --calculate-cost --no-volume-discounts
```

### 8. Batch Processing

Process multiple .esx files at once:

```bash
# Process all .esx files in a directory
ekahau-bom --batch /path/to/projects/

# Process recursively (including subdirectories)
ekahau-bom --batch /path/to/projects/ --recursive

# Batch processing with export format
ekahau-bom --batch ./projects/ --format excel,pdf

# Batch processing with filters
ekahau-bom --batch ./projects/ \
  --filter-vendor "Cisco" \
  --format csv,excel
```

**Note:** When using batch mode, each project will be processed independently and outputs will be saved in the same directory structure or the specified `--output-dir`.

---

## 📁 Output Files

### CSV Export

Creates multiple CSV files:

1. **`project_access_points.csv`**
   - Aggregated view: vendor, model, floor, color, tags, quantity

2. **`project_access_points_detailed.csv`**
   - Individual AP list with installation parameters:
     - AP name
     - Location (X, Y coordinates)
     - Mounting height (m)
     - Azimuth (degrees)
     - Tilt (degrees)
     - Enabled status

3. **`project_antennas.csv`**
   - Antenna models and quantities

4. **`project_analytics.csv`** (if data available)
   - Mounting metrics (avg/min/max height, azimuth, tilt)
   - Height distribution by ranges
   - Radio configuration analytics
   - TX power distribution
   - Installation summary

### Excel Export

Single workbook with multiple sheets:

| Sheet | Content |
|-------|---------|
| **Summary** | Project overview, totals by vendor/floor |
| **Access Points** | Aggregated AP list with tags |
| **AP Installation Details** | Individual AP installation parameters |
| **Antennas** | Antenna list with quantities |
| **By Floor** | Floor distribution with pie chart |
| **By Color** | Color distribution with bar chart |
| **By Vendor** | Vendor distribution with pie chart |
| **By Model** | Model distribution with chart |
| **Radio Analytics** | Radio configuration charts (bands, standards, channels) |
| **Mounting Analytics** | Height distribution and mounting statistics |
| **Cost Breakdown** | Cost by vendor, equipment type, floor (if --calculate-cost) |

**Features:**
- Professional formatting with borders and colors
- Auto-sized columns and frozen headers
- Auto-filters on all tables
- Charts and visualizations (pie, bar, column)
- Number formatting (2 decimals for heights, 1 for angles)

### HTML Export

Single standalone HTML file with:

- **Responsive design** (works on desktop, tablet, mobile)
- **Interactive tables** (sortable, filterable)
- **Chart.js visualizations** (pie, bar, line charts)
- **Modern styling** (gradients, shadows, professional look)
- **No external dependencies** (fully self-contained)
- **Print-friendly** CSS

Perfect for:
- Presentations to clients
- Email sharing
- Web publishing
- Project documentation

### JSON Export

Structured JSON with:

```json
{
  "metadata": {
    "project_name": "Office Building WiFi",
    "generated_at": "2025-10-24T12:34:56",
    "total_aps": 45,
    "total_antennas": 90
  },
  "summary": {
    "by_vendor": {...},
    "by_floor": {...},
    "by_color": {...}
  },
  "access_points": {
    "aggregated": [...],
    "details": [
      {
        "name": "AP-01",
        "vendor": "Cisco",
        "model": "C9120AXI",
        "floor": "Floor 1",
        "location": {"x": 10.5, "y": 20.3},
        "installation": {
          "mounting_height": 3.2,
          "azimuth": 45.0,
          "tilt": 10.0
        },
        "tags": [...]
      }
    ]
  },
  "radio_analytics": {...},
  "mounting_analytics": {...},
  "cost_breakdown": {...}
}
```

Ideal for:
- API integrations
- Database imports
- Automated workflows
- Custom reporting tools

### PDF Export

Professional print-ready PDF document with:

- **Print-optimized layout** (A4 page size with proper margins)
- **Professional styling** with tables and statistics
- **Summary statistics** (totals, distributions)
- **Grouping tables** (by vendor, floor, color, model)
- **Analytics sections** (mounting, radio configuration)
- **Access points tables** (aggregated and detailed installation params)
- **Page breaks** optimized for printing
- **No external dependencies** (fully self-contained)

Perfect for:
- Client presentations and deliverables
- Project documentation archives
- Printed reports for field teams
- Professional proposals
- Stakeholder reviews

**Note**: Requires WeasyPrint library (`pip install WeasyPrint>=60.0`)

---

## ⚙️ Configuration

### Configuration File

EkahauBOM supports a central configuration file (`config/config.yaml`) to set default values for all options:

```yaml
# Export settings
export:
  output_dir: reports
  formats:
    - excel
    - html

# Pricing configuration
pricing:
  enabled: true
  default_discount: 10.0

# Filters (optional defaults)
filters:
  exclude_colors:
    - Gray

# Logging
logging:
  level: INFO
  file: logs/ekahau_bom.log
```

Use custom configuration:

```bash
# Use specific config file
ekahau-bom project.esx --config my_config.yaml

# Use default config (config/config.yaml)
ekahau-bom project.esx
```

**Note:** CLI arguments always override configuration file values.

### Custom Colors

Create a YAML file to map Ekahau hex colors to names:

```yaml
# my_colors.yaml
"#FFE600": "Yellow"
"#FF8500": "Orange"
"#FF0000": "Red"
"#00FF00": "Green"
"#0000FF": "Blue"
"#CUSTOM": "My Custom Color"
```

Usage:

```bash
ekahau-bom project.esx --colors-config my_colors.yaml
```

Default colors are in `config/colors.yaml`.

### Pricing Configuration

Edit `config/pricing.yaml` to customize equipment prices:

```yaml
access_points:
  Cisco:
    C9120AXI: 850.00
    C9130AXI: 1200.00
  Aruba:
    AP-515: 750.00
    AP-635: 1100.00

antennas:
  ANT-2513P4M-N-R: 125.00
  ANT-20: 85.00

# Volume discount tiers
volume_discounts:
  - min_quantity: 10
    discount_percent: 5.0
  - min_quantity: 50
    discount_percent: 10.0
  - min_quantity: 100
    discount_percent: 15.0
  - min_quantity: 250
    discount_percent: 20.0
  - min_quantity: 500
    discount_percent: 25.0
```

---

## 🏗️ Project Structure

```
EkahauBOM/
├── ekahau_bom/              # Main package
│   ├── cli.py               # Command-line interface
│   ├── parser.py            # .esx file parser (ZIP + JSON)
│   ├── models.py            # Data models (AccessPoint, Radio, Tag, etc.)
│   ├── constants.py         # Constants and defaults
│   ├── utils.py             # Utility functions
│   ├── filters.py           # Filtering logic
│   ├── analytics.py         # Analytics & grouping
│   ├── pricing.py           # Cost calculation
│   ├── processors/          # Data processors
│   │   ├── access_points.py # AP processor
│   │   ├── antennas.py      # Antenna processor
│   │   ├── radios.py        # Radio processor
│   │   └── tags.py          # Tag processor (v10.2+)
│   └── exporters/           # Export formats
│       ├── base.py          # Base exporter class
│       ├── csv_exporter.py  # CSV export
│       ├── excel_exporter.py # Excel export (openpyxl)
│       ├── html_exporter.py # HTML export (Chart.js)
│       └── json_exporter.py # JSON export
├── config/                  # Configuration files
│   ├── colors.yaml          # Color database
│   └── pricing.yaml         # Equipment pricing
├── tests/                   # Test suite (258 tests, 70% coverage)
│   ├── test_analytics.py
│   ├── test_csv_exporter.py
│   ├── test_excel_exporter.py
│   ├── test_filters.py
│   ├── test_models.py
│   ├── test_parser.py
│   ├── test_pricing.py
│   ├── test_processors.py
│   ├── test_tags.py
│   └── test_utils.py
├── docs/                    # Documentation
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   └── examples/
├── output/                  # Default output directory
├── EkahauBOM.py            # Main entry point
├── setup.py                # Package setup
├── requirements.txt        # Dependencies
├── requirements-dev.txt    # Development dependencies
├── README.md               # This file
├── CHANGELOG.md            # Version history
└── LICENSE                 # MIT License
```

---

## 🧪 Testing

### Run Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=ekahau_bom

# Run specific test file
pytest tests/test_analytics.py -v

# Run with verbose output
pytest -v --tb=short
```

### Coverage Report

Current test coverage: **70%**

```
Module                          Coverage
----------------------------------------
ekahau_bom/csv_exporter.py      100%
ekahau_bom/parser.py            100%
ekahau_bom/utils.py             100%
ekahau_bom/antennas.py          100%
ekahau_bom/access_points.py     95%
ekahau_bom/radios.py            95%
ekahau_bom/analytics.py         85%
ekahau_bom/pricing.py           88%
ekahau_bom/filters.py           88%
----------------------------------------
Total: 258 tests passing
```

---

## 🛠️ Development

### Code Quality

```bash
# Format code with black
black ekahau_bom/

# Lint with flake8
flake8 ekahau_bom/

# Lint with pylint
pylint ekahau_bom/

# Type checking with mypy
mypy ekahau_bom/
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure tests pass (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for detailed contribution guidelines.

---

## 📋 Requirements

### Runtime
- **Python** 3.7+
- **PyYAML** >= 6.0
- **openpyxl** >= 3.0.0 (for Excel export)
- **WeasyPrint** >= 60.0 (for PDF export, optional)
- **rich** >= 13.0.0 (for enhanced terminal output, optional)

### Development
- **pytest** >= 7.0.0
- **pytest-cov** >= 4.0.0
- **pytest-mock** >= 3.10.0
- **black** >= 22.0.0 (code formatting)
- **flake8** >= 5.0.0 (linting)
- **pylint** >= 2.15.0 (linting)
- **mypy** >= 0.990 (type checking)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Pavel Semenischev @htechno**

- GitHub: [@htechno](https://github.com/htechno)
- Telegram: [@htechno](https://t.me/htechno)

---

## 🙏 Acknowledgments

- Ekahau for creating amazing Wi-Fi design software
- The Wi-Fi engineering community for feedback and feature requests
- Contributors and users who help improve this tool

---

## 📚 Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Detailed usage examples and scenarios ([Русский](docs/USER_GUIDE.ru.md))
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Contributing and architecture ([Русский](docs/DEVELOPER_GUIDE.ru.md))
- **[Changelog](CHANGELOG.md)** - Version history and release notes

---

## 🔗 Related Tools

- [Ekahau AI Pro](https://www.ekahau.com/) - Professional Wi-Fi design platform
- [Ekahau Connect](https://www.ekahau.com/products/ekahau-connect/) - Free Wi-Fi survey tool

---

## 💡 Use Cases

### For Wi-Fi Engineers
- Generate accurate equipment lists for RFPs
- Analyze AP placement and mounting requirements
- Review radio configuration (channels, power, standards)
- Create professional project documentation

### For Procurement Teams
- Calculate project costs with volume discounts
- Generate purchase orders by vendor
- Track equipment quantities across floors/buildings
- Compare pricing scenarios

### For Installation Teams
- Get detailed mounting instructions (height, azimuth, tilt)
- Export location coordinates for each AP
- Review floor-by-floor installation requirements
- Generate work orders with equipment lists

### For Project Managers
- Track project scope and equipment counts
- Generate client-ready reports (HTML/Excel)
- Monitor costs and budget adherence
- Create documentation for handoff

---

## ❓ FAQ

**Q: What Ekahau versions are supported?**
A: All .esx format versions. Tag support requires Ekahau v10.2+.

**Q: Can I process multiple projects at once?**
A: Not yet. Batch processing is planned for a future release.

**Q: How do I customize the output format?**
A: Use `--format` option. Multiple formats can be generated simultaneously.

**Q: Can I add custom equipment prices?**
A: Yes! Edit `config/pricing.yaml` with your pricing data.

**Q: Does this work with large projects (500+ APs)?**
A: Yes! Tested with projects up to 1000+ APs. Performance is optimized.

**Q: Can I integrate this into my workflow/pipeline?**
A: Yes! Use JSON export format for API integrations and automation.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/htechno/EkahauBOM/issues)
- **Discussions**: [GitHub Discussions](https://github.com/htechno/EkahauBOM/discussions)

---

**Made with ❤️ for the Wi-Fi community**
