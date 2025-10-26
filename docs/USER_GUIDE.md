# EkahauBOM User Guide

Complete guide for using EkahauBOM to generate Bill of Materials from Ekahau projects.

**English** | [Русский](USER_GUIDE.ru.md)

## Table of Contents

- [Getting Started](#getting-started)
- [Basic Usage](#basic-usage)
- [Filtering](#filtering)
- [Grouping & Analytics](#grouping--analytics)
- [Export Formats](#export-formats)
- [Cost Calculation](#cost-calculation)
- [Advanced Usage](#advanced-usage)
  - [Configuration File](#configuration-file)
  - [Custom Colors Configuration](#custom-colors-configuration)
  - [Multiple Projects Workflow](#multiple-projects-workflow)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Ekahau .esx project file
- Installed dependencies (`pip install -r requirements.txt`)

### First Run

```bash
# Basic usage - generates CSV files
python EkahauBOM.py path/to/project.esx

# Output will be in ./output/ directory
```

---

## Basic Usage

### Generate Reports

```bash
# CSV format (default)
ekahau-bom project.esx

# Excel format (recommended)
ekahau-bom project.esx --format excel

# HTML format (interactive web report)
ekahau-bom project.esx --format html

# All formats at once
ekahau-bom project.esx --format csv,excel,html,json
```

### Specify Output Directory

```bash
ekahau-bom project.esx --output-dir /path/to/reports/
```

### Enable Logging

```bash
# Verbose output
ekahau-bom project.esx --verbose

# Save logs to file
ekahau-bom project.esx --log-file processing.log
```

---

## Filtering

### Filter by Floor

Include only specific floors:

```bash
ekahau-bom project.esx --filter-floor "Floor 1,Floor 2,Floor 3"
```

### Filter by Vendor

```bash
# Single vendor
ekahau-bom project.esx --filter-vendor "Cisco"

# Multiple vendors
ekahau-bom project.esx --filter-vendor "Cisco,Aruba"
```

### Filter by Color

Ekahau uses colors to mark different AP types:

```bash
ekahau-bom project.esx --filter-color "Yellow,Red"
```

### Filter by Model

```bash
ekahau-bom project.esx --filter-model "C9120AXI,AP-515"
```

### Filter by Tags

For Ekahau v10.2+ projects with tags:

```bash
# Single tag
ekahau-bom project.esx --filter-tag "Location:Building A"

# Multiple tags (AND logic)
ekahau-bom project.esx \
  --filter-tag "Location:Building A" \
  --filter-tag "Zone:Office"
```

### Exclude Items

```bash
# Exclude specific floors
ekahau-bom project.esx --exclude-floor "Basement,Roof"

# Exclude colors
ekahau-bom project.esx --exclude-color "Gray"
```

### Combined Filtering

```bash
# Example: Only Cisco APs on Floor 1 and 2, Yellow color
ekahau-bom project.esx \
  --filter-floor "Floor 1,Floor 2" \
  --filter-vendor "Cisco" \
  --filter-color "Yellow"
```

---

## Grouping & Analytics

### Group by Dimension

```bash
# Group by floor
ekahau-bom project.esx --group-by floor

# Group by vendor
ekahau-bom project.esx --group-by vendor

# Group by model
ekahau-bom project.esx --group-by model

# Group by color
ekahau-bom project.esx --group-by color
```

### Group by Tags

```bash
ekahau-bom project.esx --group-by tag --tag-key "Location"
```

### Combine with Filtering

```bash
# Group Cisco APs by floor
ekahau-bom project.esx \
  --filter-vendor "Cisco" \
  --group-by floor
```

---

## Export Formats

### CSV Export

Default format. Creates multiple files:

- `project_access_points.csv` - Aggregated AP list
- `project_access_points_detailed.csv` - Individual APs with installation params
- `project_antennas.csv` - Antenna list
- `project_analytics.csv` - Analytics data (if available)

**Best for:**
- Importing into other tools
- Database imports
- Simple spreadsheet analysis

### Excel Export

Professional multi-sheet workbook:

**Sheets:**
- Summary
- Access Points
- AP Installation Details
- Antennas
- By Floor (with chart)
- By Color (with chart)
- By Vendor (with chart)
- By Model (with chart)
- Radio Analytics (if data available)
- Mounting Analytics (if data available)
- Cost Breakdown (if --calculate-cost used)

**Best for:**
- Client presentations
- Procurement
- Project documentation
- Professional reports

### HTML Export

Interactive web report:

**Features:**
- Responsive design
- Chart.js visualizations
- Sortable tables
- Print-friendly
- Self-contained (no external files)

**Best for:**
- Email sharing
- Web publishing
- Presentations
- Quick viewing

### JSON Export

Machine-readable format:

**Structure:**
```json
{
  "metadata": {...},
  "summary": {...},
  "access_points": {
    "aggregated": [...],
    "details": [...]
  },
  "antennas": [...],
  "radio_analytics": {...},
  "mounting_analytics": {...}
}
```

**Best for:**
- API integrations
- Automated workflows
- Custom processing
- Data pipelines

---

## Cost Calculation

### Basic Cost Calculation

```bash
ekahau-bom project.esx --calculate-cost
```

Uses default pricing from `config/pricing.yaml`.

### Custom Discount

```bash
# Apply 15% discount
ekahau-bom project.esx --calculate-cost --discount 15
```

### Disable Volume Discounts

```bash
ekahau-bom project.esx --calculate-cost --no-volume-discounts
```

### Customize Pricing

Edit `config/pricing.yaml`:

```yaml
access_points:
  Cisco:
    C9120AXI: 850.00
    C9130AXI: 1200.00
  Aruba:
    AP-515: 750.00

volume_discounts:
  - min_quantity: 50
    discount_percent: 10.0
```

---

## Advanced Usage

### Configuration File

Create a configuration file to set default values for all options:

```yaml
# config/config.yaml or ~/.ekahau_bom/config.yaml

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
  volume_discounts: true

# Filters (optional defaults)
filters:
  exclude_colors:
    - Gray  # Exclude grey APs by default

# Logging
logging:
  level: INFO
  file: logs/ekahau_bom.log

# Excel export settings
excel:
  add_charts: true
  freeze_header: true
  auto_filter: true
```

Use custom configuration:

```bash
# Use specific config file
ekahau-bom project.esx --config my_config.yaml

# Use default config (config/config.yaml)
ekahau-bom project.esx
```

**Note:** CLI arguments always override configuration file values.

Example with config + CLI override:

```bash
# Config sets format: excel, but CLI overrides to HTML
ekahau-bom project.esx --format html
```

### Custom Colors Configuration

Create custom colors file:

```yaml
# my_colors.yaml
"#FFE600": "Yellow"
"#FF0000": "Red"
"#CUSTOM": "Custom Color"
```

Use it:

```bash
ekahau-bom project.esx --colors-config my_colors.yaml
```

### Multiple Projects Workflow

Process multiple projects:

```bash
for project in projects/*.esx; do
  ekahau-bom "$project" --output-dir "reports/$(basename $project .esx)/"
done
```

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Generate BOM
  run: |
    python EkahauBOM.py project.esx --format excel,html
    
- name: Upload Reports
  uses: actions/upload-artifact@v2
  with:
    name: reports
    path: output/
```

---

## Troubleshooting

### Common Issues

**Issue: "File not found"**
```
Solution: Check file path and ensure .esx extension
```

**Issue: "Invalid .esx file"**
```
Solution: File may be corrupted. Try re-exporting from Ekahau
```

**Issue: "No access points found"**
```
Solution: Ensure APs are marked as "mine" in Ekahau (not survey/neighbor APs)
```

**Issue: "Tags not working"**
```
Solution: Tags require Ekahau v10.2+. Older projects don't have tagKeys.json
```

**Issue: "Missing prices for equipment"**
```
Solution: Add equipment to config/pricing.yaml or use without --calculate-cost
```

### Debug Mode

```bash
# Enable verbose logging
ekahau-bom project.esx --verbose --log-file debug.log

# Check log file for detailed information
cat debug.log
```

### Performance Tips

**Large projects (500+ APs):**
- Use CSV format for fastest processing
- Excel generation takes longer due to charts
- HTML is slower for very large datasets

**Memory usage:**
- Projects up to 1000 APs: < 500MB
- Very large projects may benefit from closing other applications

---

## Tips & Best Practices

### For Wi-Fi Engineers

1. **Use tags in Ekahau** for better organization (Location, Zone, Type)
2. **Color-code APs** by type or vendor for visual clarity
3. **Export to Excel** for professional client presentations
4. **Include mounting data** in reports for installation teams

### For Procurement

1. **Use cost calculation** to generate accurate quotes
2. **Filter by vendor** to create separate purchase orders
3. **Group by floor** to track per-building costs
4. **Export to CSV** for easy import into procurement systems

### For Installation Teams

1. **Export detailed CSV** for mounting instructions
2. **Include azimuth/tilt** data in Excel reports
3. **Group by floor** to organize installation by level
4. **Print HTML reports** for on-site reference

### For Project Managers

1. **Use HTML export** for stakeholder presentations
2. **Track changes** by comparing exports from different design iterations
3. **Archive Excel reports** for project documentation
4. **Use JSON** for integration with project management tools

---

## Examples

### Example 1: Procurement Report

```bash
ekahau-bom office_building.esx \
  --format excel \
  --calculate-cost \
  --discount 12 \
  --output-dir procurement/
```

### Example 2: Installation Package

```bash
ekahau-bom warehouse.esx \
  --format csv,excel,html \
  --group-by floor \
  --output-dir installation_docs/
```

### Example 3: Filtered Vendor Report

```bash
ekahau-bom campus.esx \
  --filter-vendor "Cisco" \
  --filter-floor "Building A*" \
  --format excel \
  --output-dir cisco_quote/
```

### Example 4: Analytics Only

```bash
ekahau-bom project.esx \
  --format json \
  --group-by vendor \
  --output-dir analytics/
```

---

## Support & Resources

- **Documentation**: See README.md for feature overview
- **Issues**: https://github.com/htechno/EkahauBOM/issues
- **Discussions**: https://github.com/htechno/EkahauBOM/discussions

---

**Version**: 2.4.0  
**Last Updated**: 2024
