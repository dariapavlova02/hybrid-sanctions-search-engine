# 🚀 AI Service - Unified Architecture

**Clean, consolidated AI service** for normalization and structured extraction from sanctions data with support for multiple languages (English, Russian, Ukrainian).

## ✨ **Unified Architecture Benefits**

🎯 **Single Orchestrator** - Replaced 3+ duplicate implementations with one clean `UnifiedOrchestrator`
📋 **CLAUDE.md Compliant** - Exact 9-layer specification implementation
🔍 **Structured Signals** - Persons, organizations, IDs, dates with full traceability
⚡ **Performance Optimized** - ≤10ms for short strings, comprehensive caching
🧪 **Comprehensive Testing** - 12 real payment scenarios, contract validation

## 🏗️ **9-Layer Architecture**

```
1. Validation & Sanitization  →  Basic input validation
2. Smart Filter              →  Pre-processing decision
3. Language Detection        →  ru/uk/en identification
4. Unicode Normalization     →  Text standardization
5. Name Normalization (CORE) →  Person names + org cores
6. Signals                   →  Structured extraction
7. Variants (optional)       →  Spelling alternatives
8. Embeddings (optional)     →  Vector representation
9. Decision & Response       →  Final result assembly
```

## 🎯 **Core Features**

- **📝 Text Normalization**: Morphological analysis with token-level tracing
- **🏢 Structured Extraction**: Persons with DOB/IDs, organizations with legal forms
- **🌍 Multi-language Support**: Russian, Ukrainian, English with mixed-script handling
- **🔍 Smart Filtering**: Pre-processing optimization with signal detection
- **📊 Signal Analysis**: Legal forms, payment contexts, document numbers
- **🎯 Variant Generation**: Transliteration, phonetic, morphological variants
- **⚡ High Performance**: Caching, async processing, performance monitoring

## 🔮 **Embeddings**

The EmbeddingService provides pure vector generation capabilities using multilingual sentence transformers:

### **Model Choice & Architecture**
- **Default Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Why L12 v2**: Balanced performance (384-dim) with multilingual support (ru/uk/en)
- **Output**: 32-bit float vectors, ready for downstream similarity analysis
- **Preprocessing**: Automatically removes dates/IDs - only names/organizations are embedded

### **Why Dates/IDs Are Excluded**
- **Separation of Concerns**: Names → semantic similarity, Dates/IDs → exact matching
- **Downstream Processing**: Signals layer handles structured data, Decision layer does exact matching
- **Performance**: Cleaner embeddings without noise from structured data

### **API Usage**
```python
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService

# Initialize service
config = EmbeddingConfig()
service = EmbeddingService(config)

# Single text encoding
vector = service.encode_one("Ivan Petrov")  # 384 floats

# Batch encoding (recommended)
vectors = service.encode_batch(["Ivan Petrov", "Anna Smith"])  # 2x384 floats

# Multilingual support
ru_vector = service.encode_one("Иван Петров")
uk_vector = service.encode_one("Іван Петров") 
en_vector = service.encode_one("Ivan Petrov")
# All vectors are comparable for similarity analysis
```

### **Model Switching**
```python
# Switch models via configuration
config = EmbeddingConfig(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    extra_models=["sentence-transformers/all-MiniLM-L6-v2"]
)
service = EmbeddingService(config)
```

### **Performance SLA**
- **Latency**: < 15ms single text, < 200ms for 1000 texts (p95)
- **Memory**: ~80MB model + ~1MB per 100 texts
- **Throughput**: ~100 texts/sec (CPU), ~500 texts/sec (GPU)

### **Important Notes**
- **No Indexing**: Pure vector generation - indexing handled downstream
- **No Similarity Search**: Vector similarity calculations done by other services  
- **Lazy Loading**: Models loaded only when first needed
- **Batch Processing**: Optimized for processing multiple texts efficiently

📖 **Detailed Documentation**: See [docs/embeddings.md](docs/embeddings.md) for complete usage guide

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Docker (optional)

### Local Development

1. **Install dependencies**:
   ```bash
   make install-dev
   ```

2. **Start the service**:
   ```bash
   make start
   ```

3. **Run tests**:
   ```bash
   make test
   ```

### Docker Deployment

1. **Build the image**:
   ```bash
   make docker-build
   ```

2. **Run production container**:
   ```bash
   make docker-run
   ```

3. **Run development container**:
   ```bash
   make docker-dev
   ```

## API Endpoints

### Core Endpoints

- `POST /process` - Complete text processing
- `POST /normalize` - Text normalization
- `POST /process-batch` - Batch text processing
- `POST /search-similar` - Similarity search
- `POST /analyze-complexity` - Text complexity analysis

### Administrative Endpoints (Protected)

- `POST /clear-cache` - Clear cache (requires API key)
- `POST /reset-stats` - Reset statistics (requires API key)

### Information Endpoints

- `GET /health` - Service health check
- `GET /stats` - Processing statistics
- `GET /languages` - Supported languages
- `GET /` - Service information

## Configuration

The service uses environment variables for configuration:

- `APP_ENV`: Environment (development, staging, production)
- `WORKERS`: Number of worker processes (production only)
- `DEBUG`: Enable debug mode

### Security

Administrative endpoints are protected with API key authentication. Set the key in `config.py`:

```python
SECURITY_CONFIG = {
    'admin_api_key': 'your-secure-api-key-here'
}
```

## Development

### Project Structure

```
src/ai_service/
├── services/           # Core services
│   ├── orchestrator_service.py
│   ├── normalization_service.py
│   ├── variant_generation_service.py
│   └── ...
├── data/              # Data files and templates
├── config/            # Configuration files
└── utils/             # Utility functions

tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
└── e2e/              # End-to-end tests
```

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Specific test file
poetry run pytest tests/unit/test_orchestrator_service.py -v
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Clean up
make clean
```

## Deployment

### Production

1. **Set environment**:
   ```bash
   export APP_ENV=production
   export WORKERS=4
   ```

2. **Install dependencies**:
   ```bash
   make install
   ```

3. **Start service**:
   ```bash
   make start-prod
   ```

### Docker Compose

```bash
# Production
docker-compose up ai-service

# Development
docker-compose --profile dev up ai-service-dev
```

## CI/CD

The project includes GitHub Actions workflow for automated testing:

- Runs on push to `main` and `develop` branches
- Runs on pull requests
- Installs dependencies with Poetry
- Runs tests with coverage
- Uploads coverage to Codecov

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Statistics

```bash
curl http://localhost:8000/stats
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

@ Daria Pavlova