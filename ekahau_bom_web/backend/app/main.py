"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, batches, notes, projects, reports, templates, upload
from app.config import settings
from app.services.index import index_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events - startup and shutdown."""
    # Startup: Load index from disk
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.index_file.parent.mkdir(parents=True, exist_ok=True)

    index_service.load_from_disk()
    print(f"Loaded {index_service.count()} projects from index")

    yield

    # Shutdown: Save index to disk
    index_service.save_to_disk()
    print("Index saved to disk")


app = FastAPI(
    title="Ekahau BOM Web API",
    version="0.1.0",
    description="Web service for Ekahau BOM processing",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)  # Auth already has /api/auth prefix
app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(projects.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(notes.router, prefix=settings.api_prefix)
app.include_router(batches.router, prefix=settings.api_prefix)
app.include_router(templates.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ekahau BOM Web API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }
