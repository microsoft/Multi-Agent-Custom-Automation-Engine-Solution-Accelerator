# Multi-stage Dockerfile for React frontend with Python backend support using UV

# Stage 1: Node build environment for React
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci --silent

# Copy source files
COPY . ./

RUN rm -rf node_modules && npm ci && npm rebuild esbuild --force

# Build the React app
RUN npm run build

# Stage 2: Python build environment with UV
FROM python:3.11-slim-bullseye AS python-builder

# Copy UV from official image
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

# Setup UV environment variables
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Copy Python project definition files
COPY pyproject.toml requirements.txt* uv.lock* ./

# Install Python dependencies using UV
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f "requirements.txt" ]; then \
      uv pip install --system -r requirements.txt && uv pip install --system "uvicorn[standard]";  \
    else \
      uv pip install --system pyproject.toml && uv pip install --system "uvicorn[standard]"; \
    fi

# Stage 3: Final production image
FROM python:3.11-slim-bullseye

# Set production environment
ENV NODE_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* 

WORKDIR /app

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/static && \
    chown -R appuser:appuser /app

# Copy Python dependencies from builder
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy React build artifacts
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/build /app/build

# Copy Python application code
COPY --chown=appuser:appuser ./*.py /app/

# Create log directory with correct permissions
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Use non-root user for security
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Run the application with uvicorn
CMD ["/usr/local/bin/uvicorn", "frontend_server:app", "--host", "0.0.0.0", "--port", "3000"]