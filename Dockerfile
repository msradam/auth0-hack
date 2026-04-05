# Amanat - Demo mode deployment (no llama-server needed)
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN uv sync --no-install-project --no-dev --frozen 2>/dev/null || \
    uv sync --no-install-project --no-dev

COPY . .
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

EXPOSE 8000
