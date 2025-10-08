# 📚 AI Service Documentation

Welcome to the comprehensive documentation for AI Service - a multilingual text processing and search system.

## 🚀 Quick Start

- **[Main README](../README.md)** - Project overview and quick start guide
- **[API Documentation](./API.md)** - Complete API reference
- **[Deployment Guide](./DEPLOYMENT.md)** - Production deployment instructions

## 🏗️ Architecture & Design

- **[Architecture Overview](./ARCHITECTURE.md)** - System architecture and 9-layer pipeline
- **[Architecture Overview (Legacy)](./ARCHITECTURE_OVERVIEW.md)** - Detailed technical architecture
- **[Data Pipeline](./DATA_PIPELINE.md)** - Data flow and processing stages

## 🔧 Configuration

- **[Configuration Guide](./CONFIGURATION.md)** - Configuration options and environment variables
- **[Feature Flags](./FEATURE_FLAGS.md)** - Runtime feature toggles
- **[Production Configuration](./PRODUCTION_CONFIGURATION.md)** - Production-specific settings

## 🔍 Search System

- **[Search API](./SEARCH_API.md)** - Search endpoints and usage
- **[Search Configuration](./SEARCH_CONFIGURATION.md)** - Search system configuration
- **[Hybrid Search Runbook](./hybrid-search-runbook.md)** - Search operations and troubleshooting
- **[Search System Stability](./search-system-stability.md)** - Search reliability and monitoring
- **[Search Troubleshooting](./SEARCH_TROUBLESHOOTING.md)** - Common search issues and solutions

## 🧠 Processing Components

- **[Embeddings](./embeddings.md)** - Vector embedding generation and models
- **[Morphology Adapter](./MORPHOLOGY_ADAPTER.md)** - Morphological analysis components
- **[Normalization Tokenizer](./NORMALIZATION_TOKENIZER.md)** - Text tokenization and normalization
- **[Elasticsearch Watchlist Adapter](./ELASTICSEARCH_WATCHLIST_ADAPTER.md)** - Elasticsearch integration

## 📊 Monitoring & Performance

- **[Profiling Guide](./PROFILING_README.md)** - Performance profiling and optimization
- **[Production Deployment](./PRODUCTION_DEPLOYMENT.md)** - Production deployment best practices

## 📋 Document Categories

### 🚀 Getting Started
- New to AI Service? Start with the [main README](../README.md)
- Need to deploy? Check the [Deployment Guide](./DEPLOYMENT.md)
- Want to use the API? See the [API Documentation](./API.md)

### 🏗️ Understanding the System
- Learn about the [9-layer architecture](./ARCHITECTURE.md)
- Understand the [data pipeline](./DATA_PIPELINE.md)
- Explore [configuration options](./CONFIGURATION.md)

### 🔍 Search & Analysis
- Master the [search API](./SEARCH_API.md)
- Configure [search system](./SEARCH_CONFIGURATION.md)
- Troubleshoot [search issues](./SEARCH_TROUBLESHOOTING.md)

### 🛠️ Advanced Topics
- Work with [embeddings](./embeddings.md)
- Configure [feature flags](./FEATURE_FLAGS.md)
- Optimize with [profiling](./PROFILING_README.md)

### 🚀 Production
- Deploy to [production](./PRODUCTION_DEPLOYMENT.md)
- Configure [production settings](./PRODUCTION_CONFIGURATION.md)
- Ensure [system stability](./search-system-stability.md)

## 🔗 Quick Links

### Development
- **Installation**: `make install-dev`
- **Start Service**: `make start`
- **Run Tests**: `make test`
- **API Docs**: http://localhost:8000/docs

### Production
- **Health Check**: `/health`
- **Metrics**: `/metrics`
- **Statistics**: `/stats`
- **Admin**: `/admin/*` (requires API key)

### Monitoring
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

## 📞 Support & Contributing

### Getting Help
- **Documentation**: Browse these docs
- **API Reference**: [API.md](./API.md)
- **Troubleshooting**: [Search Troubleshooting](./SEARCH_TROUBLESHOOTING.md)

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Reporting Issues
- **Bug Reports**: Use GitHub Issues
- **Feature Requests**: Use GitHub Discussions
- **Security Issues**: Contact maintainers directly

## 📈 Documentation Metrics

- **Total Documents**: 18
- **Core Categories**: 6
- **API Endpoints**: 15+
- **Configuration Options**: 50+
- **Deployment Options**: 5+

## 🔄 Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| [API.md](./API.md) | ✅ Complete | 2024-01-15 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | ✅ Complete | 2024-01-15 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | ✅ Complete | 2024-01-15 |
| [CONFIGURATION.md](./CONFIGURATION.md) | ✅ Complete | 2024-01-15 |
| [SEARCH_API.md](./SEARCH_API.md) | ✅ Complete | 2024-01-15 |
| [FEATURE_FLAGS.md](./FEATURE_FLAGS.md) | ✅ Complete | 2024-01-15 |

---

**Legend:**
- ✅ Complete and up-to-date
- 🔄 In progress
- 📋 Planned
- ⚠️ Needs update

## 🎯 Navigation Tips

1. **New Users**: Start with [Main README](../README.md) → [API.md](./API.md) → [DEPLOYMENT.md](./DEPLOYMENT.md)
2. **Developers**: [ARCHITECTURE.md](./ARCHITECTURE.md) → [CONFIGURATION.md](./CONFIGURATION.md) → [FEATURE_FLAGS.md](./FEATURE_FLAGS.md)
3. **Operators**: [DEPLOYMENT.md](./DEPLOYMENT.md) → [PRODUCTION_CONFIGURATION.md](./PRODUCTION_CONFIGURATION.md) → [SEARCH_TROUBLESHOOTING.md](./SEARCH_TROUBLESHOOTING.md)
4. **Researchers**: [embeddings.md](./embeddings.md) → [SEARCH_API.md](./SEARCH_API.md) → [hybrid-search-runbook.md](./hybrid-search-runbook.md)

---

*Last updated: January 15, 2024*