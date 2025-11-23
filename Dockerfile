# Multi-stage build for optimized FastAPI + LangChain/LangGraph application

# Stage 1: Builder stage - Install dependencies
FROM python:3.13-slim as builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (faster and more reliable than pip)
RUN uv sync --frozen --no-dev

# Stage 2: Runtime stage - Minimal production image
FROM python:3.13-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser pyproject.toml ./

# Switch to non-root user
USER appuser

# Ensure we use the virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Expose the port FastAPI runs on
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# Run the FastAPI application using uvicorn
# Using --host 0.0.0.0 to bind to all interfaces (required for Docker)
# Using --workers 1 for LangChain/LangGraph compatibility (stateful workflows)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

