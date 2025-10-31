# Base Python image
FROM python:3.11-slim-bullseye AS base
WORKDIR /app

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
#RUN uv sync --frozen --no-install-project --no-dev

# Backend app setup
COPY . /app  
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
#RUN uv sync --frozen --no-dev


FROM base

COPY --from=builder /app /app
COPY --from=builder /bin/uv /bin/uv

ENV PATH="/app/.venv/bin:$PATH"
# Install dependencies

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app_kernel:app", "--host", "0.0.0.0", "--port", "8000"]