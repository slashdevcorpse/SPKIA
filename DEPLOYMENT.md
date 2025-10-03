# SPKIA Deployment Guide

This guide covers deploying SPKIA to various environments.

## Table of Contents

- [Local Development](#local-development)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Production Deployment](#production-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB disk space

### Quick Start

1. **Clone repository**
   ```bash
   git clone https://github.com/your-org/spkia.git
   cd spkia
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file**
   - Set `SECRET_KEY` to a random string
   - Configure MongoDB URI if needed
   - Adjust resource limits

4. **Start services**
   ```bash
   docker-compose up -d
   ```

5. **Verify deployment**
   ```bash
   curl http://localhost:8000/health
   ```

6. **Access application**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Workflow

**Backend development**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend development**:
```bash
cd frontend
npm install
npm run dev
```

---

## Docker Compose Deployment

### Production-Ready Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  mongo:
    image: mongo:7.0
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: spkia
    volumes:
      - mongo-data:/data/db
    networks:
      - spkia-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    environment:
      - MONGODB_URI=mongodb://admin:${MONGO_PASSWORD}@mongo:27017/spkia?authSource=admin
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models:ro
      - ./trust_anchors:/app/trust_anchors:ro
      - ./sensor_pki_anchors:/app/sensor_pki_anchors:ro
    depends_on:
      - mongo
    networks:
      - spkia-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: always
    networks:
      - spkia-network

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - spkia-network

volumes:
  mongo-data:

networks:
  spkia-network:
```

**Deploy**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Production Deployment

### Server Requirements

**Minimum**:
- 2 vCPUs
- 8 GB RAM
- 50 GB SSD
- Ubuntu 22.04 LTS or similar

**Recommended**:
- 4 vCPUs
- 16 GB RAM
- 100 GB SSD
- Load balancer for multiple instances

### Pre-Deployment Checklist

- [ ] Domain name configured
- [ ] SSL/TLS certificates obtained
- [ ] Firewall configured (ports 80, 443)
- [ ] MongoDB credentials set
- [ ] Secret key generated
- [ ] ML models downloaded
- [ ] Trust anchors configured
- [ ] Backup strategy implemented

### SSL/TLS Certificate Setup

#### Using Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured)
sudo systemctl status certbot.timer
```

#### Manual Certificate

1. Place certificates in `nginx/ssl/`:
   - `fullchain.pem`
   - `privkey.pem`

2. Update `nginx/nginx.conf` to enable HTTPS block

### Environment Variables (Production)

```bash
# .env file
MONGODB_URI=mongodb://admin:STRONG_PASSWORD@mongo:27017/spkia?authSource=admin
SECRET_KEY=GENERATE_RANDOM_256_BIT_KEY
API_WORKERS=4
LOG_LEVEL=INFO
CORS_ENABLED=true
ALLOWED_ORIGINS=https://your-domain.com
MAX_UPLOAD_SIZE_MB=100
```

**Generate secret key**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Deployment Steps

1. **SSH to server**
   ```bash
   ssh user@your-server.com
   ```

2. **Install Docker**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

3. **Clone repository**
   ```bash
   git clone https://github.com/your-org/spkia.git
   cd spkia
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit configuration
   ```

5. **Download ML models**
   ```bash
   # Download models to models/ directory
   # See models/README.md for training instructions
   ```

6. **Start services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

7. **Verify deployment**
   ```bash
   curl https://your-domain.com/health
   ```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.21+)
- kubectl configured
- Helm 3.0+ (optional)

### Deployment Manifests

Create `k8s/deployment.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spkia

---

apiVersion: v1
kind: ConfigMap
metadata:
  name: spkia-config
  namespace: spkia
data:
  LOG_LEVEL: "INFO"
  MAX_UPLOAD_SIZE_MB: "100"

---

apiVersion: v1
kind: Secret
metadata:
  name: spkia-secrets
  namespace: spkia
type: Opaque
stringData:
  MONGODB_URI: "mongodb://admin:password@mongo:27017/spkia"
  SECRET_KEY: "your-secret-key-here"

---

apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: spkia
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/spkia-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: spkia-secrets
              key: MONGODB_URI
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: spkia-secrets
              key: SECRET_KEY
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---

apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: spkia
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: spkia-ingress
  namespace: spkia
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: spkia-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

**Deploy to Kubernetes**:
```bash
kubectl apply -f k8s/deployment.yaml
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: spkia
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Configuration

### Database Configuration

**MongoDB Atlas (Managed)**:
```bash
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/spkia?retryWrites=true&w=majority
```

**Self-hosted MongoDB**:
```bash
# Enable authentication
MONGODB_URI=mongodb://admin:password@localhost:27017/spkia?authSource=admin

# Replica set (recommended for production)
MONGODB_URI=mongodb://admin:password@mongo1:27017,mongo2:27017,mongo3:27017/spkia?replicaSet=rs0
```

### ML Models

Download and place models in `models/`:
```bash
models/
├── cnn_artifact_detector_v1.0.pth
├── prnu_patterns_v1.0.npz
└── metadata_classifier_v1.0.pkl
```

See `models/README.md` for training instructions.

### Trust Anchors

Configure manufacturer certificates:
```bash
trust_anchors/
└── adobe/
    └── adobe_root_ca.pem

sensor_pki_anchors/
├── Sony/
│   └── sony_imx989.pem
└── Canon/
    └── canon_digic_x.pem
```

---

## Monitoring

### Health Checks

```bash
# Backend health
curl https://your-domain.com/health

# Expected response
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "ml_models_loaded": true
}
```

### Metrics

```bash
# Get aggregated metrics
curl https://your-domain.com/api/metrics?days=7
```

### Logging

**View logs**:
```bash
# Docker Compose
docker-compose logs -f backend

# Kubernetes
kubectl logs -f deployment/backend -n spkia
```

### Prometheus + Grafana (Optional)

Add to `docker-compose.yml`:
```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
```

---

## Troubleshooting

### Backend Won't Start

**Check logs**:
```bash
docker-compose logs backend
```

**Common issues**:
- MongoDB connection failed → Check `MONGODB_URI`
- ML models not found → Download models to `models/`
- Port already in use → Change `API_PORT` in `.env`

### Frontend Build Fails

```bash
cd frontend
npm install
npm run build
```

### Database Connection Issues

```bash
# Test MongoDB connection
docker exec -it spkia-mongo mongosh

# Check network
docker network inspect spkia_spkia-network
```

### High Memory Usage

- Reduce `API_WORKERS` in `.env`
- Implement request queuing
- Scale horizontally (multiple instances)

### SSL Certificate Errors

```bash
# Verify certificate
openssl s_client -connect your-domain.com:443

# Renew Let's Encrypt
sudo certbot renew
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup
docker exec spkia-mongo mongodump --out /backup

# Restore
docker exec spkia-mongo mongorestore /backup
```

### Automated Backups

Add to crontab:
```bash
0 2 * * * docker exec spkia-mongo mongodump --out /backup/$(date +\%Y\%m\%d)
```

---

## Security Hardening

1. **Enable firewall**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Disable root SSH**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set: PermitRootLogin no
   sudo systemctl restart sshd
   ```

3. **Keep system updated**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Monitor logs**
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```

---

## Support

- 📧 **Email**: deploy@spkia.org
- 🐛 **Issues**: https://github.com/your-org/spkia/issues
- 📖 **Docs**: https://docs.spkia.org
