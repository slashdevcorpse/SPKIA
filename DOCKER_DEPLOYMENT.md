# SPKIA - Docker Deployment Guide

This guide covers deploying SPKIA using Docker and Docker Compose. All dependencies are installed automatically within containers.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- No local Python or Node.js installation required
- At least 8GB RAM and 20GB disk space

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration (optional for local dev)
# Default values work for local development
```

### 2. Build and Start Services

```bash
# Build all Docker images (this installs all dependencies)
docker-compose build

# Start all services in detached mode
docker-compose up -d
```

This will start:
- **MongoDB** (port 27017) - Database for verification jobs
- **Redis** (port 6379) - Caching layer
- **Backend** (port 8000) - FastAPI + Taipy
- **Frontend** (port 3000) - React + Nginx
- **Nginx** (port 80) - Reverse proxy

### 3. Verify Deployment

```bash
# Check all containers are running
docker-compose ps

# Check container logs
docker-compose logs -f

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost/health
```

### 4. Access Services

- **Main Application**: http://localhost
- **API Documentation**: http://localhost:8000/docs
- **Taipy UI**: http://localhost:5000 (start via API: `POST /api/taipy/start`)
- **Health Check**: http://localhost:8000/health

## Service Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
┌──────▼──────────────────────────┐
│  Nginx Reverse Proxy (port 80)  │
└──────┬──────────────────────────┘
       │
       ├──────► Frontend (React + CopilotKit)
       │
       └──────► Backend (FastAPI + Taipy)
                  │
                  ├──► MongoDB (verification data)
                  ├──► Redis (caching)
                  └──► ML Models (CNN, PRNU, etc.)
```

## Docker Commands

### Development

```bash
# Start with live logs
docker-compose up

# Rebuild after code changes
docker-compose up --build

# Restart specific service
docker-compose restart backend

# View logs for specific service
docker-compose logs -f backend
```

### Maintenance

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes data!)
docker-compose down -v

# Remove all containers, networks, and images
docker-compose down --rmi all

# Execute command in running container
docker-compose exec backend python -c "import taipy; print(taipy.__version__)"
docker-compose exec frontend npm list --depth=0
```

### Debugging

```bash
# Shell into backend container
docker-compose exec backend bash

# Shell into frontend container
docker-compose exec frontend sh

# Check MongoDB connection
docker-compose exec mongo mongosh --eval "db.adminCommand('ping')"

# Check Redis connection
docker-compose exec redis redis-cli ping
```

## Dependency Management

All dependencies are installed during Docker build:

### Backend Dependencies (backend/requirements.txt)
- Installed automatically via `pip install -r requirements.txt` in Dockerfile
- Includes: FastAPI, Taipy, PyTorch, scikit-learn, cryptography, testing tools

### Frontend Dependencies (frontend/package.json)
- Installed automatically via `npm ci --legacy-peer-deps` in Dockerfile
- Includes: React, CopilotKit, Vite, Tailwind CSS, TypeScript

**No local installation required** - Docker handles everything!

## Environment Variables

Key variables in `.env`:

```bash
# MongoDB
MONGODB_URI=mongodb://mongo:27017
MONGODB_DB=spkia

# Redis
REDIS_URL=redis://redis:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# CORS (for production, restrict this)
ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:80

# Data Retention
JOB_TTL_HOURS=24

# ML Models
ML_MODELS_DIR=/app/models

# Logging
LOG_LEVEL=INFO
```

## Production Deployment

For production:

1. **Update .env**:
   ```bash
   # Use specific allowed origins
   ALLOWED_ORIGINS=https://yourdomain.com
   
   # Use secure secrets
   SECRET_KEY=<generate-secure-random-key>
   
   # Adjust resources
   API_WORKERS=4
   ```

2. **Use production-ready MongoDB/Redis**:
   - Replace docker-compose MongoDB with managed MongoDB Atlas
   - Replace docker-compose Redis with managed Redis service
   - Update connection strings in `.env`

3. **Add SSL/TLS**:
   - Configure nginx with SSL certificates
   - Update nginx.conf with SSL configuration
   - Use Let's Encrypt for free certificates

4. **Scale services**:
   ```bash
   docker-compose up -d --scale backend=3
   ```

5. **Monitor**:
   - Add health check monitoring
   - Set up log aggregation
   - Configure alerts

## Taipy Integration

The Taipy UI for scenario management is available via API:

```bash
# Start Taipy GUI
curl -X POST http://localhost:8000/api/taipy/start

# Check Taipy status
curl http://localhost:8000/api/taipy/status

# Access Taipy UI
open http://localhost:5000
```

Taipy provides:
- Threshold configuration UI
- Scenario management for what-if analysis
- Verification history visualization
- Comparison of AI detection thresholds

## Troubleshooting

### Container fails to start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Port already in use: Stop conflicting service or change port in docker-compose.yml
# - Out of memory: Increase Docker memory limit
# - Build failure: Check Dockerfile syntax and dependency versions
```

### MongoDB connection issues

```bash
# Verify MongoDB is running
docker-compose ps mongo

# Test connection
docker-compose exec backend python -c "from motor.motor_asyncio import AsyncIOMotorClient; print('OK')"
```

### Frontend not loading

```bash
# Check nginx logs
docker-compose logs nginx

# Verify frontend built correctly
docker-compose exec frontend ls -la /usr/share/nginx/html

# Rebuild frontend
docker-compose up --build frontend
```

### Performance issues

```bash
# Check resource usage
docker stats

# Increase Docker resources in Docker Desktop settings
# Recommended: 4 CPU cores, 8GB RAM
```

## File Structure

```
SPKIA/
├── docker-compose.yml          # Multi-container orchestration
├── .env                        # Environment variables (create from .env.example)
├── .env.example               # Environment template
├── backend/
│   ├── Dockerfile             # Backend container definition
│   ├── requirements.txt       # Python dependencies (auto-installed)
│   └── app/                   # FastAPI application code
├── frontend/
│   ├── Dockerfile             # Frontend container definition
│   ├── package.json           # Node dependencies (auto-installed)
│   └── src/                   # React application code
└── nginx/
    └── nginx.conf             # Nginx reverse proxy configuration
```

## Next Steps

1. Review and customize `.env` for your environment
2. Run `docker-compose build && docker-compose up -d`
3. Access the application at http://localhost
4. Upload test media for verification
5. Configure AI detection thresholds via Taipy UI
6. Review API documentation at http://localhost:8000/docs

## Support

- Check logs: `docker-compose logs -f`
- Review API docs: http://localhost:8000/docs
- Taipy documentation: https://docs.taipy.io/
- CopilotKit documentation: https://docs.copilotkit.ai/
