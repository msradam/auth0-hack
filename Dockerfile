# Amanat - Demo mode deployment
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install only production deps, no dev
RUN uv sync --no-install-project --no-dev --frozen 2>/dev/null || \
    uv sync --no-install-project --no-dev

COPY . .
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

EXPOSE 8000

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
