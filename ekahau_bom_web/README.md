# Ekahau BOM Web Service

**Web interface for centralized Ekahau project management**

## Overview

This is a web-based service for processing and viewing Ekahau .esx project files. It provides:
- **Admin Panel**: Upload and process .esx files
- **User Interface**: Browse projects, view reports, and interactive visualizations
- **Short Links**: Share projects with expiring links
- **REST API**: Programmatic access to all features

## Current Status

**Version**: 0.1.0 (Development)
**Last Updated**: 2025-11-02

### Implementation Progress

- ✅ **Phase 1**: Environment Setup (Complete)
- ✅ **Phase 2**: Backend Development (Complete)
  - 13 REST API endpoints
  - StorageService, IndexService, ProcessorService
  - In-memory indexing with JSON persistence
  - Short link generation
- ✅ **Phase 3**: Frontend Development (Complete)
  - 6 Angular components (Upload, Processing, Projects List, Project Detail)
  - Taiga UI integration (25+ components used)
  - Reactive state management with Angular signals
  - Floor plan visualizations with Lightbox modal
- ⏳ **Phase 4**: Testing & Integration (In Progress)
  - ✅ Step 4.1: Backend Tests (69/69 passing)
  - ⏳ Step 4.2: Frontend Unit Tests (pending)
  - ✅ Step 4.3: E2E Testing (Playwright MCP - 5 scenarios)
- 📋 **Phase 5**: Deployment Preparation (Planned)
- 📋 **Phase 6**: Documentation (Planned)

### Test Coverage

**Backend**:
- **Total Tests**: 69 (100% passing)
- **Coverage**:
  - Storage Service: 100%
  - Index Service: 100%
  - Processor Service: 100%
  - API Endpoints: 100% (all 13 endpoints tested)

**E2E Testing**:
- Projects List page ✅
- Project Detail page (3 tabs) ✅
- Floor plan visualizations with Lightbox ✅
- Report downloads ✅
- Short links ✅

### Known Limitations

- Frontend unit tests not yet implemented (Phase 4.2)
- No Docker setup yet (Phase 5)
- Production configuration pending (Phase 5)

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

# Configure environment (see Configuration section below)
cp .env.example .env
# Edit .env with your settings

uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend/ekahau-bom-ui
npm install
npm start
```

Access the application at http://localhost:4200

## Configuration

### ⚠️ Important: Default Credentials

The application uses a `.env` file for configuration. **You must configure admin credentials before first use.**

**Default credentials:**
- Username: `admin`
- Password: `EkahauAdmin`

**To change credentials:**

1. Copy the example configuration:
   ```bash
   cd backend
   cp .env.example .env
   ```

2. Edit `backend/.env` file:
   ```env
   # Authentication & Security
   ADMIN_USERNAME=your_username
   ADMIN_PASSWORD=your_secure_password

   # JWT Secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
   JWT_SECRET_KEY=your_generated_secret_key
   ```

3. Restart the backend server to apply changes

### Configuration Options

The `.env` file supports the following settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `ADMIN_USERNAME` | Admin panel login username | `admin` |
| `ADMIN_PASSWORD` | Admin panel login password | `EkahauAdmin` |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | (must change in production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | `480` (8 hours) |
| `CORS_ORIGINS` | Allowed frontend origins | `["http://localhost:4200"]` |
| `MAX_UPLOAD_SIZE` | Max file upload size (bytes) | `524288000` (500MB) |

See [.env.example](backend/.env.example) for complete configuration reference.

### 🔒 Security Notes

- **Never commit `.env` file to git** - it's already in `.gitignore`
- Change default credentials in production
- Use strong, randomly generated JWT secret key
- In production, consider using a proper database with password hashing

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
