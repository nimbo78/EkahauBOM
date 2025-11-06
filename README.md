# EkahauBOM

> **Professional BOM generator + Web UI for Ekahau Wi-Fi projects**

Generate comprehensive equipment reports from Ekahau .esx files via **CLI** or **Web Interface**. Built for Wi-Fi engineers, procurement teams, and installation crews.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/nimbo78/EkahauBOM/actions/workflows/tests.yml/badge.svg)](https://github.com/nimbo78/EkahauBOM/actions/workflows/tests.yml)
[![Coverage: 86%](https://img.shields.io/badge/coverage-86%25-brightgreen.svg)](tests/)
[![Release](https://img.shields.io/github/v/release/nimbo78/EkahauBOM)](https://github.com/nimbo78/EkahauBOM/releases)

**English** | [Русский](README.ru.md)

---

## 🌟 What's New in v3.0.0

### 🎉 Web UI - Centralized Project Registry

Upload, process, and share Ekahau projects via web browser:

- **Drag-and-drop upload** with real-time processing
- **Project dashboard** with search and filters
- **Floor plan visualizations** with zoom/pan
- **Download reports** (CSV, Excel, HTML, PDF, JSON)
- **Short link sharing** for easy collaboration
- **No database required** - JSON-based storage

[See Web UI Guide](#-web-ui-new-in-v300) →

---

## Key Features

### 📊 Reports & Analytics

- **5 export formats**: CSV, Excel, HTML, JSON, PDF
- **Radio analytics**: Frequency bands, channels, TX power, Wi-Fi standards
- **Cost calculation**: Equipment pricing with volume discounts
- **Installation params**: Mounting height, azimuth, tilt, coordinates
- **Cable infrastructure**: Length calculations, BOM, cost estimation
- **Map notes**: Text notes, cable paths, picture markers

### 🗺️ Floor Plan Visualizations

- **AP placement overlay** with Ekahau colors
- **Azimuth arrows** for directional antennas
- **Adjustable opacity** (10-100%)
- **High-res PNG export** for documentation

---

## 🚀 Quick Start

### Option 1: Web UI (Recommended)

```bash
# Clone repository
git clone https://github.com/nimbo78/EkahauBOM.git
cd EkahauBOM

# Setup backend
cd ekahau_bom_web/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend/ekahau-bom-ui
npm install

# Run servers (2 terminals)
# Terminal 1 - Backend
cd ekahau_bom_web/backend
uvicorn app.main:app --port 8001

# Terminal 2 - Frontend
cd ekahau_bom_web/frontend/ekahau-bom-ui
npm start

# Open http://localhost:4200
```

### Option 2: CLI Only

```bash
pip install ekahau-bom

ekahau-bom myproject.esx \
  --format csv,excel,html \
  --visualize-floor-plans \
  --show-azimuth-arrows
```

---

## 🖥️ Web UI _(New in v3.0.0)_

### Upload & Process

![Upload Interface](docs/images/webui-upload.png)

Drag-and-drop .esx files with instant upload and processing queue.

**Keyboard Shortcuts**: Navigate faster with global shortcuts:
- `Alt+U` - Quick upload (admin only)
- `Ctrl+K` or `/` - Focus search
- `Escape` - Clear search
- `←/→` - Navigate between tabs
- `1-4` - Jump to specific tab

### Project Dashboard

![Projects List](docs/images/webui-projects.png)

Search, filter, and manage all uploaded projects. Real-time status tracking.

### Floor Plan Visualizations

![Floor Plans](docs/images/webui-visualizations.png)

Interactive floor plans with zoom/pan and lightbox modal for full-screen viewing.

### Reports Download

![Reports Tab](docs/images/webui-reports.png)

Download reports in all formats directly from browser.

### Configuration

![Processing Config](docs/images/webui-processing.png)

Configure all processing options via web interface:
- Grouping (by model, floor, vendor, color, tag)
- Output formats (CSV, Excel, HTML, PDF, JSON)
- Visualizations with azimuth arrows and custom opacity
- Real-time progress tracking

### Archive Management

**Automatic space savings**: Old projects (not accessed for 60+ days) are automatically compressed to tar.gz archives, saving 60-70% disk space. Projects are transparently decompressed on first access.

**Background job** (optional, requires cron/Task Scheduler):
```bash
# Run weekly to archive old projects
python -m app.tasks.archive_old_projects
```

---

## 📖 CLI Usage

### Basic Export

```bash
# Simple CSV export
ekahau-bom project.esx

# Multiple formats
ekahau-bom project.esx --format csv,excel,html,pdf

# Custom output directory
ekahau-bom project.esx --output-dir ./reports
```

### Grouping & Analytics

```bash
# Group by AP model
ekahau-bom project.esx --group-by model

# Group by floor
ekahau-bom project.esx --group-by floor

# Group by vendor
ekahau-bom project.esx --group-by vendor
```

### Floor Plan Visualizations

```bash
# Generate floor plans with APs
ekahau-bom project.esx --visualize-floor-plans

# With azimuth arrows
ekahau-bom project.esx \
  --visualize-floor-plans \
  --show-azimuth-arrows

# Custom opacity (0.0-1.0)
ekahau-bom project.esx \
  --visualize-floor-plans \
  --ap-opacity 0.4

# Hide AP names on visualizations
ekahau-bom project.esx \
  --visualize-floor-plans \
  --no-ap-names
```

### Advanced Options

```bash
# Custom project name (for reports)
ekahau-bom project.esx --project-name "Office Building 2024"

# Custom AP circle radius (for visualizations)
ekahau-bom project.esx \
  --visualize-floor-plans \
  --ap-circle-radius 20

# Enable verbose logging
ekahau-bom project.esx --verbose
```

---

## 📁 Output Structure

```
output/
├── Project_Name_access_points.csv          # Main BOM
├── Project_Name_access_points_detailed.csv # Full AP details
├── Project_Name_antennas.csv               # Antenna inventory
├── Project_Name_analytics.csv              # Radio analytics
├── Project_Name_report.xlsx                # Excel workbook
├── Project_Name_report.html                # Interactive HTML
├── Project_Name_report.pdf                 # Print-ready PDF
├── Project_Name_data.json                  # Complete JSON
└── visualizations/                         # Floor plans
    ├── Floor_1_visualization.png
    └── Floor_2_visualization.png
```

---

## 🛠️ Installation

### Prerequisites

- **Python 3.7+** (for CLI and backend)
- **Node.js 18+** (for Web UI frontend only)
- **Git** (to clone repository)

### Full Installation (Web UI + CLI)

```bash
git clone https://github.com/nimbo78/EkahauBOM.git
cd EkahauBOM

# Backend
cd ekahau_bom_web/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend/ekahau-bom-ui
npm install
```

### CLI Only

```bash
pip install ekahau-bom
```

### Optional: PDF Export Support

PDF export requires WeasyPrint + GTK libraries:

**Linux (Ubuntu/Debian)**:
```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
pip install weasyprint
```

**macOS**:
```bash
brew install pango gdk-pixbuf libffi
pip install weasyprint
```

**Windows**:
```bash
pip install weasyprint
# Download GTK3 Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
```

---

## 📚 Documentation

- [**CLI Reference**](docs/CLI_REFERENCE.md) - Complete command-line options
- [**Developer Guide**](docs/DEVELOPER_GUIDE.md) - Contributing and development
- [**Extending Guide**](docs/EXTENDING.md) - Add custom exporters/processors
- [**Release Process**](RELEASE_PROCESS.md) - How to create releases

---

## 🎯 Use Cases

### For Wi-Fi Engineers
- Generate professional BOMs from Ekahau designs
- Share projects via Web UI with stakeholders
- Visualize AP placements on floor plans
- Export installation parameters (height, azimuth, tilt)

### For Procurement Teams
- Equipment lists with quantities and models
- Cost calculations with volume discounts
- Vendor breakdown for multi-vendor deployments
- Cable infrastructure BOM and costs

### For Installation Crews
- Detailed AP locations with coordinates
- Mounting instructions (height, azimuth, tilt)
- Floor-by-floor installation guides
- Visual floor plans for reference

### For Project Managers
- Centralized project repository (Web UI)
- Share reports via short links
- Track processing status
- Quick project statistics

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=ekahau_bom --cov-report=html

# Backend API tests only
pytest ekahau_bom_web/backend/tests/ -v
```

**Current stats**: 545 tests passing | 86% coverage

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/nimbo78/EkahauBOM/issues)
- **Author**: Igor Singosin

---

**Built with ❤️ for the Wi-Fi engineering community**
