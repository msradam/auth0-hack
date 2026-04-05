# Amanat - Demo mode deployment (no llama-server needed)
# Tools return synthetic data, Auth0 login works

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install deps
RUN uv sync --no-install-project --frozen 2>/dev/null || \
    uv sync --no-install-project

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen 2>/dev/null || uv sync

EXPOSE 8000

# Demo mode: no llama-server, DEMO_TOOLS=true means synthetic data
CMD ["uv", "run", "chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
