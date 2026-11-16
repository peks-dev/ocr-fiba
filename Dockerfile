# Single image for both Cloud Run services; OCR_SERVICE=api|mcp selects the entrypoint.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app

# Dependency layer (cached unless the lockfile / package manifests change).
COPY pyproject.toml uv.lock ./
COPY packages/core-engine/pyproject.toml packages/core-engine/pyproject.toml
COPY packages/api/pyproject.toml packages/api/pyproject.toml
COPY packages/cli/pyproject.toml packages/cli/pyproject.toml
COPY packages/mcp/pyproject.toml packages/mcp/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-workspace

# Application code.
COPY packages/core-engine packages/core-engine
COPY packages/api packages/api
COPY packages/cli packages/cli
COPY packages/mcp packages/mcp
COPY mcp_server.py ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    OCR_ENV=production \
    OCR_SERVICE=api \
    OCR_API_HOST=0.0.0.0 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    PORT=8080

RUN useradd --create-home --uid 10001 app && mkdir -p /app/runs && chown app /app/runs
USER app

EXPOSE 8080
CMD ["sh", "-c", "if [ \"$OCR_SERVICE\" = mcp ]; then exec ocr-mcp; else exec ocr-api; fi"]
