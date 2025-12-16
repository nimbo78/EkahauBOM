"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    batches,
    comparison,
    notes,
    projects,
    reports,
    schedules,
    templates,
    upload,
    websocket,
)
from app.config import settings
from app.services.index import index_service
from app.services.scheduler_service import scheduler_service
from app.services.batch_service import batch_service
from app.services.storage_service import storage_service
from app.services.notification_service import notification_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events - startup and shutdown."""
    # Startup: Load index from disk
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.index_file.parent.mkdir(parents=True, exist_ok=True)

    index_service.load_from_disk()
    print(f"Loaded {index_service.count()} projects from index")

    # Inject services into scheduler for batch processing
    scheduler_service.set_services(
        batch_service=batch_service,
        storage_service=storage_service,
        notification_service=notification_service,
    )
    # Start scheduler (now that event loop is running)
    scheduler_service.start()
    print("Scheduler services injected and started")

    yield

    # Shutdown: Save index to disk and stop scheduler
    scheduler_service.shutdown()
    index_service.save_to_disk()
    print("Index saved to disk, scheduler stopped")


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
app.include_router(comparison.router, prefix=settings.api_prefix)
app.include_router(batches.router, prefix=settings.api_prefix)
app.include_router(templates.router, prefix=settings.api_prefix)
app.include_router(schedules.router, prefix=settings.api_prefix)
app.include_router(websocket.router, prefix=settings.api_prefix)  # WebSocket at /api/ws


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
