# 🚀 AI Service

Multilingual text normalization and structured extraction system with advanced search capabilities.

## ✨ Features

- **🌍 Multilingual Support**: English, Russian, Ukrainian with mixed-script handling
- **🔍 Smart Processing**: 9-layer architecture for comprehensive text analysis
- **⚡ High Performance**: Sub-100ms processing with intelligent caching
- **🎯 Structured Extraction**: Persons, organizations, dates, IDs with confidence scores
- **🔎 Hybrid Search**: Combined AC (Aho-Corasick) and vector search
- **📊 Comprehensive Monitoring**: Prometheus metrics and Grafana dashboards

## 🏗️ Architecture

Clean 9-layer processing pipeline:

```
1. Validation & Sanitization → Input validation and security
2. Smart Filter              → Pre-processing optimization
3. Language Detection        → ru/uk/en identification
4. Unicode Normalization     → Text standardization
5. Name Normalization        → Morphological analysis (CORE)
6. Signals Extraction        → Structured data extraction
7. Variants Generation       → Spelling alternatives
8. Embeddings Generation     → Vector representation
9. Decision & Response       → Result assembly
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Poetry (recommended)

### Installation

```bash
# Clone repository
git clone [rep]
cd ai-service

# Install dependencies
make install-dev

# Start development server
make start
```

### Docker Deployment

```bash
# Build and run
make docker-build
make docker-run

# Or with docker-compose
docker-compose up ai-service
```

## 📚 API Documentation

### Core Endpoints

```bash
# Process text
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Иван Иванов 15.05.1985"}'

# Hybrid search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Ivan Petrov", "search_type": "hybrid"}'

# Health check
curl http://localhost:8000/health
```

### Response Example

```json
{
  "processed_text": "иван иванов 15.05.1985",
  "language": "ru",
  "signals": {
    "persons": [
      {
        "name": "Иван Иванов",
        "confidence": 0.95,
        "position": {"start": 0, "end": 11}
      }
    ],
    "dates": [
      {
        "value": "15.05.1985",
        "normalized": "1985-05-15",
        "confidence": 0.98
      }
    ]
  },
  "processing_time_ms": 45
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Core settings
APP_ENV=production
WORKERS=4
DEBUG=false

# Security
ADMIN_API_KEY=your-secure-key

# Search
ELASTICSEARCH_URL=http://localhost:9200
ENABLE_VECTOR_SEARCH=true

# Performance
CACHE_TTL=3600
MAX_BATCH_SIZE=100
```

### Feature Flags

```python
FEATURE_FLAGS = {
    "use_factory_normalizer": True,
    "enable_search_optimizations": True,
    "enhanced_accuracy_mode": False
}
```

## 🧪 Testing

```bash
# Run all tests
make test

# With coverage
make test-cov

# Specific test categories
poetry run pytest -m unit -v
poetry run pytest -m integration -v
poetry run pytest -m performance -v
```

## 📊 Monitoring

### Health & Metrics

```bash
# Service health
curl http://localhost:8000/health

# Processing statistics
curl http://localhost:8000/stats

# Prometheus metrics
curl http://localhost:9090/metrics
```

### Grafana Dashboard

Access at `http://localhost:3000` (admin/admin)

- Processing latency and throughput
- Cache hit rates and memory usage
- Error rates and language distribution
- Search performance metrics

## 🐳 Docker Production

### Production Deployment

```bash
# Production image
docker build -f Dockerfile.prod -t ai-service:latest .

# Run with limits
docker run -d \
  --name ai-service \
  -p 8000:8000 \
  --memory=4g \
  --cpus=2 \
  --env-file env.production \
  ai-service:latest
```

### Docker Compose

```bash
# Full stack with monitoring
docker-compose -f docker-compose.prod.yml \
  -f monitoring/docker-compose.monitoring.yml up -d
```

## ☸️ Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/
kubectl apply -f monitoring/

# Check status
kubectl get pods -l app=ai-service
kubectl logs -f deployment/ai-service
```

## 📖 Documentation

- **[API Reference](./docs/API.md)** - Complete API documentation
- **[Architecture](./docs/ARCHITECTURE.md)** - System architecture and design
- **[Deployment](./docs/DEPLOYMENT.md)** - Production deployment guide
- **[Configuration](./docs/CONFIGURATION.md)** - Configuration options
- **[Monitoring](./docs/MONITORING.md)** - Monitoring and observability

## 🔒 Security

- **API Authentication**: Bearer token for admin endpoints
- **Input Validation**: Comprehensive validation and sanitization
- **Rate Limiting**: Configurable request throttling
- **TLS Encryption**: Secure communications
- **Secrets Management**: Secure credential storage

## ⚡ Performance

### Benchmarks

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Text processing | 15ms | 45ms | 80ms |
| Hybrid search | 20ms | 50ms | 100ms |
| Batch processing (10) | 80ms | 150ms | 250ms |

### Optimization Features

- **Multi-level Caching**: LRU, TTL, and persistent caches
- **Async Processing**: Non-blocking operations
- **Connection Pooling**: Efficient resource usage
- **Batch Processing**: Optimized for throughput

## 🛠️ Development

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type checking
make typecheck
```

### Project Structure

```
src/ai_service/
├── core/                   # Unified orchestrator
├── layers/                 # Processing layers
├── search/                 # Hybrid search system
├── monitoring/             # Metrics and monitoring
├── utils/                  # Shared utilities
├── config/                 # Configuration
└── api/                    # FastAPI endpoints

tests/
├── unit/                   # Component tests
├── integration/            # Service tests
├── e2e/                    # End-to-end tests
└── performance/            # Performance tests
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

- **Documentation**: [./docs/](./docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/ai-service/issues)
- **API Reference**: [./docs/API.md](./docs/API.md)
