# Configuration Examples

Configuration file examples for common scenarios.

## Table of Contents

- [Basic Configuration](#basic-configuration)
- [Pricing Configuration](#pricing-configuration)
- [Custom Colors](#custom-colors)
- [Production Workflow](#production-workflow)
- [Batch Processing](#batch-processing)
- [High-Performance](#high-performance)

---

## Basic Configuration

**File**: `config/config.yaml` (default)

Basic configuration with sensible defaults for most use cases.

```yaml
# config/config.yaml
export:
  output_dir: output
  formats:
    - csv
    - excel
  timestamp: false

filters:
  # No filters by default - process all equipment
  include_floors: []
  exclude_floors: []
  include_colors: []
  exclude_colors: []

logging:
  level: INFO  # Use DEBUG for troubleshooting
  file: null   # Set to path for file logging

excel:
  add_charts: true
  freeze_header: true
  auto_filter: true
```

**Usage:**
```bash
# Uses default config automatically
ekahau-bom project.esx
```

---

## Pricing Configuration

### Scenario 1: Enable Pricing with Discounts

**File**: `configs/with-pricing.yaml`

```yaml
# configs/with-pricing.yaml
pricing:
  enabled: true
  database: pricing.yaml
  volume_discounts: true
  default_discount: 10.0  # 10% partner discount

export:
  formats:
    - excel
    - pdf

excel:
  add_charts: true  # Include cost charts
```

**Usage:**
```bash
ekahau-bom project.esx --config configs/with-pricing.yaml
```

### Scenario 2: Custom Pricing Database

**File**: `configs/regional-pricing.yaml`

```yaml
# configs/regional-pricing.yaml
pricing:
  enabled: true
  database: pricing/eu-pricing.yaml  # Custom pricing file
  volume_discounts: false            # Fixed prices
  default_discount: 0.0

export:
  formats:
    - excel

excel:
  add_charts: true
```

**Custom Pricing Database** (`pricing/eu-pricing.yaml`):
```yaml
# pricing/eu-pricing.yaml
vendors:
  Cisco:
    "AIR-AP3802I-B-K9": 750.00
    "AIR-AP4800-B-K9": 1100.00
    "C9120AXI-B": 1050.00

  Aruba:
    "AP-515": 650.00
    "AP-535": 950.00
    "AP-635": 1250.00

volume_discounts:
  enabled: false  # Fixed pricing

labor:
  installation_per_ap: 150.00  # Installation cost per AP
  configuration_per_ap: 50.00  # Configuration cost per AP
```

**Usage:**
```bash
ekahau-bom project.esx --config configs/regional-pricing.yaml
```

---

## Custom Colors

### Scenario: Deployment Status Colors

**File**: `configs/deployment-colors.yaml`

```yaml
# configs/deployment-colors.yaml
colors:
  database: colors/deployment-status.yaml
  warn_unknown: true
  use_hex_fallback: true

export:
  formats:
    - excel
    - html

excel:
  add_charts: true  # Color distribution chart
```

**Custom Colors Database** (`colors/deployment-status.yaml`):
```yaml
# colors/deployment-status.yaml
# Color name to RGB mapping for deployment status

colors:
  # Planned APs
  Planned: [255, 255, 0]       # Yellow
  ToDeploy: [255, 165, 0]      # Orange

  # Deployed status
  Deployed: [0, 255, 0]        # Green
  Active: [0, 200, 0]          # Dark Green

  # Issues
  Issue: [255, 0, 0]           # Red
  Maintenance: [255, 140, 0]   # Dark Orange

  # Existing infrastructure
  Existing: [128, 128, 128]    # Gray
  ToRemove: [64, 64, 64]       # Dark Gray

  # Building phases
  Phase1: [0, 0, 255]          # Blue
  Phase2: [0, 128, 255]        # Light Blue
  Phase3: [128, 0, 255]        # Purple
```

**Usage:**
```bash
ekahau-bom project.esx \
  --config configs/deployment-colors.yaml \
  --colors-config colors/deployment-status.yaml
```

---

## Production Workflow

### Scenario: Professional Deliverables

**File**: `configs/production.yaml`

```yaml
# configs/production.yaml
# Complete production configuration for client deliverables

export:
  output_dir: deliverables
  formats:
    - csv
    - excel
    - html
    - json
    - pdf
  timestamp: true  # Add date/time to filenames

pricing:
  enabled: true
  database: pricing.yaml
  volume_discounts: true
  default_discount: 15.0

filters:
  # Exclude gray (existing) APs
  exclude_colors:
    - Gray
    - Grey

logging:
  level: INFO
  file: logs/production.log

excel:
  add_charts: true
  freeze_header: true
  auto_filter: true
  auto_width: true
  max_column_width: 50

html:
  include_charts: true
  responsive: true
  dark_mode_support: true

pdf:
  paper_size: A4
  orientation: portrait
  page_numbers: true

analytics:
  coverage: true
  mounting: true
  radio: true
  grouping: true
```

**Usage:**
```bash
ekahau-bom project.esx --config configs/production.yaml
```

**Output:**
```
deliverables/
├── project_20240115_143022.csv
├── project_20240115_143022.xlsx
├── project_20240115_143022.html
├── project_20240115_143022.json
├── project_20240115_143022.pdf
└── logs/
    └── production.log
```

---

## Batch Processing

### Scenario: Process Multiple Buildings

**File**: `configs/batch-processing.yaml`

```yaml
# configs/batch-processing.yaml
# Optimized for batch processing multiple projects

export:
  output_dir: batch-reports
  formats:
    - excel  # Faster than generating all formats
  timestamp: true

filters:
  # Exclude test/demo APs
  exclude_colors:
    - Gray
    - Black

logging:
  level: WARNING  # Reduce log noise
  file: logs/batch.log

batch:
  recursive: true
  continue_on_error: true  # Don't stop on failures
  summary_report: true

excel:
  add_charts: false  # Faster without charts
  auto_filter: true
  auto_width: true

performance:
  optimized_lookups: true
  cache_parsed_data: false  # Don't cache in batch mode

analytics:
  # Disable expensive analytics for speed
  coverage: false
  mounting: true
  radio: true
  grouping: false
```

**Usage:**
```bash
ekahau-bom --batch projects/ --config configs/batch-processing.yaml
```

**Directory structure:**
```
projects/
├── building-a/
│   ├── floor1.esx
│   └── floor2.esx
├── building-b/
│   └── warehouse.esx
└── campus.esx
```

**Output:**
```
batch-reports/
├── building-a_floor1_20240115.xlsx
├── building-a_floor2_20240115.xlsx
├── building-b_warehouse_20240115.xlsx
├── campus_20240115.xlsx
└── batch_summary.xlsx
```

---

## High-Performance

### Scenario: Large Projects (500+ APs)

**File**: `configs/high-performance.yaml`

```yaml
# configs/high-performance.yaml
# Optimized for large projects with many access points

export:
  output_dir: output
  formats:
    - csv    # Fastest format
    - excel  # Add Excel if needed
  timestamp: false

logging:
  level: WARNING  # Minimal logging
  file: null      # No file logging for speed

excel:
  add_charts: false      # Skip chart generation
  freeze_header: true
  auto_filter: true
  auto_width: false      # Skip width calculation
  max_column_width: 30

html:
  include_charts: false  # Skip JavaScript charts
  responsive: false
  dark_mode_support: false

analytics:
  # Disable expensive analytics
  coverage: false
  mounting: false
  radio: false
  grouping: false

performance:
  optimized_lookups: true
  cache_parsed_data: true  # Cache for multiple exports

advanced:
  strict_mode: false
  validate_data: false  # Skip validation for speed
  max_access_points: 0  # No limit
```

**Usage:**
```bash
ekahau-bom large-project.esx --config configs/high-performance.yaml
```

**Performance comparison** (1000 APs):
- Default config: ~45 seconds
- High-performance config: ~15 seconds

---

## Advanced Examples

### Scenario 1: Filter Cisco Only with Pricing

**File**: `configs/cisco-only.yaml`

```yaml
# configs/cisco-only.yaml
filters:
  include_vendors:
    - Cisco

pricing:
  enabled: true
  volume_discounts: true

export:
  formats:
    - excel
    - pdf

grouping:
  group_by: model  # Group by AP model

excel:
  add_charts: true
```

**Usage:**
```bash
ekahau-bom project.esx --config configs/cisco-only.yaml
```

### Scenario 2: Per-Floor Reports

**File**: `configs/floor-template.yaml`

```yaml
# configs/floor-template.yaml
# Use with script to generate per-floor reports

export:
  output_dir: reports  # Will be overridden by script
  formats:
    - excel
    - pdf
  timestamp: false

excel:
  add_charts: true
  freeze_header: true

pdf:
  paper_size: A4
  orientation: landscape  # Better for wide tables
  page_numbers: true
```

**Bash script** (`process-floors.sh`):
```bash
#!/bin/bash
PROJECT=$1

for floor in "Floor 1" "Floor 2" "Floor 3" "Roof"; do
  echo "Processing $floor..."
  ekahau-bom "$PROJECT" \
    --config configs/floor-template.yaml \
    --filter-floor "$floor" \
    --output-dir "reports/$floor/"
done
```

**Usage:**
```bash
./process-floors.sh project.esx
```

### Scenario 3: Comparison Report (Two Vendors)

**File**: `configs/vendor-comparison.yaml`

```yaml
# configs/vendor-comparison.yaml
pricing:
  enabled: true
  volume_discounts: true
  default_discount: 0  # No discount for fair comparison

export:
  formats:
    - excel
  timestamp: false

grouping:
  group_by: vendor

excel:
  add_charts: true  # Comparison charts

analytics:
  coverage: true
  mounting: true
  radio: true
  grouping: true
```

**Bash script** (`compare-vendors.sh`):
```bash
#!/bin/bash
PROJECT=$1

# Cisco option
ekahau-bom "$PROJECT" \
  --config configs/vendor-comparison.yaml \
  --filter-vendor Cisco \
  --output-dir comparison/cisco/

# Aruba option
ekahau-bom "$PROJECT" \
  --config configs/vendor-comparison.yaml \
  --filter-vendor Aruba \
  --output-dir comparison/aruba/

echo "Comparison reports generated in comparison/"
```

---

## Configuration Hierarchy

Configuration sources (in order of precedence):

1. **Command-line arguments** (highest priority)
2. **Custom config file** (`--config`)
3. **Default config file** (`config/config.yaml`)
4. **Built-in defaults** (lowest priority)

**Example:**
```bash
# CLI argument overrides config file
ekahau-bom project.esx \
  --config configs/production.yaml \
  --format csv  # Overrides formats in production.yaml
```

---

## Tips & Best Practices

### Organization

**Recommended directory structure:**
```
configs/
├── production.yaml       # Client deliverables
├── development.yaml      # Testing/development
├── batch-processing.yaml # Batch operations
├── cisco-only.yaml       # Vendor-specific
├── aruba-only.yaml
└── high-performance.yaml # Large projects

pricing/
├── us-pricing.yaml       # US market prices
├── eu-pricing.yaml       # European prices
└── partner-pricing.yaml  # Partner discounts

colors/
├── deployment-status.yaml
├── building-phases.yaml
└── vendor-colors.yaml
```

### Version Control

**Add to `.gitignore`:**
```
# Sensitive pricing information
pricing/*-confidential.yaml
pricing/*-internal.yaml

# Temporary configs
configs/temp-*.yaml
configs/test-*.yaml
```

### Documentation

**Include README in configs directory:**
```
configs/README.md
```

Example README:
```markdown
# Configuration Files

- `production.yaml` - For client deliverables (all formats, pricing)
- `development.yaml` - For testing (minimal output, verbose logging)
- `batch-processing.yaml` - For processing multiple projects
- `high-performance.yaml` - For large projects (optimized)

## Usage

See [Configuration Examples](../docs/examples/config-examples.md)
```

---

## Troubleshooting

### Invalid YAML syntax

```yaml
# ❌ Wrong: Unquoted strings with special characters
filter_floor: Floor 1: Main Hall

# ✅ Correct: Use quotes
filter_floor: "Floor 1: Main Hall"
```

### Path issues

```yaml
# ❌ Wrong: Windows path without escaping
database: C:\pricing\prices.yaml

# ✅ Correct: Use forward slashes or escape
database: C:/pricing/prices.yaml
# or
database: "C:\\pricing\\prices.yaml"
```

### List vs single value

```yaml
# ❌ Wrong: Single value where list expected
formats: excel

# ✅ Correct: Use list syntax
formats:
  - excel
# or
formats: [excel]
```

---

## See Also

- **[CLI Reference](CLI_REFERENCE.md)** - Command-line options
- **[User Guide](USER_GUIDE.md)** - Usage scenarios
- **[Default Config](../../config/config.yaml)** - Full default configuration

---

**Last Updated**: 2025-10-28
