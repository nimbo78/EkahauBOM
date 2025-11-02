# Web UI Visual Guide

> **Less text, more pictures!** 📸

## Quick Overview

Ekahau BOM Web UI provides a modern interface for managing and analyzing Ekahau project files.

**Key Features**: Upload projects • Process data • View reports • Interactive visualizations • Share with short links

---

## 📊 Projects Dashboard

Browse all your projects with statistics and filters.

![Projects List](web_ui_screenshots/01-projects-list.png)

**What you see**:
- Total/Pending/Processing/Completed counters
- Search and status filters
- Project list with short links
- Quick actions: View, Configure, Delete

---

## 📤 Upload Project

Drag & drop your `.esx` files or browse to upload.

![Upload Page](web_ui_screenshots/02-upload-page.png)

**Supported**: `.esx` files up to 500 MB

---

## 📋 Project Overview

Complete project information and metadata.

![Project Detail - Overview](web_ui_screenshots/03-project-detail-overview.png)

**Displays**:
- Processing status and short link
- Customer, Location, Responsible person
- Access Points, Antennas, Vendors counts
- Floors and Color codes
- Processing options used

---

## 📄 Reports Tab

Download generated reports in multiple formats.

![Project Detail - Reports](web_ui_screenshots/04-project-detail-reports.png)

**Available formats**:
- CSV (access points, detailed, analytics, antennas)
- Excel (`.xlsx`)
- JSON (complete data)
- HTML (interactive)
- PDF (printable)

---

## 🗺️ Floor Plan Visualizations

Interactive floor plans with AP positions and details.

![Project Detail - Visualizations](web_ui_screenshots/05-project-detail-visualizations.png)

**Features**:
- Clickable thumbnails
- Download as PNG
- Full-screen lightbox view

---

## 🔍 Lightbox View

Full-screen visualization with zoom and download.

![Lightbox Fullscreen](web_ui_screenshots/06-lightbox-fullscreen.png)

**Controls**:
- Click outside or X button to close
- Download button in footer
- High-resolution images
- Access Point markers with names
- Azimuth direction arrows (if enabled)

---

## 🚀 Getting Started

### 1. Start Backend (Terminal 1)
```bash
cd ekahau_bom_web/backend
./venv/Scripts/activate  # Windows
# or: source venv/bin/activate  # Linux/Mac
python -m uvicorn app.main:app --port 8001
```

### 2. Start Frontend (Terminal 2)
```bash
cd ekahau_bom_web/frontend/ekahau-bom-ui
npm start
```

### 3. Open Browser
Navigate to: **http://localhost:4200**

---

## 📦 Technology Stack

- **Frontend**: Angular 19+ • Taiga UI v4.60.0 • TypeScript
- **Backend**: FastAPI • Python 3.11+ • EkahauBOM CLI
- **Storage**: JSON metadata • File system • In-memory indexing

---

## 🔗 Links

- [Main README](../../README.md)
- [Web UI Documentation](../../ekahau_bom_web/README.md)
- [CLI Examples](README.md)
- [Configuration Examples](config-examples.md)

---

**Need help?** Open an issue on GitHub or check the documentation.
