# SignalOS Backend Deployment Guide

## Production Deployment Overview

**Status:** ✅ PRODUCTION READY  
**Deployment Method:** Docker + Kubernetes  
**Environment:** Production, Staging, Development  
**Scalability:** Horizontal scaling ready  

---

## Prerequisites

### System Requirements
```
OS: Linux (Ubuntu 20.04+ recommended)
CPU: 4 cores minimum (8 cores recommended)
RAM: 8GB minimum (16GB recommended)
Storage: 50GB minimum (SSD recommended)
Network: Stable internet connection
```

### Software Dependencies
```
Docker: 24.0+
Docker Compose: 2.20+
Kubernetes: 1.28+ (optional)
Python: 3.11+
PostgreSQL: 15+ (for production)
Redis: 7.0+ (for caching)
```

---

## Environment Configuration

### 1. Environment Variables
Create `.env` file in the backend directory:

```bash
# Application Settings
APP_NAME=SignalOS
APP_VERSION=1.0.0
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/signalos_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password

# JWT Configuration
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Security Settings
CORS_ORIGINS=https://app.signalos.com,https://dashboard.signalos.com
CORS_ALLOW_CREDENTIALS=true
ALLOWED_HOSTS=api.signalos.com,localhost

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=200

# MT5 Configuration
MT5_SOCKET_HOST=localhost
MT5_SOCKET_PORT=9999
MT5_FILE_INPUT_PATH=/opt/mt5/input
MT5_FILE_OUTPUT_PATH=/opt/mt5/output

# External APIs
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Storage
UPLOAD_PATH=/app/uploads
MAX_FILE_SIZE=50MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf,txt,csv

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
```

### 2. Database Setup

#### PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE signalos_prod;
CREATE USER signalos_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE signalos_prod TO signalos_user;
\q
```

#### Database Migration
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Create initial admin user
python scripts/create_admin_user.py
```

### 3. Redis Setup
```bash
# Ubuntu/Debian
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set password: requirepass your_redis_password

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

---

## Docker Deployment

### 1. Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/status/health || exit 1

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/signalos
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - signalos-network

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=signalos
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - signalos-network

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass password
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - signalos-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - signalos-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - signalos-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - signalos-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  signalos-network:
    driver: bridge
```

### 3. Deploy with Docker Compose
```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app

# Scale the application
docker-compose up -d --scale app=3

# Stop services
docker-compose down
```

---

## Kubernetes Deployment

### 1. Kubernetes Manifests

#### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: signalos
```

#### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: signalos-config
  namespace: signalos
data:
  APP_NAME: "SignalOS"
  APP_ENV: "production"
  LOG_LEVEL: "INFO"
  PROMETHEUS_ENABLED: "true"
```

#### Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: signalos-secrets
  namespace: signalos
type: Opaque
data:
  JWT_SECRET_KEY: <base64-encoded-secret>
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
```

#### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: signalos-backend
  namespace: signalos
spec:
  replicas: 3
  selector:
    matchLabels:
      app: signalos-backend
  template:
    metadata:
      labels:
        app: signalos-backend
    spec:
      containers:
      - name: signalos-backend
        image: signalos/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: signalos-config
              key: APP_NAME
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: signalos-secrets
              key: JWT_SECRET_KEY
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/status/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/status/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

#### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: signalos-backend-service
  namespace: signalos
spec:
  selector:
    app: signalos-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: signalos-ingress
  namespace: signalos
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.signalos.com
    secretName: signalos-tls
  rules:
  - host: api.signalos.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: signalos-backend-service
            port:
              number: 80
```

### 2. Deploy to Kubernetes
```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n signalos

# View logs
kubectl logs -f deployment/signalos-backend -n signalos

# Scale deployment
kubectl scale deployment signalos-backend --replicas=5 -n signalos

# Check service
kubectl get svc -n signalos
```

---

## Nginx Configuration

### 1. Nginx Config
```nginx
events {
    worker_connections 1024;
}

http {
    upstream signalos_backend {
        server app:8000;
    }

    server {
        listen 80;
        server_name api.signalos.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.signalos.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # Rate limiting
        limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
        limit_req zone=api burst=20 nodelay;

        location / {
            proxy_pass http://signalos_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

---

## Monitoring & Logging

### 1. Prometheus Configuration
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'signalos-backend'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/api/v1/status/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### 2. Grafana Dashboard
Import the SignalOS dashboard from `monitoring/grafana-dashboard.json`

### 3. Log Aggregation
```bash
# ELK Stack deployment
docker-compose -f docker-compose.elk.yml up -d

# Fluentd configuration for log shipping
# See monitoring/fluentd.conf
```

---

## SSL/TLS Configuration

### 1. Let's Encrypt Setup
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate SSL certificate
sudo certbot --nginx -d api.signalos.com

# Auto-renewal
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Manual SSL Certificate
```bash
# Generate private key
openssl genrsa -out privkey.pem 2048

# Generate certificate signing request
openssl req -new -key privkey.pem -out cert.csr

# Generate self-signed certificate (for testing)
openssl x509 -req -days 365 -in cert.csr -signkey privkey.pem -out fullchain.pem
```

---

## Backup & Recovery

### 1. Database Backup
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="signalos_prod"

# Create backup
pg_dump -h localhost -U signalos_user -d $DB_NAME > $BACKUP_DIR/backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/backup_$DATE.sql

# Remove old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

### 2. Application Backup
```bash
#!/bin/bash
# app_backup.sh

BACKUP_DIR="/app_backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /app/uploads

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /app/config

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /app/logs
```

### 3. Recovery Procedure
```bash
# Database recovery
gunzip backup_20250118_120000.sql.gz
psql -h localhost -U signalos_user -d signalos_prod < backup_20250118_120000.sql

# Application recovery
tar -xzf uploads_20250118_120000.tar.gz -C /
tar -xzf config_20250118_120000.tar.gz -C /
```

---

## Performance Tuning

### 1. Database Optimization
```sql
-- PostgreSQL optimization
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET random_page_cost = 1.1;
SELECT pg_reload_conf();
```

### 2. Application Optimization
```python
# Uvicorn production settings
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload
```

### 3. Redis Configuration
```
# redis.conf optimization
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

---

## Security Hardening

### 1. System Security
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install fail2ban
sudo apt install fail2ban

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### 2. Application Security
```bash
# Run security scan
safety check

# Update dependencies
pip-audit

# Check for vulnerabilities
bandit -r backend/
```

---

## Troubleshooting

### 1. Common Issues

#### Database Connection Issues
```bash
# Check database status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U signalos_user -d signalos_prod

# Check logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

#### Application Errors
```bash
# Check application logs
docker-compose logs -f app

# Check system resources
htop
df -h
free -h

# Check network connectivity
curl -I http://localhost:8000/api/v1/status/health
```

#### Performance Issues
```bash
# Monitor database queries
SELECT * FROM pg_stat_activity WHERE state = 'active';

# Check Redis performance
redis-cli info stats

# Monitor application metrics
curl http://localhost:8000/api/v1/status/metrics
```

### 2. Debug Mode
```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart application
docker-compose restart app
```

---

## Production Checklist ✅

### Pre-deployment
- [x] Environment variables configured
- [x] Database setup and migrated
- [x] SSL certificates installed
- [x] Backup procedures tested
- [x] Monitoring configured
- [x] Security hardening applied
- [x] Performance tuning completed

### Post-deployment
- [x] Health checks passing
- [x] Monitoring dashboards working
- [x] Log aggregation functioning
- [x] Backup cron jobs running
- [x] SSL certificates valid
- [x] Performance metrics within limits
- [x] Security scans clean

### Ongoing Maintenance
- [x] Regular security updates
- [x] Database maintenance
- [x] Log rotation
- [x] Backup verification
- [x] Performance monitoring
- [x] Security audits
- [x] Documentation updates

---

## Support & Maintenance

### 1. Support Contacts
```
Technical Support: support@signalos.com
Security Issues: security@signalos.com
Infrastructure: devops@signalos.com
```

### 2. Maintenance Schedule
```
Daily: Health checks, log review
Weekly: Security updates, backup verification
Monthly: Performance analysis, security audit
Quarterly: Full system review, disaster recovery test
```

### 3. Emergency Procedures
```
1. Identify issue severity
2. Check monitoring dashboards
3. Review recent logs
4. Implement emergency fixes
5. Escalate if needed
6. Document incident
```

---

## Conclusion

The SignalOS backend is **production-ready** with:
- ✅ **Complete deployment automation**
- ✅ **Comprehensive monitoring and logging**
- ✅ **Robust security measures**
- ✅ **Scalable architecture**
- ✅ **Disaster recovery procedures**
- ✅ **Performance optimization**

The deployment is designed for **high availability**, **security**, and **scalability** to handle production workloads effectively.

---

*Deployment Guide Version: 1.0.0*
*Last Updated: January 18, 2025*
*Environment: Production Ready*