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
git clone [rep]
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

# Initialize search indices with component templates, index templates, and warmup
python scripts/elasticsearch_setup_and_warmup.py

# Alternative: Use the setup script
./scripts/setup_elasticsearch.sh
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

## Production Deployment Workflow

### Automated Production Deployment

The project includes a comprehensive production deployment script that handles the complete workflow:

```bash
# Run the complete production deployment
./scripts/deploy_search_production.sh
```

This script performs a 12-step automated deployment process:

1. **Backup Configuration**: Creates timestamped backup of current configuration
2. **Update Configuration**: Applies latest configuration changes
3. **Elasticsearch Setup**: Runs component template and index template initialization
4. **Index Creation**: Creates watchlist indices with proper mappings
5. **Alias Management**: Sets up current aliases for seamless access
6. **Data Loading**: Loads sanctioned entities data using bulk loader
7. **Service Restart**: Restarts AI service with new configuration
8. **Health Check**: Verifies service health and connectivity
9. **Search Integration Test**: Runs comprehensive search tests
10. **Performance Validation**: Validates search performance metrics
11. **Cache Warmup**: Warms up normalization and search caches
12. **Final Verification**: Runs end-to-end system validation

### Manual Production Deployment

If you need to perform manual deployment or troubleshoot issues:

```bash
# 1. Setup Elasticsearch infrastructure
python scripts/elasticsearch_setup_and_warmup.py

# 2. Load sanctioned entities data
python scripts/bulk_loader.py --input data/entities/persons.jsonl --entity-type person --upsert
python scripts/bulk_loader.py --input data/entities/orgs.jsonl --entity-type org --upsert

# 3. Test search functionality
python scripts/quick_test_search.py --test all

# 4. Warmup the service
./scripts/smoke_warmup.sh
# Or
poetry run python tools/warmup.py --n 200 --verbose
```

### Production Configuration

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
NORM_CACHE_LRU=8192
MORPH_CACHE_LRU=8192
DISABLE_DEBUG_TRACING=true

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

## Elasticsearch Data Management

### Bulk Data Loading

The system provides a sophisticated bulk loader for sanctioned entities:

```bash
# Load person entities
python scripts/bulk_loader.py --input data/entities/persons.jsonl --entity-type person --upsert --batch-size 1000

# Load organization entities
python scripts/bulk_loader.py --input data/entities/orgs.yaml --entity-type org --upsert --rebuild-alias

# With custom Elasticsearch configuration
python scripts/bulk_loader.py --input entities.jsonl --entity-type person \
  --es-url https://production-es.com:9200 \
  --es-user ai-service \
  --es-pass secure-password \
  --embedding-model sentence-transformers/all-MiniLM-L6-v2
```

### Bulk Loader Features

- **Embedding Generation**: Automatically generates 384-dimensional embeddings for entities without vectors
- **Caching**: In-memory caching for embedding generation to improve performance
- **Batch Processing**: Configurable batch sizes for optimal throughput
- **Metrics Tracking**: Comprehensive metrics including throughput, success rate, and latency
- **Alias Management**: Automatic alias rebuilding for seamless index transitions
- **Retry Logic**: Exponential backoff retry for failed operations

### Elasticsearch Infrastructure Setup

```bash
# Complete Elasticsearch setup
python scripts/elasticsearch_setup_and_warmup.py

# Manual setup steps
# 1. Component templates
curl -X PUT "localhost:9200/_component_template/watchlist_component_template" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/elasticsearch_component_template.json

# 2. Index templates  
curl -X PUT "localhost:9200/_index_template/watchlist_persons_template" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/elasticsearch_persons_template.json

# 3. Create indices
curl -X PUT "localhost:9200/watchlist_persons_v1" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/elasticsearch_persons_template.json

# 4. Setup aliases
curl -X POST "localhost:9200/_aliases" \
  -H "Content-Type: application/json" \
  -d '{"actions": [{"add": {"index": "watchlist_persons_v1", "alias": "watchlist_persons_current"}}]}'

# 5. Warmup queries
python scripts/elasticsearch_setup_and_warmup.py --warmup-only
```

### Search System Testing

```bash
# Comprehensive search testing
python scripts/quick_test_search.py --test all

# Individual component tests
python scripts/quick_test_search.py --test health      # Elasticsearch cluster health
python scripts/quick_testsearch.py --test indices     # Verify required indices exist
python scripts/quick_test_search.py --test ac          # Test AC (Approximate Matching) search
python scripts/quick_test_search.py --test vector      # Test vector/kNN search
python scripts/quick_test_search.py --test multi       # Test multi-search functionality
python scripts/quick_test_search.py --test performance # Performance benchmarking

# Performance metrics output
# ✅ AC Search Latency: 45.23ms
# ✅ Vector Search Latency: 67.89ms
# ✅ Multi-Search Test: 2 responses received
```

## Sanctions Data Pipeline

### INN Cache Generation

The system maintains a cache of Russian Tax Identification Numbers (INN) for improved matching:

```bash
# Generate INN cache from sanctions data
python scripts/generate_inn_cache.py

# Simple INN cache generation
python scripts/generate_inn_cache_simple.py

# Test INN cache coverage
python scripts/test_inn_cache_coverage.py

# Extract sanctioned INNs from data
python scripts/extract_sanctioned_inns.py --input data/sanctions.json --output inn_cache.txt
```

### Sanctions Pipeline

```bash
# Run complete sanctions data pipeline
python scripts/sanctions_pipeline.py

# Pipeline steps:
# 1. Load sanctions data from multiple sources
# 2. Normalize and deduplicate entities
# 3. Generate embeddings for all entities
# 4. Load into Elasticsearch indices
# 5. Create aliases and setup warmup
# 6. Validate data integrity

# Prepare sanctions data
python scripts/prepare_sanctions_data.py --source data/raw/ --output data/processed/

# Export high-recall AC patterns
python scripts/export_high_recall_ac_patterns.py --output patterns/ac_patterns.json
```

### Data Validation

```bash
# Local validation of sanctions data
./scripts/local_validation.sh

# Simple validation
./scripts/simple_validation.sh

# Smoke test sanctions search
./scripts/smoke_test_search.sh

# Test bulk loader functionality
python scripts/test_bulk_loader.py --sample-data

# Test Elasticsearch setup
python scripts/test_elasticsearch_setup.py
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

# Elasticsearch health check
python scripts/quick_test_search.py --test health

# Comprehensive system health
python scripts/quick_test_search.py --test all
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

# Run performance profiling tests
python scripts/test_profiling.py --duration 60 --requests 1000

# Test ASCII fastpath performance
python tests/performance/test_ascii_fastpath_performance.py

# Test decomposed pipeline performance
python tests/performance/test_decomposed_pipeline_performance.py

# Performance benchmarking
python tools/performance_test.py --concurrent-users 50 --duration 300
```

## Maintenance

### Regular Tasks

```bash
# Daily: Check health
curl http://localhost:8000/health
python scripts/quick_test_search.py --test health

# Weekly: Clear cache if needed
curl -X POST http://localhost:8000/admin/clear-cache \
  -H "Authorization: Bearer $API_KEY"

# Weekly: System warmup
./scripts/smoke_warmup.sh

# Monthly: Update dependencies
poetry update
make test
make docker-build

# Monthly: Elasticsearch maintenance
python scripts/elasticsearch_setup_and_warmup.py --maintenance-mode
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

# Complete emergency recovery procedure
./scripts/emergency_procedures.sh

# Elasticsearch recovery
python scripts/setup_elasticsearch.py --recovery-mode
python scripts/bulk_loader.py --input backup_entities.jsonl --entity-type person --restore

# Service warmup after recovery
./scripts/smoke_warmup.sh
python scripts/quick_test_search.py --test all
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

## Deployment Integration

### Search Integration Deployment

```bash
# Deploy search integration components
python scripts/deploy_search_integration.py

# Deploy to production with validation
python scripts/deploy_search_production.sh

# Upload data via API
python scripts/upload_data_via_api.py --data entities.jsonl --batch-size 100

# Upload via shell script
./scripts/upload_via_api.sh entities.jsonl

# Test deployment integration
python scripts/deploy_to_elasticsearch.py --test-mode
```

### API Testing Templates

```bash
# Generate AC search curl commands
python scripts/ac_search_templates.py --output curl_commands.md

# Generate vector search curl commands  
python scripts/vector_search_templates.py --output vector_curls.md

# Use predefined curl commands
./scripts/ac_search_curl_commands.md
./scripts/vector_search_curl_commands.md
```

### Rollback Procedures

```bash
# Rollback search integration
python scripts/rollback_search_integration.py --version previous

# Emergency rollback
./scripts/deploy_smartfilter_fix.sh --rollback

# Update INN cache hook (for rollback)
./scripts/update_inn_cache_hook.sh --restore-backup
```

## Additional Resources

- [API Documentation](./API.md)
- [Architecture Overview](./ARCHITECTURE_OVERVIEW.md)
- [Monitoring Guide](./MONITORING.md)
- [Security Guide](./SECURITY.md)