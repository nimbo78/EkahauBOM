# Examples

This directory contains example outputs from EkahauBOM to demonstrate the tool's capabilities.

## Example Output Types

### 1. Floor Plan Visualizations
- **Description**: Floor plan images with AP positions overlaid
- **File Format**: PNG
- **Shows**:
  - Access Point locations with colored markers
  - AP names/labels
  - Mounting types (ceiling, wall, floor)
  - Azimuth direction arrows (for directional APs)

### 2. CSV Reports
- **Access Points Detailed**: Complete AP information with mounting heights, models, etc.
- **Access Points Summary**: Aggregated AP data by model
- **Antennas**: Antenna specifications
- **Radio Summary**: Radio configurations

### 3. Excel Reports
- **Format**: XLSX with multiple sheets
- **Sheets**: Project metadata, APs, Antennas, Radios, Analytics
- **Features**: Formatted tables, conditional formatting

### 4. HTML Reports
- **Format**: Interactive HTML with embedded CSS
- **Features**: Sortable tables, search functionality, responsive design

### 5. JSON Exports
- **Format**: Structured JSON data
- **Use Case**: API integration, data processing

## How to Generate Examples

```bash
# Generate all formats with visualizations
python -m ekahau_bom your_project.esx -o output/examples/ --csv --json --excel --html --visualize-floor-plans

# Generate only visualizations with azimuth arrows
python -m ekahau_bom your_project.esx -o output/examples/ --visualize-floor-plans --show-azimuth-arrows
```

## Contributing Examples

If you have interesting Ekahau projects and would like to contribute example outputs (with appropriate permissions), please open a pull request or issue.

**Note**: Do not include sensitive or proprietary project data in examples.
