# 🚀 AI Service Deployment Guide

## Overview

Comprehensive deployment guide for AI Service in development, staging, and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Production Configuration](#production-configuration)
7. [Monitoring & Observability](#monitoring--observability)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 4+ cores (production: 8+ cores)
- **Memory**: 8GB+ (production: 16GB+)
- **Storage**: 50GB+ SSD
- **Network**: 1Gbps+ connectivity

### Software Requirements

- **Python**: 3.12+
- **Docker**: 20.10+
- **Kubernetes**: 1.25+ (for K8s deployment)
- **Elasticsearch**: 8.11.0+
- **Poetry**: 1.6+

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/ai-service.git
cd ai-service
```

### 2. Install Dependencies

```bash
# Using Poetry (recommended)
make install-dev

# Or manually
poetry install --with dev
```

### 3. Environment Configuration

```bash
# Copy environment template
cp env.production.example env.production

# Edit configuration
nano env.production
```

### 4. Verify Installation

```bash
# Run tests
make test

# Check service health
make start
curl http://localhost:8000/health
```

## Local Development

### Development Server

```bash
# Start development server
make start

# Or with uvicorn directly
poetry run uvicorn src.ai_service.main:app --reload --host 0.0.0.0 --port 8000
```

### Development with Docker

```bash
# Build development image
make docker-build

# Run development container
make docker-dev

# Or with docker-compose
docker-compose --profile dev up ai-service-dev
```

### Database Setup

```bash
# Start Elasticsearch for development
docker-compose up -d elasticsearch

# Initialize search indices
python scripts/setup_elasticsearch.py
```

## Docker Deployment

### Build Production Image

```bash
# Build production image
make docker-build

# Or with custom tag
docker build -f Dockerfile.prod -t ai-service:latest .
```

### Run Production Container

```bash
# Basic production run
docker run -d \
  --name ai-service \
  -p 8000:8000 \
  --env-file env.production \
  ai-service:latest

# With resource limits
docker run -d \
  --name ai-service \
  -p 8000:8000 \
  --memory=4g \
  --cpus=2 \
  --env-file env.production \
  ai-service:latest
```

### Docker Compose Production

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# With monitoring stack
docker-compose -f docker-compose.prod.yml -f monitoring/docker-compose.monitoring.yml up -d
```

## Kubernetes Deployment

### Namespace Setup

```bash
# Create namespace
kubectl create namespace ai-service

# Set context
kubectl config set-context --current --namespace=ai-service
```

### Configuration

```bash
# Apply ConfigMaps
kubectl apply -f k8s/configmap.yaml

# Apply Secrets
kubectl apply -f k8s/secrets.yaml
```

### Service Deployment

```bash
# Deploy application
kubectl apply -f k8s/ai-service.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Deploy monitoring
kubectl apply -f k8s/monitoring.yaml
```

### Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=ai-service

# Check service
kubectl get svc ai-service

# Check logs
kubectl logs -f deployment/ai-service
```

## Production Configuration

### Environment Variables

```bash
# Core Configuration
APP_ENV=production
WORKERS=4
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security
ADMIN_API_KEY=your-secure-api-key-here
CORS_ORIGINS=https://your-domain.com

# Elasticsearch
ELASTICSEARCH_URL=https://your-elasticsearch-cluster.com:9200
ELASTICSEARCH_USERNAME=ai-service
ELASTICSEARCH_PASSWORD=secure-password
ELASTICSEARCH_SSL_VERIFY=true

# Performance
CACHE_TTL=3600
MAX_BATCH_SIZE=100
REQUEST_TIMEOUT=30

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

### Feature Flags

```python
# config/settings.py
FEATURE_FLAGS = {
    "use_factory_normalizer": True,
    "enable_search_optimizations": True,
    "enhanced_accuracy_mode": False,
    "enable_embeddings": True,
    "enable_variants": True
}
```

### Resource Limits

```yaml
# Kubernetes resources
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## Monitoring & Observability

### Prometheus Metrics

```bash
# Access metrics
curl http://localhost:9090/metrics

# Key metrics to monitor
ai_service_requests_total
ai_service_processing_duration_seconds
ai_service_cache_hit_rate
ai_service_errors_total
```

### Grafana Dashboard

```bash
# Access dashboard
http://localhost:3000
# Username: admin
# Password: admin

# Import dashboard from monitoring/grafana-dashboard.json
```

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# Readiness probe
curl http://localhost:8000/health/ready
```

### Logging

```bash
# View logs
docker logs -f ai-service

# Kubernetes logs
kubectl logs -f deployment/ai-service

# Structured logging format
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Request processed",
  "request_id": "req_123",
  "processing_time_ms": 45,
  "language": "ru"
}
```

## Security

### API Security

```python
# Admin endpoints protection
@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/admin/"):
        api_key = request.headers.get("Authorization")
        if not validate_api_key(api_key):
            raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = await call_next(request)
    return response
```

### Network Security

```yaml
# Network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-service-netpol
spec:
  podSelector:
    matchLabels:
      app: ai-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
```

### Secrets Management

```bash
# Kubernetes secrets
kubectl create secret generic ai-service-secrets \
  --from-literal=api-key=your-secure-key \
  --from-literal=es-password=secure-password \
  --namespace=ai-service

# AWS Secrets Manager (alternative)
aws secretsmanager create-secret \
  --name ai-service/production \
  --secret-string file://secrets.json
```

## Performance Optimization

### Caching Strategy

```python
# Multi-level caching
L1_CACHE_SIZE = 1000  # Hot data
L2_CACHE_SIZE = 10000  # Warm data
CACHE_TTL = 3600      # 1 hour
```

### Connection Pooling

```python
# Elasticsearch configuration
ELASTICSEARCH_CONFIG = {
    "maxsize": 50,
    "timeout": 30,
    "max_retries": 3,
    "retry_on_timeout": True
}
```

### Autoscaling

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-service
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

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker logs ai-service

# Common causes:
# - Port already in use
# - Invalid environment variables
# - Missing dependencies
```

#### 2. High Memory Usage

```bash
# Check memory usage
docker stats ai-service

# Solutions:
# - Reduce cache sizes
# - Enable memory pressure cleanup
# - Add memory limits
```

#### 3. Slow Performance

```bash
# Check metrics
curl http://localhost:9090/metrics | grep ai_service_processing_duration

# Optimization steps:
# - Enable caching
# - Optimize batch sizes
# - Check Elasticsearch performance
```

#### 4. Elasticsearch Connection Issues

```bash
# Test connectivity
curl -u username:password https://elasticsearch:9200/_cluster/health

# Common fixes:
# - Check network connectivity
# - Verify credentials
# - Check SSL certificates
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Or temporarily
curl -X POST http://localhost:8000/admin/set-log-level \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'
```

### Performance Profiling

```bash
# Enable profiling
curl -X POST http://localhost:8000/admin/enable-profiling \
  -H "Authorization: Bearer $API_KEY"

# View profile report
curl http://localhost:8000/admin/profile-report
```

## Maintenance

### Regular Tasks

```bash
# Daily: Check health
curl http://localhost:8000/health

# Weekly: Clear cache if needed
curl -X POST http://localhost:8000/admin/clear-cache \
  -H "Authorization: Bearer $API_KEY"

# Monthly: Update dependencies
poetry update
make test
make docker-build
```

### Backup Procedures

```bash
# Backup Elasticsearch data
curl -X PUT "elasticsearch:9200/_snapshot/backup/snapshot_1" \
  -H "Content-Type: application/json" \
  -d '{"indices": "ai_service_*"}'

# Backup configuration
kubectl get configmap ai-service-config -o yaml > config-backup.yaml
```

### Rolling Updates

```bash
# Kubernetes rolling update
kubectl set image deployment/ai-service \
  ai-service=ai-service:v2.0.0 \
  --namespace=ai-service

# Monitor rollout
kubectl rollout status deployment/ai-service --namespace=ai-service
```

## Emergency Procedures

### Service Recovery

```bash
# Quick restart
kubectl rollout restart deployment/ai-service

# Emergency fallback mode
curl -X POST http://localhost:8000/admin/enable-fallback \
  -H "Authorization: Bearer $API_KEY"
```

### Incident Response

1. **Detection**: Monitor alerts and metrics
2. **Assessment**: Check health endpoints and logs
3. **Containment**: Scale up or enable fallback mode
4. **Resolution**: Apply fix and verify
5. **Recovery**: Restore normal operation

### Contact Information

- **Development Team**: dev-team@company.com
- **Operations Team**: ops-team@company.com
- **On-call Engineer**: +1-555-0123

## Additional Resources

- [API Documentation](./API.md)
- [Architecture Overview](./ARCHITECTURE_OVERVIEW.md)
- [Monitoring Guide](./MONITORING.md)
- [Security Guide](./SECURITY.md)