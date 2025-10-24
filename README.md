# EkahauBOM

Bill of Materials (BOM) generator for Ekahau AI project files.

EkahauBOM extracts equipment data from Ekahau .esx project files and generates comprehensive reports showing access points, antennas, and their quantities.

## Features

- Extract access points data (vendor, model, floor, color, tags, quantity)
- Extract antennas data with quantities
- **Filter access points** by floor, color, vendor, model, or tags
- **Group and analyze** by floor, color, vendor, model, or tag key
- **Tag support** for Ekahau v10.2+ projects
- Export to CSV format with tags
- Configurable color database
- Optimized performance for large projects
- Comprehensive error handling and logging
- Type-safe with full type hints
- Extensible architecture for future export formats (Excel, HTML, JSON, PDF)

## Installation

### From source

```bash
# Clone the repository
git clone https://github.com/nimbo78/EkahauBOM.git
cd EkahauBOM

# Install dependencies
pip install -r requirements.txt

# Optional: Install in development mode
pip install -e .
```

### As a package

```bash
pip install -e .
```

After installation, you can use the `ekahau-bom` command globally.

## Usage

### Basic usage

```bash
python EkahauBOM.py project.esx
```

### With options

```bash
# Specify output directory
python EkahauBOM.py project.esx --output-dir reports/

# Use custom colors configuration
python EkahauBOM.py project.esx --colors-config my_colors.yaml

# Enable verbose logging
python EkahauBOM.py project.esx --verbose

# Save logs to file
python EkahauBOM.py project.esx --log-file ekahau_bom.log
```

### Using installed command

```bash
ekahau-bom project.esx
ekahau-bom project.esx --output-dir reports/ --verbose
```

### Advanced usage: Filtering

Filter access points by various criteria:

```bash
# Filter by floor
python EkahauBOM.py project.esx --filter-floor "Floor 1,Floor 2"

# Filter by color
python EkahauBOM.py project.esx --filter-color "Yellow,Red"

# Filter by vendor
python EkahauBOM.py project.esx --filter-vendor "Cisco,Aruba"

# Filter by model
python EkahauBOM.py project.esx --filter-model "AP-515,AP-635"

# Filter by tags (can use multiple times)
python EkahauBOM.py project.esx --filter-tag "Location:Building A" --filter-tag "Zone:Office"

# Exclude specific items
python EkahauBOM.py project.esx --exclude-floor "Basement" --exclude-color "Gray"

# Combine multiple filters (AND logic)
python EkahauBOM.py project.esx \
  --filter-floor "Floor 1,Floor 2" \
  --filter-color "Yellow" \
  --filter-vendor "Cisco"
```

### Advanced usage: Grouping and Analytics

Group access points and display statistics:

```bash
# Group by floor
python EkahauBOM.py project.esx --group-by floor

# Group by color
python EkahauBOM.py project.esx --group-by color

# Group by vendor
python EkahauBOM.py project.esx --group-by vendor

# Group by model
python EkahauBOM.py project.esx --group-by model

# Group by specific tag key
python EkahauBOM.py project.esx --group-by tag --tag-key "Location"

# Combine filtering and grouping
python EkahauBOM.py project.esx \
  --filter-vendor "Cisco" \
  --group-by floor
```

## Output

The script generates two CSV files in the output directory:

- `{project_name}_access_points.csv`: Access points with vendor, model, floor, color, tags, and quantity
- `{project_name}_antennas.csv`: Antennas with model and quantity

When using `--group-by`, statistics are displayed in the console showing the distribution of access points by the selected dimension.

## Configuration

### Custom colors

You can customize color mappings by creating a YAML file:

```yaml
# my_colors.yaml
"#FFE600": "Yellow"
"#FF8500": "Orange"
"#CUSTOM": "My Custom Color"
```

Then use it with:

```bash
python EkahauBOM.py project.esx --colors-config my_colors.yaml
```

## Development

### Project Structure

```
EkahauBOM/
├── ekahau_bom/           # Main package
│   ├── cli.py            # Command-line interface
│   ├── parser.py         # .esx file parser
│   ├── models.py         # Data models (AccessPoint, Tag, etc.)
│   ├── constants.py      # Constants and defaults
│   ├── utils.py          # Utility functions
│   ├── filters.py        # Filtering logic
│   ├── analytics.py      # Grouping and analytics
│   ├── processors/       # Data processors
│   │   ├── access_points.py
│   │   ├── antennas.py
│   │   └── tags.py       # Tag processing
│   └── exporters/        # Export formats
│       ├── base.py
│       └── csv_exporter.py
├── config/               # Configuration files
│   └── colors.yaml       # Color database
├── tests/                # Test suite
├── output/               # Default output directory
├── EkahauBOM.py         # Main entry point
├── setup.py             # Package setup
└── requirements.txt     # Dependencies
```

### Running tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=ekahau_bom
```

### Code quality

```bash
# Format code
black ekahau_bom/

# Lint
flake8 ekahau_bom/
pylint ekahau_bom/

# Type checking
mypy ekahau_bom/
```

## Requirements

- Python 3.7+
- PyYAML >= 6.0

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Pavel Semenischev

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.