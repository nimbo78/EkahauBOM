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

## Storage Backends

The backend supports **pluggable storage backends** for project files:
- **Local Filesystem** (default) - Files stored in `PROJECTS_DIR`
- **S3-Compatible Storage** - AWS S3, MinIO, Wasabi, DigitalOcean Spaces, etc.

### Local Storage (Default)

```bash
# .env
STORAGE_BACKEND=local
PROJECTS_DIR=./projects
```

No additional configuration needed. All project files are stored in the local filesystem.

### S3-Compatible Storage

Supports AWS S3, MinIO, Wasabi, DigitalOcean Spaces, Dell EMC ECS, IBM Cloud Object Storage, and any S3-compatible storage.

#### AWS S3 Configuration

```bash
# .env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=ekahau-bom-projects
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**AWS Setup**:
1. Create S3 bucket: `aws s3 mb s3://ekahau-bom-projects --region us-east-1`
2. Create IAM user with S3 permissions
3. Attach policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ekahau-bom-projects",
        "arn:aws:s3:::ekahau-bom-projects/*"
      ]
    }
  ]
}
```

#### MinIO Configuration (Self-Hosted)

```bash
# .env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=ekahau-bom
S3_REGION=us-east-1
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_USE_SSL=false
```

**MinIO Setup**:
```bash
# Start MinIO with Docker
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Create bucket
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/ekahau-bom
```

#### Wasabi Configuration

```bash
# .env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=my-bucket
S3_REGION=us-east-1
S3_ENDPOINT_URL=https://s3.wasabisys.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

#### DigitalOcean Spaces Configuration

```bash
# .env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=my-space
S3_REGION=nyc3
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

#### Corporate S3 with Custom CA Certificate

```bash
# .env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.company.internal
S3_BUCKET_NAME=ekahau-bom
S3_VERIFY=false  # or path to CA bundle
# S3_CA_BUNDLE=/path/to/ca-bundle.crt
```

### Storage Migration

Migrate projects between local and S3 storage:

```bash
# Migrate all projects from local to S3
python -m app.utils.migrate_storage local-to-s3 --all

# Migrate specific project from S3 to local
python -m app.utils.migrate_storage s3-to-local --project-id 550e8400-e29b-41d4-a716-446655440000

# Dry run (preview without migrating)
python -m app.utils.migrate_storage local-to-s3 --all --dry-run
```

**Migration Features**:
- Copies all project files, reports, and visualizations
- Preserves metadata and structure
- Progress tracking
- Automatic error recovery
- Dry-run mode for testing

### Archiving Behavior

**Local Storage**: Projects are archived to `.tar.gz` files after 60 days of inactivity to save disk space (~60-70% compression).

**S3 Storage**: Archiving is **automatically skipped** since S3 already provides efficient storage. Use S3 lifecycle policies for cost optimization instead.

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
│   ├── config.py         # Settings (including storage backend config)
│   ├── models.py         # Pydantic models
│   ├── api/              # API endpoints
│   │   ├── upload.py     # File upload endpoints
│   │   ├── projects.py   # Projects endpoints
│   │   └── reports.py    # Reports endpoints
│   ├── services/         # Business logic
│   │   ├── storage/      # Storage abstraction layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # StorageBackend interface
│   │   │   ├── local.py      # Local filesystem implementation
│   │   │   ├── s3.py         # S3-compatible storage implementation
│   │   │   └── factory.py    # Backend factory
│   │   ├── storage_service.py  # High-level storage operations
│   │   ├── index.py      # In-memory indexing
│   │   ├── processor.py  # EkahauBOM processing
│   │   ├── archive.py    # Project archiving (local storage only)
│   │   └── cache.py      # Response caching
│   ├── tasks/            # Background jobs
│   │   ├── archive_old_projects.py    # Archive old projects
│   │   └── cleanup_expired_links.py   # Remove expired links
│   └── utils/            # Utilities
│       ├── short_links.py
│       ├── migrate_storage.py  # Storage migration tool
│       ├── thumbnails.py       # Thumbnail generation
│       └── etag.py             # ETag utilities
├── tests/                # Tests
│   ├── test_storage_abstraction.py  # Local storage tests
│   ├── test_storage_s3.py           # S3 storage tests
│   └── ...               # Other tests
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
