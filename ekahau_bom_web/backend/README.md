# Ekahau BOM Web - Backend

FastAPI backend for Ekahau BOM Web Service.

## Setup

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -e ".[dev]"
```

### Configuration
Copy `.env.example` to `.env` and configure settings.

## Running

### Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

Access API at:
- http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Production Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

### Run Tests
```bash
pytest tests/
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Code Quality

### Format Code
```bash
black app/ tests/
```

### Type Checking
```bash
mypy app/
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings
│   ├── models.py         # Pydantic models
│   ├── api/              # API endpoints
│   │   ├── upload.py     # File upload endpoints
│   │   ├── projects.py   # Projects endpoints
│   │   └── reports.py    # Reports endpoints
│   ├── services/         # Business logic
│   │   ├── storage.py    # File storage
│   │   ├── index.py      # In-memory indexing
│   │   ├── processor.py  # EkahauBOM processing
│   │   ├── archive.py    # Project archiving
│   │   └── cache.py      # Response caching
│   ├── tasks/            # Background jobs
│   │   ├── archive_old_projects.py    # Archive old projects
│   │   └── cleanup_expired_links.py   # Remove expired links
│   └── utils/            # Utilities
│       └── short_links.py
├── tests/                # Tests
├── pyproject.toml        # Dependencies
└── .env                  # Local configuration
```

## API Endpoints

### Health Check
- `GET /health` - Health check

### Upload
- `POST /api/upload` - Upload .esx file
- `POST /api/upload/{project_id}/process` - Start processing

### Projects
- `GET /api/projects` - List projects
- `GET /api/projects/{project_id}` - Get project details
- `GET /api/projects/short/{short_link}` - Get project by short link
- `DELETE /api/projects/{project_id}` - Delete project

### Reports
- `GET /api/reports/{project_id}/list` - List reports
- `GET /api/reports/{project_id}/download/{filename}` - Download report
- `GET /api/reports/{project_id}/visualization/{filename}` - Get visualization
- `GET /api/reports/{project_id}/original` - Download original .esx

## Background Jobs

### Archive Old Projects

Compress old projects (not accessed for 60+ days) to save disk space:

```bash
# Run manually
python -m app.tasks.archive_old_projects

# Schedule with cron (Linux/macOS)
# Add to crontab -e:
0 2 * * 0 cd /path/to/backend && ./venv/bin/python -m app.tasks.archive_old_projects

# Schedule with Task Scheduler (Windows)
# Create task that runs weekly:
# Program: C:\path\to\backend\venv\Scripts\python.exe
# Arguments: -m app.tasks.archive_old_projects
# Start in: C:\path\to\backend
```

**Archive criteria**:
- Processing status: COMPLETED
- Last accessed: > 60 days ago (or never accessed)
- Not already archived

**Space savings**: 60-70% compression ratio

### Cleanup Expired Links

Remove expired short links from projects:

```bash
# Run manually
python -m app.tasks.cleanup_expired_links

# Schedule daily at 3 AM
0 3 * * * cd /path/to/backend && ./venv/bin/python -m app.tasks.cleanup_expired_links
```
