# 🚀 Production Deployment Guide

Complete guide for deploying the AI Service to production with monitoring, health checks, and performance optimization.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.10+ with virtual environment support
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: 10GB+ available disk space
- **Network**: Outbound HTTPS access for dependencies

### Optional Dependencies
- **Elasticsearch**: For hybrid search functionality
- **Prometheus**: For metrics collection
- **Grafana**: For metrics visualization

## 🏗️ Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                  AI Service                               │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   FastAPI App   │  │      Health Checks              │   │
│  │   Port: 8000    │  │      /health/* endpoints        │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   Orchestrator  │  │      Prometheus Metrics         │   │
│  │   9-Layer Proc. │  │      /metrics endpoint          │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                 Monitoring Stack                           │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   Prometheus    │  │        Grafana                  │   │
│  │   Port: 9090    │  │        Port: 3000               │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Steps

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd ai-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r current_requirements.txt

# Verify installation
python -c "import ai_service; print('✓ AI Service installed successfully')"
```

### 2. Configuration

#### Environment Variables

Create a `.env` file with production settings:

```bash
# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
SERVICE_WORKERS=4

# Security
ADMIN_TOKEN=<generate-secure-token>
API_KEY_ENABLED=true
CORS_ORIGINS=["https://your-domain.com"]

# Performance
MAX_INPUT_LENGTH=10000
CACHE_SIZE=1000
CONNECTION_POOL_SIZE=50

# Monitoring
PROMETHEUS_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Optional: Elasticsearch
ES_URL=https://your-elasticsearch.com:9200
ES_USERNAME=elastic
ES_PASSWORD=<password>
ES_VERIFY_SSL=true
```

#### Logging Configuration

Configure production logging in `logging.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout

  file:
    class: logging.RotatingFileHandler
    level: INFO
    formatter: json
    filename: logs/ai-service.log
    maxBytes: 100MB
    backupCount: 5

root:
  level: INFO
  handlers: [console, file]
```

### 3. Service Startup

#### Option A: Direct Python

```bash
# Development/testing
python -m uvicorn ai_service.main:app --host 0.0.0.0 --port 8000

# Production with multiple workers
python -m uvicorn ai_service.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --access-log \
  --log-level info
```

#### Option B: Gunicorn (Recommended for Production)

```bash
# Install gunicorn
pip install gunicorn

# Start with gunicorn
gunicorn ai_service.main:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info \
  --preload
```

#### Option C: Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY current_requirements.txt .
RUN pip install --no-cache-dir -r current_requirements.txt

# Copy application
COPY src/ src/
COPY docs/ docs/

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ready || exit 1

# Start service
CMD ["gunicorn", "ai_service.main:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker"]
```

Build and run:

```bash
docker build -t ai-service .
docker run -p 8000:8000 --env-file .env ai-service
```

### 4. Monitoring Setup

#### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

Start Prometheus:

```bash
# Download and start Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
./prometheus --config.file=prometheus.yml
```

#### Grafana Dashboard

Import the dashboard from `monitoring/grafana_dashboard.json` or create custom panels for:

- Request rate and latency
- Success/error rates
- Cache hit rates
- Active connections
- Memory usage

## 🏥 Health Checks

The service provides multiple health check endpoints:

### Basic Health Check
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "service": "AI Service", "version": "1.0.0", "timestamp": 1640995200.0}
```

### Detailed Health Check
```bash
curl http://localhost:8000/health/detailed
# Includes component status, performance metrics, and connection stats
```

### Kubernetes Probes
```yaml
# Liveness probe
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Readiness probe
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## 📊 Performance Optimization

### Connection Pooling

The service includes optimized HTTP connection pooling:

```python
# Automatic connection pooling is enabled by default
# Max connections: 100
# Max keepalive connections: 20
# Connection timeout: 30s
```

### Async Processing

For long texts, the service automatically uses async tokenization:

```python
# Texts longer than 1000 characters are processed asynchronously
# with chunking for optimal performance
# Speed improvement: ~98% for long texts
```

### Caching

Dictionary loading and morphological analysis are cached:

```python
# LRU cache on morphological operations
# Lazy loading of payment triggers (31.6% size reduction)
# Memory-efficient data structures
```

## 🔧 Production Configuration

### Resource Limits

Recommended production limits:

```yaml
# Kubernetes resource limits
resources:
  limits:
    memory: "4Gi"
    cpu: "2000m"
  requests:
    memory: "2Gi"
    cpu: "1000m"
```

### Security

Enable production security features:

```python
# API key authentication
API_KEY_ENABLED=true

# CORS restrictions
CORS_ORIGINS=["https://your-production-domain.com"]

# Rate limiting (if using reverse proxy)
# Nginx example:
# limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

### Auto-scaling

Configure horizontal pod autoscaling:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-service
  minReplicas: 2
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

## 📈 Monitoring and Alerting

### Key Metrics to Monitor

1. **Request Metrics**
   - Request rate (RPS)
   - Response latency (p50, p95, p99)
   - Error rate

2. **Performance Metrics**
   - Processing time
   - Cache hit rate
   - Connection pool usage

3. **Resource Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O

4. **Application Metrics**
   - Success rate
   - Component health
   - Queue length

### Alerting Rules

Create alerts for critical conditions:

```yaml
# High error rate
- alert: HighErrorRate
  expr: rate(ai_service_requests_failed_total[5m]) / rate(ai_service_requests_total[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"

# High latency
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m])) > 1000
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High response latency detected"

# Service down
- alert: ServiceDown
  expr: up{job="ai-service"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "AI Service is down"
```

## 🛠️ Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   curl http://localhost:8000/health/detailed | jq '.components'

   # Restart service if needed
   systemctl restart ai-service
   ```

2. **Slow Response Times**
   ```bash
   # Check performance metrics
   curl http://localhost:8000/metrics | grep latency

   # Check cache hit rate
   curl http://localhost:8000/health/detailed | jq '.orchestrator.cache_hit_rate'
   ```

3. **Connection Pool Exhaustion**
   ```bash
   # Check connection stats
   curl http://localhost:8000/health/detailed | jq '.components.http_client_pool'
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or modify logging config
# Set root logger level to DEBUG
```

### Performance Profiling

Use the built-in profiling endpoint:

```bash
# Get processing stats
curl http://localhost:8000/stats

# Analyze complexity for specific inputs
curl -X POST http://localhost:8000/analyze-complexity \
  -H "Content-Type: application/json" \
  -d '{"text": "your test text here"}'
```

## 🔄 Updates and Maintenance

### Rolling Updates

For zero-downtime updates:

1. Deploy new version to staging
2. Run health checks and tests
3. Gradually roll out to production
4. Monitor metrics during rollout

### Backup and Recovery

- **Configuration**: Store in version control
- **Logs**: Centralized logging system
- **Metrics**: Prometheus retention policy
- **State**: Service is stateless - no backup needed

### Maintenance Windows

Schedule regular maintenance:

- **Weekly**: Log rotation and cleanup
- **Monthly**: Dependency updates
- **Quarterly**: Performance review and optimization

## ✅ Deployment Checklist

- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Logging configured
- [ ] Service started successfully
- [ ] Health checks passing
- [ ] Metrics endpoint working
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Load balancer configured
- [ ] Auto-scaling configured
- [ ] Security features enabled
- [ ] Documentation updated

## 🎯 Performance Targets

Production performance targets:

- **Latency**: p95 < 100ms for short texts (< 1000 chars)
- **Throughput**: > 100 RPS per instance
- **Availability**: 99.9% uptime
- **Error Rate**: < 0.1%
- **Cache Hit Rate**: > 80%
- **Memory Usage**: < 4GB per instance
- **CPU Usage**: < 70% average