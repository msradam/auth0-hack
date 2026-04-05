#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/models/granite-4.0-micro-Q4_K_S.gguf}"
LLAMA_PORT="${LLAMA_PORT:-8080}"
CHAINLIT_PORT="${CHAINLIT_PORT:-8000}"

echo "=== Amanat - Offline Humanitarian Data Governance ==="
echo "Starting llama-server on port ${LLAMA_PORT}..."

# Start llama-server in the background
# --ctx-size 4096: context window
# --n-gpu-layers 0: CPU only (no GPU in container by default)
llama-server \
    --model "${MODEL_PATH}" \
    --port "${LLAMA_PORT}" \
    --host 0.0.0.0 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    2>&1 &

LLAMA_PID=$!

# Wait for llama-server to be ready
echo "Waiting for llama-server to be ready..."
for i in $(seq 1 120); do
    if curl -sf http://localhost:${LLAMA_PORT}/health > /dev/null 2>&1; then
        echo "llama-server is ready."
        break
    fi
    if ! kill -0 $LLAMA_PID 2>/dev/null; then
        echo "ERROR: llama-server exited unexpectedly."
        exit 1
    fi
    sleep 1
done

# Point the OpenAI-compatible client at llama-server
export OPENAI_API_KEY="not-needed"
export OPENAI_BASE_URL="http://localhost:${LLAMA_PORT}/v1"

echo "Starting Chainlit on port ${CHAINLIT_PORT}..."

# Run Chainlit in the foreground
exec uv run chainlit run app.py \
    --host 0.0.0.0 \
    --port "${CHAINLIT_PORT}"
