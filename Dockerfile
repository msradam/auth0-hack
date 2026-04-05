# Amanat - Full deployment with llama-server for tool calling
FROM python:3.13-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build deps including git (required by llama.cpp cmake)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

# Build llama-server from source
ARG LLAMA_CPP_TAG=b5580
RUN curl -fsSL https://github.com/ggerganov/llama.cpp/archive/refs/tags/${LLAMA_CPP_TAG}.tar.gz \
    | tar xz \
    && cd llama.cpp-${LLAMA_CPP_TAG} \
    && cmake -B build -DGGML_CUDA=OFF -DGGML_METAL=OFF -DLLAMA_CURL=OFF -DBUILD_SHARED_LIBS=OFF \
    && cmake --build build --target llama-server -j$(nproc) \
    && cp build/bin/llama-server /usr/local/bin/llama-server \
    && cd / && rm -rf llama.cpp-${LLAMA_CPP_TAG}

# Runtime image
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Only runtime dep: libgomp for OpenMP (llama-server needs it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy llama-server binary from builder
COPY --from=builder /usr/local/bin/llama-server /usr/local/bin/llama-server

WORKDIR /app

# Install Python deps (no docling/torch for lightweight deploy)
COPY requirements-railway.txt ./
RUN pip install --no-cache-dir -r requirements-railway.txt

COPY . .

# Download model at build time (cached in Docker layer)
ARG MODEL_REPO=lmstudio-community/granite-4.0-tiny-preview-GGUF
ARG MODEL_FILE=granite-4.0-tiny-preview-Q4_K_M.gguf
RUN mkdir -p /models && \
    curl -fSL -o /models/${MODEL_FILE} \
    "https://huggingface.co/${MODEL_REPO}/resolve/main/${MODEL_FILE}"

ENV MODEL_PATH=/models/${MODEL_FILE}

EXPOSE 8000 8080

# Entrypoint: start llama-server then chainlit
COPY scripts/container_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
