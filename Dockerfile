# Amanat - Demo mode deployment (no llama-server, no docling/torch)
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install only lightweight deps (no docling/torch)
COPY requirements-railway.txt ./
RUN pip install --no-cache-dir -r requirements-railway.txt

COPY . .

EXPOSE 8000
