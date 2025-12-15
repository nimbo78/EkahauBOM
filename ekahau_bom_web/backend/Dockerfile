# EkahauBOM Web Backend Dockerfile
# Build from project root: docker build -f ekahau_bom_web/backend/Dockerfile .

FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Copy the main ekahau-bom CLI package first (for layer caching)
COPY pyproject.toml README.md ./
COPY ekahau_bom/ ./ekahau_bom/

# Install the main ekahau-bom package with all extras
RUN pip install ".[all]"

# Copy backend pyproject.toml and install dependencies
COPY ekahau_bom_web/backend/pyproject.toml ./backend/
WORKDIR /build/backend
RUN pip install .

# -----------------------------------
# Final stage
# -----------------------------------
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # WeasyPrint/Pango environment
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# Install runtime dependencies for WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY ekahau_bom_web/backend/app/ ./app/

# Create data directories
RUN mkdir -p /data/projects /data/batches /data/temp /data/archives

# Create non-root user
RUN groupadd -r ekahau && useradd -r -g ekahau ekahau && \
    chown -R ekahau:ekahau /app /data

USER ekahau

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
