# Amanat - Demo mode deployment (no llama-server needed)
# Tools return synthetic data, Auth0 login works

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install deps into project venv
RUN uv sync --no-install-project --frozen 2>/dev/null || \
    uv sync --no-install-project

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen 2>/dev/null || uv sync

EXPOSE 8000

# Run chainlit directly from the venv
CMD ["python", "-m", "chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
