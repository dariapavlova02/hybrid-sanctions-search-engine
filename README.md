# AI Service for Sanctions Data Verification

AI service for normalization and variant generation of sanctions data with support for multiple languages (English, Russian, Ukrainian).

## Features

- **Text Normalization**: Advanced text processing with Unicode cleaning and morphological analysis
- **Variant Generation**: Multiple algorithms for generating spelling variants (transliteration, phonetic, morphological)
- **Multi-language Support**: English, Russian, and Ukrainian with automatic language detection
- **Caching**: LRU cache with TTL support for improved performance
- **Signal Detection**: Pattern matching for sanctions data
- **Embedding Generation**: Vector representations for similarity search
- **Batch Processing**: Efficient processing of multiple texts
- **Health Monitoring**: Comprehensive health checks and statistics

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