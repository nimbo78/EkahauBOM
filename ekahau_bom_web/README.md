# Ekahau BOM Web Service

**Web interface for centralized Ekahau project management**

## Overview

This is a web-based service for processing and viewing Ekahau .esx project files. It provides:
- **Admin Panel**: Upload and process .esx files
- **User Interface**: Browse projects, view reports, and interactive visualizations
- **Short Links**: Share projects with expiring links
- **REST API**: Programmatic access to all features

## Architecture

```
Frontend (Angular + Taiga UI)
    ↓ REST API (HTTP/JSON)
Backend (FastAPI)
    ↓ File System
Storage (JSON metadata + in-memory index)
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Processing**: EkahauBOM CLI integration
- **Storage**: File system with JSON metadata
- **Indexing**: In-memory cache for fast search

### Frontend
- **Framework**: Angular 16+
- **UI Library**: Taiga UI v4.60.0 (130+ enterprise components)
- **Features**: Drag & drop upload, interactive tables, floor plan visualizations

## Project Structure

```
ekahau_bom_web/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # API endpoints
│   │   ├── services/  # Business logic
│   │   └── models.py  # Pydantic models
│   └── tests/
├── frontend/          # Angular application
│   └── ekahau-bom-ui/
│       └── src/
│           └── app/
│               ├── features/  # Feature modules
│               └── core/      # Services & models
├── docker/            # Docker configuration
└── docs/              # Documentation
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- EkahauBOM package (v2.8.0+)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend/ekahau-bom-ui
npm install
npm start
```

Access the application at http://localhost:4200

## Features

### Administrative Panel
- Upload .esx files via drag & drop
- Configure processing options (grouping, formats, visualizations)
- Monitor processing status in real-time

### User Interface
- Browse all uploaded projects with search and filtering
- View project metadata (APs count, buildings, floors)
- Download reports in multiple formats (CSV, Excel, HTML)
- Interactive floor plan visualizations
- Short link sharing with expiration

### REST API
- Full CRUD operations for projects
- File upload and processing endpoints
- Report download endpoints
- OpenAPI/Swagger documentation at `/docs`

## Development

See [WEBUI_PLAN.md](../WEBUI_PLAN.md) for detailed implementation plan.

## Documentation

- [Implementation Plan](../WEBUI_PLAN.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [User Guide](docs/USER_GUIDE.md) (coming soon)

## License

Same as parent project (EkahauBOM)

## Related

- [EkahauBOM CLI](https://github.com/htechno/EkahauBOM)
- [Taiga UI](https://taiga-ui.dev)
