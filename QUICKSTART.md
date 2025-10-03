# Quick Start Guide

Get SPKIA running in 5 minutes!

## Prerequisites

- Docker Desktop installed
- 8GB RAM available
- Internet connection

## Steps

### 1. Clone & Setup

```bash
git clone https://github.com/your-org/spkia.git
cd spkia
cp .env.example .env
```

### 2. Generate Secret Key

**Linux/Mac**:
```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
```

**Windows (PowerShell)**:
```powershell
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" | Out-File -Append .env
```

### 3. Start Services

```bash
docker-compose up -d
```

Wait 30 seconds for services to initialize.

### 4. Verify

```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "ml_models_loaded": true
}
```

### 5. Open Application

Visit: **http://localhost:3000**

## Test Verification

1. Drag and drop an image file
2. Wait for verification to complete
3. View results showing authenticity status

## Troubleshooting

**Services not starting?**
```bash
docker-compose logs
```

**Port already in use?**

Edit `.env` and change:
```
API_PORT=8001  # Change from 8000
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

**Out of memory?**

Reduce workers in `.env`:
```
API_WORKERS=2  # Change from 4
```

## Next Steps

- Read `README.md` for full documentation
- Configure ML models (see `models/README.md`)
- Set up trust anchors for C2PA/Sensor-PKI
- Deploy to production (see `DEPLOYMENT.md`)

## Stop Services

```bash
docker-compose down
```

To remove all data:
```bash
docker-compose down -v
```

---

**Need help?** Open an issue on GitHub or email support@spkia.org
