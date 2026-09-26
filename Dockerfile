# Multi-stage Dockerfile for Unified Cloud Deployment
# Stage 1: Build React Production Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend + Embedded Dashboard
FROM python:3.11-slim
WORKDIR /app

# Install minimal system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application layers
COPY backend/ /app/backend/
COPY simulator/ /app/simulator/
COPY ros2_ws/src/gps_denied_localization/ /app/ros2_ws/src/gps_denied_localization/

# Copy compiled frontend from stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:/app/backend:/app/simulator:/app/ros2_ws/src/gps_denied_localization"
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "run.py"]
