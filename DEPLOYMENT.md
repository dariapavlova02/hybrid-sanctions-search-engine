# 🚀 AI Service Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Git configured
- Server access (if deploying remotely)

## Quick Start

### 1. Local Development

```bash
# Clone repository
git clone <repository-url>
cd elastic-test-clean

# Setup environment
cd services/ai-service
cp env.production .env
# Edit .env with your configuration

# Install dependencies
make install-deps

# Download models
make download-models

# Run locally
make run
```

### 2. Production Deployment

```bash
# Build and deploy
make deploy

# Or manually:
docker-compose up -d
```

### 3. Server Deployment

```bash
# Push to Git
git push origin main

# On server:
ssh user@server
cd /path/to/project
git pull
make update
```

## Configuration

### Environment Variables

Key environment variables in `env.production`:

- `AI_SERVICE_ADMIN_API_KEY`: Admin API key for protected endpoints
- `AI_SERVICE_MAX_INPUT_LENGTH`: Maximum input text length
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `AI_SERVICE_ENABLE_CORS`: Enable CORS for web clients

### Security

- Change default API keys in production
- Use HTTPS in production
- Configure proper CORS origins
- Set up rate limiting

## Monitoring

### Health Checks

- Health endpoint: `GET /health`
- Metrics endpoint: `GET /metrics`
- Statistics: `GET /stats`

### Logs

```bash
# View logs
make logs

# Or with Docker
docker-compose logs -f ai-service
```

## Troubleshooting

### Common Issues

1. **SpaCy models not found**
   ```bash
   make download-models
   ```

2. **Service not starting**
   ```bash
   make logs
   # Check for error messages
   ```

3. **Memory issues**
   - Increase Docker memory limits
   - Check `AI_SERVICE_CACHE_SIZE` setting

### Performance Tuning

- Adjust `AI_SERVICE_MAX_CONCURRENT_REQUESTS`
- Tune `AI_SERVICE_CACHE_SIZE` and `AI_SERVICE_CACHE_TTL`
- Monitor memory usage with `docker stats`

## API Endpoints

- `POST /screen` - Screen text for sanctions
- `POST /process` - Process text with normalization
- `POST /process-batch` - Batch text processing
- `GET /health` - Health check
- `GET /stats` - Service statistics
- `GET /metrics` - Prometheus metrics

## Support

For issues and questions:
1. Check logs: `make logs`
2. Check health: `make health`
3. Review configuration in `env.production`
