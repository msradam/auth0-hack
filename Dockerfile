# Amanat - Offline humanitarian data governance agent
# Runs entirely offline after build. No data leaves the container.
#
# Build:  podman build -t amanat -f Containerfile .
# Run:    podman run --rm -p 8000:8000 -e AUTH0_DOMAIN=... -e AUTH0_CLIENT_ID=... amanat
#
# For fully offline demo (no Auth0), set AMANAT_OFFLINE=1:
#   podman run --rm -p 8000:8000 -e AMANAT_OFFLINE=1 amanat

FROM python:3.13-slim AS base

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# ---------- Install uv ----------
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# ---------- Build llama.cpp from source ----------
# Pre-built binaries are x86-only and often lag behind; building from
# source works on both amd64 and arm64 and takes ~2 min on a modern host.
ARG LLAMA_CPP_TAG=b5580
RUN curl -fsSL https://github.com/ggerganov/llama.cpp/archive/refs/tags/${LLAMA_CPP_TAG}.tar.gz \
    | tar xz \
    && cd llama.cpp-${LLAMA_CPP_TAG} \
    && cmake -B build -DGGML_CUDA=OFF -DGGML_METAL=OFF -DLLAMA_CURL=OFF \
    && cmake --build build --target llama-server -j$(nproc) \
    && cp build/bin/llama-server /usr/local/bin/llama-server \
    && cd / && rm -rf llama.cpp-${LLAMA_CPP_TAG}

# ---------- Download Granite 4 Micro GGUF ----------
# Q4_K_M is a good balance of quality vs size (~2.5 GB)
ARG MODEL_REPO=lmstudio-community/granite-4.0-tiny-preview-GGUF
ARG MODEL_FILE=granite-4.0-tiny-preview-Q4_K_M.gguf
RUN mkdir -p /models && \
    curl -fSL -o /models/${MODEL_FILE} \
    "https://huggingface.co/${MODEL_REPO}/resolve/main/${MODEL_FILE}"

ENV MODEL_PATH=/models/${MODEL_FILE}

# ---------- Install Python project ----------
WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install deps (skip mlx/mlx-lm/mlx-vlm which are macOS-only)
RUN uv sync --no-install-project --frozen 2>/dev/null || \
    uv sync --no-install-project

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen 2>/dev/null || uv sync

# ---------- Entrypoint ----------
COPY scripts/container_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
