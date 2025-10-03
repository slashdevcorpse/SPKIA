# Backend Dockerfile - Multi-stage build for optimized production image
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies for Python packages and Taipy
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories for models, trust anchors, and Taipy storage
RUN mkdir -p /app/models /app/trust_anchors /app/sensor_pki_anchors \
    /app/.taipy /app/taipy_storage /app/uploads /app/temp

# Set permissions for runtime directories
RUN chmod -R 755 /app/models /app/trust_anchors /app/sensor_pki_anchors \
    /app/.taipy /app/taipy_storage /app/uploads /app/temp

# Environment variables (defaults, override with .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MONGODB_URI=mongodb://mongo:27017 \
    MONGODB_DB=spkia \
    REDIS_URL=redis://redis:6379/0 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

# Expose ports (8000 for FastAPI, 5000 for Taipy GUI)
EXPOSE 8000 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
