# Project Version Comparison

> **Track changes between Wi-Fi design revisions with visual diffs and detailed reports**

The Project Comparison feature provides a comprehensive way to identify, visualize, and document all changes between two versions of an Ekahau project. Perfect for design reviews, change management, and client communication.

---

## Key Capabilities

| Feature | Description |
|---------|-------------|
| **AP Inventory Tracking** | Detect added, removed, modified, moved, and renamed access points |
| **Visual Floor Diffs** | Color-coded floor plans with movement arrows |
| **Real Meter Distances** | Accurate distance calculations using project scale |
| **Radio Config Changes** | Track channel, power, and antenna modifications |
| **Export Reports** | CSV, HTML, JSON for documentation and integration |

---

## Change Detection

### Change Categories

| Status | Icon | Description |
|--------|------|-------------|
| **Added** | 🟢 | New AP in current version |
| **Removed** | 🔴 | AP deleted from previous version |
| **Modified** | 🟡 | Configuration changed (radio, color, tags) |
| **Moved** | 🔵→🟣 | Position changed (with movement arrows) |
| **Renamed** | 🟠 | Same location, different name |

### Tracked Fields

**Radio Settings:**
- Channel (2.4GHz, 5GHz, 6GHz)
- TX Power
- Channel Width
- Antenna Type

**Placement:**
- Floor Plan Location (X, Y coordinates)
- Mounting Height
- Azimuth
- Tilt

**Configuration:**
- AP Name
- Vendor
- Model
- Color
- Tags
- Enabled/Disabled

---

## Distance Accuracy

The comparison engine uses the project's **metersPerUnit** scale factor from Ekahau to calculate real-world distances:

```
Distance (meters) = Distance (units) × metersPerUnit
```

**Example:**
- AP moved from (685, 127) to (834, 109)
- Distance in units: ~149 units
- Project scale: 0.0215 m/unit
- **Actual distance: 3.2 meters**

This ensures accurate movement detection regardless of floor plan resolution or zoom level.

---

## Visual Diff Images

Floor plan visualizations show all changes at a glance:

```
Legend:
🟢 Green circle    = Added AP
🔴 Red circle      = Removed AP
🟡 Yellow circle   = Modified AP
🔵→🟣 Arrow        = Moved AP (old → new position)
🟠 Orange circle   = Renamed AP
```

**Features:**
- High-resolution PNG output
- Adaptive marker sizes based on floor plan dimensions
- Movement arrows with direction indicators
- Floor name labels
- Zoomable in Web UI lightbox

---

## Example Output

### Visual Diff (Floor Plan)

Here's a real example showing 3 moved APs on a floor plan. Blue circles show old positions, purple circles show new positions, with arrows indicating movement direction:

![Visual Diff Example](examples/comparison_output/diff_maga-flat.png)

*Example: 3 APs moved between project versions (1.4m, 2.0m, and 3.1m respectively)*

### CSV Report

Simple tabular format perfect for Excel:

```csv
AP Name,Status,Floor,Details
maga-ap01-01,moved,maga-flat,"Moved 1.4m: (215.8,224.6) → (154.4,207.7)"
maga-ap01-04,moved,maga-flat,"Moved 2.0m: (833.8,109.3) → (741.7,107.2)"
maga-ap01-05,moved,maga-flat,"Moved 3.1m: (960.8,470.2) → (868.7,362.2)"
```

[View full CSV example](examples/comparison_output/maga_comparison.csv)

### JSON Report

Structured data with full details:

```json
{
  "project_a_name": "maga",
  "project_b_name": "maga",
  "comparison_timestamp": "2025-12-17T00:29:04",
  "summary": {
    "old_total_aps": 11,
    "new_total_aps": 11,
    "total_changes": 3,
    "moved": 3,
    "unchanged": 8
  },
  "changes": [
    {
      "status": "moved",
      "ap_name": "maga-ap01-04",
      "floor": "maga-flat",
      "distance_moved": 1.98,
      "old_coords": [833.8, 109.3],
      "new_coords": [741.7, 107.2],
      "details": "Moved 2.0m: (833.8,109.3) → (741.7,107.2)",
      "field_changes": [
        {
          "field": "azimuth",
          "category": "placement",
          "old": 228.3,
          "new": 180.0
        }
      ]
    }
  ]
}
```

[View full JSON example](examples/comparison_output/maga_comparison.json) | [View HTML report](examples/comparison_output/maga_comparison.html)

---

## CLI Usage

### Compare Two .esx Files

```bash
# Basic comparison
python -m ekahau_bom old_design.esx --compare new_design.esx

# With all export formats
python -m ekahau_bom old_design.esx --compare new_design.esx \
    --format csv,excel,html,json

# Custom move threshold (default: 0.5 meters)
python -m ekahau_bom old_design.esx --compare new_design.esx \
    --move-threshold 1.0
```

### Output Files

```
output/
├── project_comparison.csv      # Changes table
├── project_comparison.html     # Visual HTML report
├── project_comparison.json     # Machine-readable data
└── diff_Floor1.png             # Visual diff per floor
```

---

## Web UI Integration

### Automatic Comparison on Update

When you update an existing project in the Web UI:

1. **Upload** new version with "Update existing" option
2. **Previous version** automatically saved as `previous.esx`
3. **Comparison runs** during processing
4. **Comparison tab** becomes active in project details

### Comparison Tab

The Comparison tab shows:

**Summary Cards:**
- Added / Removed / Modified / Moved / Renamed counts
- Previous vs Current total APs

**Visual Diff Gallery:**
- Thumbnail per floor
- Click to open full-size in lightbox
- Zoom and pan support

**Detailed Changes Table:**
- Filterable by status
- Field-level change details
- e.g., "5GHz TX Power: 5.0 → 8.0"

**Export Buttons:**
- Download CSV
- Download HTML
- Download JSON

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/comparison/{id}` | GET | Full comparison data |
| `/api/comparison/{id}/summary` | GET | Change counts only |
| `/api/comparison/{id}/diff/{floor}` | GET | Floor diff PNG image |
| `/api/comparison/{id}/report/{format}` | GET | Download report (csv/html/json) |

### Example Response

```json
{
  "project_a_name": "Design v1",
  "project_b_name": "Design v2",
  "comparison_timestamp": "2025-12-17T10:30:00",
  "total_changes": 5,
  "inventory": {
    "old_total_aps": 24,
    "new_total_aps": 26,
    "aps_added": 3,
    "aps_removed": 1,
    "aps_modified": 2,
    "aps_moved": 2
  },
  "ap_changes": [
    {
      "status": "moved",
      "ap_name": "AP-101",
      "floor_name": "Floor 1",
      "distance_moved": 3.21,
      "old_coords": [685.6, 127.3],
      "new_coords": [833.8, 109.3],
      "changes": [
        {
          "field_name": "5GHz_tx_power",
          "category": "radio",
          "old_value": "8.0",
          "new_value": "5.0"
        }
      ]
    }
  ]
}
```

---

## Use Cases

### Design Review

Compare draft and final versions to document all changes made during review:

```bash
python -m ekahau_bom draft.esx --compare final.esx --format html
# Open project_comparison.html in browser
```

### Change Management

Track what changed between site survey and as-built:

1. Upload initial design
2. After installation, update with as-built
3. Comparison tab shows all field modifications

### Client Communication

Generate professional reports showing design evolution:

- Visual diff images for presentations
- CSV exports for Excel analysis
- HTML reports for email attachments

### Troubleshooting

Identify accidental changes in coverage design:

- "Why did coverage change?"
- "Which APs were reconfigured?"
- "What moved since last week?"

---

## Technical Details

### Matching Strategy

APs are matched between versions using:

1. **Name matching** (primary) - Same AP name in both versions
2. **Position matching** (fallback) - Same location, different name (detects renames)

### Move Threshold

Default: **0.5 meters**

APs moved less than the threshold are considered "unchanged" for position. They may still appear as "modified" if other fields changed.

### Storage

Comparison data is stored with each project:

```
projects/{project_id}/
├── original.esx          # Current version
├── previous.esx          # Previous version (auto-saved)
└── comparison/
    ├── comparison_data.json
    ├── project_comparison.csv
    ├── project_comparison.html
    ├── project_comparison.json
    └── visualizations/
        ├── diff_Floor1.png
        └── diff_Floor2.png
```

---

## Best Practices

1. **Consistent naming** - Use the same AP naming convention between versions for accurate matching
2. **Set project scale** - Ensure metersPerUnit is properly calibrated in Ekahau
3. **Regular updates** - Update projects after each design iteration to maintain history
4. **Export before major changes** - Download reports before starting new revision

---

*For general usage, see [User Guide](USER_GUIDE.md) • For Web UI details, see [Web UI Guide](examples/WEB_UI_GUIDE.md)*
