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

## 🔍 Elasticsearch Deployment

### Quick Start

For complete deployment (data preparation + Elasticsearch loading):

```bash
# Inside Docker container (recommended for production)
docker exec ai-service-prod python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200
```

Or automatic initialization on Docker startup:

```bash
# Simply start the container - entrypoint handles everything
docker-compose up -d

# Check logs to verify initialization
docker logs ai-service
```

### What Gets Deployed

- **AC Patterns Index** (`sanctions_ac_patterns`): ~2.7M Aho-Corasick patterns for exact/fuzzy matching
- **Vectors Index** (`sanctions_vectors`): ~10K sentence-transformer embeddings for semantic search

### Deployment Options

**Option 1: Automatic (Docker Entrypoint)** - Simplest for production
```bash
docker-compose down && docker-compose up -d
# ✅ docker-entrypoint.sh automatically loads data on startup
```

**Option 2: Manual Pipeline** - Full control over deployment
```bash
# Prepare data files
python scripts/prepare_sanctions_data.py

# Deploy to Elasticsearch
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200
```

**Option 3: Complete Pipeline** - One command for everything
```bash
docker exec ai-service-prod python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200
```

### Verification

```bash
# Check indices
curl http://localhost:9200/_cat/indices?v | grep sanctions

# Expected output:
# green open sanctions_ac_patterns 1 0 2768827
# green open sanctions_vectors     1 0   10000

# Test search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Петров", "search_type": "hybrid"}'
```

📖 **Full Guide**: See [ELASTICSEARCH_DEPLOYMENT.md](./ELASTICSEARCH_DEPLOYMENT.md) for detailed deployment instructions, troubleshooting, and configuration options.

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

# Pull latest code
git pull origin main

# Rebuild and restart (automatic ES initialization)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# ✅ docker-entrypoint.sh will automatically:
#    1. Wait for Elasticsearch to be ready
#    2. Find data files in output/sanctions/
#    3. Create indices: sanctions_ac_patterns, sanctions_vectors
#    4. Load ~2.7M AC patterns (batch 5000, ~30-60s)
#    5. Load ~10K vectors (batch 1000, ~10-20s)
#    6. Run warmup queries
#    7. Start the application

# Verify deployment
docker logs ai-service-prod | head -100
curl http://localhost:9200/_cat/indices?v | grep sanctions
```

### Manual Data Loading (Inside Container)

```bash
# When you need manual control over deployment
docker exec -it ai-service-prod python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200

# This runs complete chain:
# 1. Check source files
# 2. Generate AC patterns + vectors (if needed)
# 3. Deploy to Elasticsearch
# 4. Verify deployment
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
