# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install uv. We pin to the same range as pyproject.toml ([tool.uv].required-version).
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first so the layer is cached across source changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source and install the project itself.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 \
    OLLAMA_MODEL=gemma4:31b \
    CORS_ORIGINS=*

EXPOSE 8000

CMD ["uvicorn", "llm_uv_template.api:app", "--host", "0.0.0.0", "--port", "8000"]
