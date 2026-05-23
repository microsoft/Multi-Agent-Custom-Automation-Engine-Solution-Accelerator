# Base Python image
FROM python:3.11-slim-bullseye AS base
WORKDIR /app

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install the project's dependencies using the lockfile and settings
COPY uv.lock pyproject.toml /app/
RUN uv sync --frozen --no-install-project --no-dev

# Backend app setup
COPY . /app  
RUN uv sync --frozen --no-dev
# Fix: agent-framework-azure-ai-search ships an empty agent_framework/__init__.py
# that overwrites the real one from agent-framework-core. Reinstall core last.
RUN uv pip install --reinstall --no-deps agent-framework-core==1.2.2


FROM base

COPY --from=builder /app /app
COPY --from=builder /bin/uv /bin/uv

ENV PATH="/app/.venv/bin:$PATH"
# Install dependencies

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]