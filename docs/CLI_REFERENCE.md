# CLI Reference

Complete command-line reference for EkahauBOM.

**English** | [Русский](CLI_REFERENCE.ru.md)

## Table of Contents

- [Basic Usage](#basic-usage)
- [Global Options](#global-options)
- [Export Formats](#export-formats)
- [Filtering Options](#filtering-options)
- [Grouping Options](#grouping-options)
- [Pricing Options](#pricing-options)
- [Batch Processing](#batch-processing)
- [Visualization Options](#visualization-options)
- [Examples](#examples)

---

## Basic Usage

```bash
ekahau-bom <esx_file> [OPTIONS]
```

**Positional Arguments:**

- `esx_file` - Path to Ekahau .esx project file
  - Optional if `--batch` is used
  - Can be absolute or relative path
  - Enclose paths with spaces in quotes

**Example:**
```bash
ekahau-bom project.esx
ekahau-bom "C:\Projects\My Office.esx"
ekahau-bom /home/user/wifi/warehouse.esx
```

---

## Global Options

### `--output-dir OUTPUT_DIR`

Specify output directory for generated files.

- **Type**: Path
- **Default**: `output`
- **Creates directory** if it doesn't exist

**Examples:**
```bash
# Relative path
ekahau-bom project.esx --output-dir reports/

# Absolute path
ekahau-bom project.esx --output-dir "C:\Reports\Office Building"

# Date-based directory
ekahau-bom project.esx --output-dir reports/2024-01-15/
```

### `--config CONFIG`

Path to configuration file.

- **Type**: Path
- **Default**: `config/config.yaml`
- **Format**: YAML

**Example:**
```bash
ekahau-bom project.esx --config custom-config.yaml
ekahau-bom project.esx -c configs/production.yaml
```

See [Configuration Files](#configuration-files) for details.

### `--colors-config COLORS_CONFIG`

Path to custom colors configuration file.

- **Type**: Path
- **Format**: YAML
- **Overrides** default color mappings

**Example:**
```bash
ekahau-bom project.esx --colors-config custom-colors.yaml
```

### `--verbose, -v`

Enable verbose logging (DEBUG level).

- **Type**: Flag
- **Default**: INFO level logging
- **Shows**: Detailed processing information

**Example:**
```bash
ekahau-bom project.esx --verbose
ekahau-bom project.esx -v
```

**Output includes:**
- File parsing details
- Data extraction steps
- Filter application
- Export generation progress

### `--log-file LOG_FILE`

Write logs to file.

- **Type**: Path
- **Optional**: Logs to console if not specified

**Example:**
```bash
ekahau-bom project.esx --log-file processing.log
ekahau-bom project.esx --log-file logs/$(date +%Y%m%d).log
```

### `--version`

Show program version and exit.

**Example:**
```bash
ekahau-bom --version
# Output: EkahauBOM version 2.7.0
```

---

## Export Formats

### `--format FORMAT`

Export format(s) to generate.

- **Type**: String (comma-separated)
- **Default**: `csv`
- **Options**: `csv`, `excel`, `html`, `json`, `pdf`
- **Multiple formats**: Separate with commas (no spaces)

**Single format:**
```bash
ekahau-bom project.esx --format csv
ekahau-bom project.esx --format excel
ekahau-bom project.esx --format json
```

**Multiple formats:**
```bash
ekahau-bom project.esx --format csv,excel
ekahau-bom project.esx --format csv,excel,html,json
ekahau-bom project.esx --format csv,excel,html,json,pdf
```

**Format Details:**

| Format | Files Generated | Use Case |
|--------|----------------|----------|
| `csv` | 4+ files | Data analysis, import to other tools |
| `excel` | 1 file (multi-sheet) | Professional reports, charts |
| `html` | 1 file | Interactive web viewing |
| `json` | 1 file | API integration, automation |
| `pdf` | 1 file | Print-ready professional reports |

**CSV Files Generated:**
- `project_access_points.csv` - Aggregated AP summary
- `project_access_points_detailed.csv` - Individual APs with installation parameters
- `project_antennas.csv` - Antenna specifications
- `project_radio_summary.csv` - Radio configurations

---

## Filtering Options

Filter which equipment to include in the output.

### `--filter-floor FILTER_FLOOR`

Filter by floor names (comma-separated).

**Examples:**
```bash
# Single floor
ekahau-bom project.esx --filter-floor "Floor 1"

# Multiple floors
ekahau-bom project.esx --filter-floor "Floor 1,Floor 2,Floor 3"

# Case-sensitive matching
ekahau-bom project.esx --filter-floor "First Floor,Second Floor"
```

### `--filter-color FILTER_COLOR`

Filter by AP colors (comma-separated).

**Examples:**
```bash
# Single color
ekahau-bom project.esx --filter-color Yellow

# Multiple colors
ekahau-bom project.esx --filter-color "Yellow,Red,Blue"

# Common workflow: Extract only planned APs (often yellow)
ekahau-bom project.esx --filter-color Yellow --format excel
```

### `--filter-vendor FILTER_VENDOR`

Filter by equipment vendors (comma-separated).

**Examples:**
```bash
# Single vendor
ekahau-bom project.esx --filter-vendor Cisco

# Multiple vendors
ekahau-bom project.esx --filter-vendor "Cisco,Aruba"

# Compare vendors
ekahau-bom project.esx --filter-vendor Cisco --output-dir reports/cisco/
ekahau-bom project.esx --filter-vendor Aruba --output-dir reports/aruba/
```

### `--filter-model FILTER_MODEL`

Filter by equipment models (comma-separated).

**Examples:**
```bash
# Single model
ekahau-bom project.esx --filter-model "AIR-AP3802I-B-K9"

# Multiple models
ekahau-bom project.esx --filter-model "AP-515,AP-635"

# Indoor APs only
ekahau-bom project.esx --filter-model "AP-515,AP-535,AP-555"
```

### `--filter-tag FILTER_TAG`

Filter by custom tags (Ekahau v10.2+).

- **Format**: `"TagKey:TagValue"`
- **Can be used multiple times** for AND logic
- **Case-sensitive**

**Examples:**
```bash
# Single tag
ekahau-bom project.esx --filter-tag "Location:Building A"

# Multiple tags (AND logic)
ekahau-bom project.esx \
  --filter-tag "Location:Building A" \
  --filter-tag "Zone:Office"

# Department-specific
ekahau-bom project.esx --filter-tag "Department:IT"
```

### Exclude Options

Inverse of filter options - exclude matching items.

**`--exclude-floor EXCLUDE_FLOOR`**
```bash
# Exclude basement
ekahau-bom project.esx --exclude-floor Basement

# Exclude multiple floors
ekahau-bom project.esx --exclude-floor "Parking,Basement,Rooftop"
```

**`--exclude-color EXCLUDE_COLOR`**
```bash
# Exclude existing/surveyed APs (often gray)
ekahau-bom project.esx --exclude-color Gray

# Exclude multiple colors
ekahau-bom project.esx --exclude-color "Gray,Black"
```

**`--exclude-vendor EXCLUDE_VENDOR`**
```bash
# Exclude specific vendor
ekahau-bom project.esx --exclude-vendor "Generic"
```

### Combining Filters

Filters can be combined for complex queries:

```bash
# Cisco APs on Floor 1, excluding gray
ekahau-bom project.esx \
  --filter-vendor Cisco \
  --filter-floor "Floor 1" \
  --exclude-color Gray

# Yellow and Red APs in Building A
ekahau-bom project.esx \
  --filter-color "Yellow,Red" \
  --filter-tag "Location:Building A"
```

---

## Grouping Options

Display statistics grouped by specific dimensions.

### `--group-by {floor,color,vendor,model,tag}`

Group results and show statistics.

**Options:**
- `floor` - Group by floor
- `color` - Group by AP color
- `vendor` - Group by vendor
- `model` - Group by model
- `tag` - Group by custom tag (requires `--tag-key`)

**Examples:**
```bash
# Group by floor
ekahau-bom project.esx --group-by floor

# Group by vendor
ekahau-bom project.esx --group-by vendor

# Group by color
ekahau-bom project.esx --group-by color
```

**Output includes:**
- Count per group
- Percentage distribution
- List of items in each group

### `--tag-key TAG_KEY`

Specify tag key when using `--group-by tag`.

**Example:**
```bash
# Group by Location tag
ekahau-bom project.esx --group-by tag --tag-key Location

# Group by Department tag
ekahau-bom project.esx --group-by tag --tag-key Department
```

**Combined with Excel:**
```bash
# Generate Excel report grouped by floor with charts
ekahau-bom project.esx --format excel --group-by floor
```

---

## Pricing Options

Calculate equipment costs and include in reports.

### `--enable-pricing`

Enable cost calculations.

- **Type**: Flag
- **Requires**: Pricing database file
- **Default file**: `config/pricing.yaml`

**Example:**
```bash
ekahau-bom project.esx --enable-pricing
```

**Includes in reports:**
- Unit prices
- Extended totals
- Volume discounts (if enabled)
- Grand total

### `--pricing-file PRICING_FILE`

Path to custom pricing database.

- **Type**: Path
- **Format**: YAML
- **Default**: `config/pricing.yaml`

**Example:**
```bash
# Custom pricing
ekahau-bom project.esx --enable-pricing --pricing-file prices/2024-q1.yaml

# Regional pricing
ekahau-bom project.esx --enable-pricing --pricing-file prices/eu-pricing.yaml
```

### `--discount DISCOUNT`

Additional discount percentage.

- **Type**: Number (0-100)
- **Default**: 0
- **Applied**: After volume discounts

**Examples:**
```bash
# 10% discount
ekahau-bom project.esx --enable-pricing --discount 10

# 15% partner discount
ekahau-bom project.esx --enable-pricing --discount 15

# 25% promotional discount
ekahau-bom project.esx --enable-pricing --discount 25
```

**Calculation:**
1. Base price from pricing file
2. Volume discount applied (if enabled)
3. Additional discount applied
4. Final price calculated

### `--no-volume-discounts`

Disable automatic volume-based discounts.

**Example:**
```bash
# Pricing without volume discounts
ekahau-bom project.esx --enable-pricing --no-volume-discounts

# Fixed pricing with custom discount
ekahau-bom project.esx --enable-pricing --no-volume-discounts --discount 20
```

**Default volume discounts:**
- 1-9 units: 0%
- 10-24 units: 5%
- 25-49 units: 10%
- 50-99 units: 15%
- 100+ units: 20%

---

## Batch Processing

Process multiple .esx files at once.

### `--batch BATCH`

Process all .esx files in directory.

- **Type**: Path (directory)
- **Searches**: Only direct children by default
- **Use with** `--recursive` for subdirectories

**Examples:**
```bash
# Process all files in directory
ekahau-bom --batch projects/

# Process with specific output
ekahau-bom --batch projects/ --output-dir batch-reports/

# Process with format
ekahau-bom --batch projects/ --format excel,pdf
```

### `--recursive`

Search for .esx files recursively.

- **Type**: Flag
- **Requires**: `--batch`
- **Searches**: All subdirectories

**Example:**
```bash
# Process all .esx files recursively
ekahau-bom --batch /projects/ --recursive

# Recursive with filters
ekahau-bom --batch projects/ --recursive --filter-vendor Cisco
```

**Directory structure example:**
```
projects/
├── building-a/
│   ├── floor1.esx
│   └── floor2.esx
├── building-b/
│   └── warehouse.esx
└── campus.esx
```

**Command:**
```bash
ekahau-bom --batch projects/ --recursive --format excel
```

**Output:**
```
batch-reports/
├── building-a_floor1_report.xlsx
├── building-a_floor2_report.xlsx
├── building-b_warehouse_report.xlsx
└── campus_report.xlsx
```

---

## Visualization Options

Generate floor plan images with AP placements.

### `--visualize-floor-plans`

Generate floor plan visualizations.

- **Type**: Flag
- **Requires**: Pillow library (`pip install Pillow`)
- **Output**: PNG files in `visualizations/` subdirectory

**Example:**
```bash
# Basic visualization
ekahau-bom project.esx --visualize-floor-plans

# Visualization with custom output
ekahau-bom project.esx --visualize-floor-plans --output-dir reports/
```

**Output:**
```
reports/
└── visualizations/
    ├── Floor_1_visualization.png
    ├── Floor_2_visualization.png
    └── Floor_3_visualization.png
```

### `--ap-circle-radius AP_CIRCLE_RADIUS`

AP marker circle radius in pixels.

- **Type**: Integer
- **Default**: 15
- **Range**: 5-50 (recommended)

**Examples:**
```bash
# Smaller markers
ekahau-bom project.esx --visualize-floor-plans --ap-circle-radius 10

# Larger markers
ekahau-bom project.esx --visualize-floor-plans --ap-circle-radius 25
```

### `--no-ap-names`

Hide AP names on visualizations.

- **Type**: Flag
- **Default**: Names shown
- **Use case**: Cleaner visualization, large deployments

**Example:**
```bash
# Visualization without AP names
ekahau-bom project.esx --visualize-floor-plans --no-ap-names
```

### `--show-azimuth-arrows`

Show azimuth direction arrows.

- **Type**: Flag
- **Shows**: Direction arrows for wall-mounted and directional APs
- **Useful for**: Installation verification

**Example:**
```bash
# Show antenna directions
ekahau-bom project.esx --visualize-floor-plans --show-azimuth-arrows

# Complete visualization
ekahau-bom project.esx --visualize-floor-plans \
  --show-azimuth-arrows \
  --ap-circle-radius 20
```

### `--ap-opacity AP_OPACITY`

AP marker opacity level.

- **Type**: Float (0.0-1.0)
- **Default**: 1.0 (100% opaque)
- **Use case**: See floor plan details through markers

**Examples:**
```bash
# Semi-transparent markers (75%)
ekahau-bom project.esx --visualize-floor-plans --ap-opacity 0.75

# More transparent (50%)
ekahau-bom project.esx --visualize-floor-plans --ap-opacity 0.5

# Complete visualization with transparency
ekahau-bom project.esx --visualize-floor-plans \
  --ap-opacity 0.75 \
  --show-azimuth-arrows \
  --ap-circle-radius 18
```

---

## Examples

### Basic Operations

**Generate CSV report:**
```bash
ekahau-bom project.esx
```

**Generate all formats:**
```bash
ekahau-bom project.esx --format csv,excel,html,json,pdf
```

**Custom output directory:**
```bash
ekahau-bom project.esx --output-dir "C:\Reports\Office Building"
```

### Filtering

**Single floor BOM:**
```bash
ekahau-bom project.esx --filter-floor "Floor 1" --format excel
```

**Cisco equipment only:**
```bash
ekahau-bom project.esx --filter-vendor Cisco --format csv,excel
```

**Planned APs (yellow) excluding basement:**
```bash
ekahau-bom project.esx \
  --filter-color Yellow \
  --exclude-floor Basement \
  --format excel
```

### Pricing

**BOM with pricing:**
```bash
ekahau-bom project.esx --enable-pricing --format excel
```

**Custom pricing with discount:**
```bash
ekahau-bom project.esx \
  --enable-pricing \
  --pricing-file prices/special-pricing.yaml \
  --discount 15 \
  --format excel,pdf
```

### Batch Processing

**Process all projects:**
```bash
ekahau-bom --batch projects/ --format excel --output-dir batch-reports/
```

**Recursive with pricing:**
```bash
ekahau-bom --batch /projects/ \
  --recursive \
  --enable-pricing \
  --format excel,pdf
```

### Visualization

**Basic floor plans:**
```bash
ekahau-bom project.esx --visualize-floor-plans
```

**Installation guide (with arrows):**
```bash
ekahau-bom project.esx \
  --visualize-floor-plans \
  --show-azimuth-arrows \
  --ap-opacity 0.8 \
  --format excel
```

**Clean visualization for presentations:**
```bash
ekahau-bom project.esx \
  --visualize-floor-plans \
  --no-ap-names \
  --ap-circle-radius 20 \
  --ap-opacity 0.75
```

### Advanced Workflows

**Compare two vendors:**
```bash
# Cisco BOM
ekahau-bom project.esx --filter-vendor Cisco \
  --output-dir reports/cisco/ --format excel --enable-pricing

# Aruba BOM
ekahau-bom project.esx --filter-vendor Aruba \
  --output-dir reports/aruba/ --format excel --enable-pricing
```

**Per-floor reports:**
```bash
for floor in "Floor 1" "Floor 2" "Floor 3"; do
  ekahau-bom project.esx --filter-floor "$floor" \
    --output-dir "reports/$floor/" --format excel,pdf
done
```

**Complete professional package:**
```bash
ekahau-bom project.esx \
  --format csv,excel,html,json,pdf \
  --enable-pricing \
  --visualize-floor-plans \
  --show-azimuth-arrows \
  --output-dir "deliverables/$(date +%Y-%m-%d)/" \
  --verbose \
  --log-file processing.log
```

---

## Tips & Best Practices

### Performance

- **Large projects**: Use specific formats instead of all formats
- **Batch processing**: Process during off-hours for large batches
- **Visualization**: Skip if not needed (adds processing time)

### Organization

- **Use date-based directories**: `--output-dir reports/2024-01-15/`
- **Descriptive names**: Include project name in output directory
- **Separate by purpose**: Different directories for pricing vs. technical

### Automation

**Bash script example:**
```bash
#!/bin/bash
PROJECT=$1
DATE=$(date +%Y-%m-%d)
OUTPUT="reports/${PROJECT}/${DATE}"

ekahau-bom "${PROJECT}.esx" \
  --output-dir "$OUTPUT" \
  --format csv,excel,pdf \
  --enable-pricing \
  --visualize-floor-plans \
  --verbose \
  --log-file "${OUTPUT}/processing.log"
```

**Python script example:**
```python
import subprocess
import sys
from pathlib import Path

def process_project(esx_file, output_dir):
    """Process Ekahau project with standard options."""
    cmd = [
        "ekahau-bom",
        str(esx_file),
        "--format", "csv,excel,pdf",
        "--enable-pricing",
        "--output-dir", str(output_dir),
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    process_project(sys.argv[1], "reports/")
```

---

## Troubleshooting

### Common Issues

**"File not found"**
```bash
# Use quotes for paths with spaces
ekahau-bom "My Project.esx"
ekahau-bom "C:\Projects\Office Building\design.esx"
```

**"No such file or directory: output"**
```bash
# Directory will be created automatically - check permissions
ekahau-bom project.esx --output-dir /path/with/permissions/
```

**PDF export fails**
```bash
# Install GTK3 libraries (see README.md for platform-specific instructions)
# On Windows: Download GTK3 Runtime installer
# On Linux: sudo apt-get install libgtk-3-0
# On macOS: brew install gtk+3
```

**Visualization fails**
```bash
# Install Pillow
pip install Pillow

# Or install all optional dependencies
pip install ekahau-bom[visualization]
```

### Debug Mode

Enable verbose logging for troubleshooting:
```bash
ekahau-bom project.esx --verbose --log-file debug.log
```

Check the log file for detailed error messages.

---

## See Also

- **[User Guide](USER_GUIDE.md)** - Detailed usage scenarios
- **[Configuration Guide](../config/README.md)** - Configuration files
- **[FAQ](../README.md#-faq)** - Frequently asked questions

---

**Version**: 2.7.0
**Last Updated**: 2025-10-28
