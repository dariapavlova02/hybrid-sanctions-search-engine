# Configuration Guide

This document provides comprehensive guidance for configuring the AI Service, with special focus on the search layer configuration and hot-reloading capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Search Layer Configuration](#search-layer-configuration)
3. [Environment Variables](#environment-variables)
4. [Configuration Validation](#configuration-validation)
5. [Hot-Reloading](#hot-reloading)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Migration Guide](#migration-guide)

## Overview

The AI Service uses a layered configuration system that supports:

- **Environment Variable Overrides**: All configuration can be overridden via environment variables
- **Hot-Reloading**: Configuration changes can be applied without service restart
- **Validation**: Comprehensive validation ensures configuration correctness
- **Fallback Mechanisms**: Graceful degradation when services are unavailable

## Search Layer Configuration

The search layer provides hybrid search capabilities combining AC (exact) and Vector (kNN) search modes with Elasticsearch as the primary backend.

### Core Settings

#### Elasticsearch Connection

```yaml
# Elasticsearch hosts (comma-separated)
ES_HOSTS: "localhost:9200,localhost:9201"

# Authentication (choose one)
ES_USERNAME: "elastic"
ES_PASSWORD: "password"
# OR
ES_API_KEY: "your-api-key"

# SSL/TLS settings
ES_VERIFY_CERTS: "true"
ES_CA_CERTS: "/path/to/ca.crt"

# Connection settings
ES_TIMEOUT: "30"
```

#### Search Behavior

```yaml
# Enable hybrid search (AC + Vector)
ENABLE_HYBRID_SEARCH: "true"

# Enable escalation from AC to Vector search
ENABLE_ESCALATION: "true"
ESCALATION_THRESHOLD: "0.8"

# Enable fallback to local indexes
ENABLE_FALLBACK: "true"
FALLBACK_THRESHOLD: "0.3"
```

#### Vector Search

```yaml
# Vector dimension (must match embedding model)
VECTOR_DIMENSION: "384"

# Similarity threshold for vector search
VECTOR_SIMILARITY_THRESHOLD: "0.7"
```

#### Performance Tuning

```yaml
# Maximum concurrent requests
MAX_CONCURRENT_REQUESTS: "10"

# Request timeout in milliseconds
REQUEST_TIMEOUT_MS: "5000"
```

#### Caching

```yaml
# Enable embedding cache
ENABLE_EMBEDDING_CACHE: "true"

# Cache size (number of entries)
EMBEDDING_CACHE_SIZE: "1000"

# Cache TTL in seconds
EMBEDDING_CACHE_TTL_SECONDS: "3600"
```

### Configuration Validation

All configuration values are validated with the following rules:

#### Host Validation
- Must include port (host:port format)
- Port must be between 1 and 65535
- At least one host must be specified

#### Timeout Validation
- Must be positive
- ES_TIMEOUT: 1-300 seconds
- REQUEST_TIMEOUT_MS: 1-30000 milliseconds

#### Threshold Validation
- Must be between 0.0 and 1.0
- ESCALATION_THRESHOLD: > 0.5 for meaningful escalation
- FALLBACK_THRESHOLD: > 0.1 for meaningful fallback
- VECTOR_SIMILARITY_THRESHOLD: > 0.3 for meaningful similarity

#### Dimension Validation
- VECTOR_DIMENSION: 1-4096
- Must match your embedding model's output dimension

#### Cache Validation
- EMBEDDING_CACHE_SIZE: 1-100000
- EMBEDDING_CACHE_TTL_SECONDS: 1-86400 (24 hours)

## Environment Variables

### Complete Environment Variable Reference

| Variable | Default | Description | Validation |
|----------|---------|-------------|------------|
| `ES_HOSTS` | `localhost:9200` | Elasticsearch hosts (comma-separated) | host:port format |
| `ES_USERNAME` | `None` | Elasticsearch username | string |
| `ES_PASSWORD` | `None` | Elasticsearch password | string |
| `ES_API_KEY` | `None` | Elasticsearch API key | string |
| `ES_VERIFY_CERTS` | `true` | Verify SSL certificates | boolean |
| `ES_TIMEOUT` | `30` | Connection timeout (seconds) | 1-300 |
| `ENABLE_HYBRID_SEARCH` | `true` | Enable hybrid search | boolean |
| `ENABLE_ESCALATION` | `true` | Enable AC→Vector escalation | boolean |
| `ESCALATION_THRESHOLD` | `0.8` | AC score threshold for escalation | 0.0-1.0 |
| `ENABLE_FALLBACK` | `true` | Enable fallback to local indexes | boolean |
| `FALLBACK_THRESHOLD` | `0.3` | Score threshold for fallback | 0.0-1.0 |
| `VECTOR_DIMENSION` | `384` | Vector dimension | 1-4096 |
| `VECTOR_SIMILARITY_THRESHOLD` | `0.7` | Vector similarity threshold | 0.0-1.0 |
| `MAX_CONCURRENT_REQUESTS` | `10` | Max concurrent requests | 1-100 |
| `REQUEST_TIMEOUT_MS` | `5000` | Request timeout (ms) | 1-30000 |
| `ENABLE_EMBEDDING_CACHE` | `true` | Enable embedding cache | boolean |
| `EMBEDDING_CACHE_SIZE` | `1000` | Cache size (entries) | 1-100000 |
| `EMBEDDING_CACHE_TTL_SECONDS` | `3600` | Cache TTL (seconds) | 1-86400 |

### Environment File Example

Create a `.env` file in your project root:

```bash
# Elasticsearch Configuration
ES_HOSTS=localhost:9200,localhost:9201
ES_USERNAME=elastic
ES_PASSWORD=your_password
ES_VERIFY_CERTS=true
ES_TIMEOUT=30

# Search Configuration
ENABLE_HYBRID_SEARCH=true
ENABLE_ESCALATION=true
ESCALATION_THRESHOLD=0.8
ENABLE_FALLBACK=true
FALLBACK_THRESHOLD=0.3

# Vector Search
VECTOR_DIMENSION=384
VECTOR_SIMILARITY_THRESHOLD=0.7

# Performance
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT_MS=5000

# Caching
ENABLE_EMBEDDING_CACHE=true
EMBEDDING_CACHE_SIZE=1000
EMBEDDING_CACHE_TTL_SECONDS=3600
```

## Configuration Validation

### Validation Levels

1. **Field Validation**: Individual field values are validated
2. **Consistency Validation**: Related settings are validated together
3. **Runtime Validation**: Configuration is tested against actual services

### Validation Endpoints

#### Validate Configuration
```bash
curl -X POST "http://localhost:8000/validate-config" \
  -H "Authorization: Bearer your-admin-token"
```

Response:
```json
{
  "search_service": {
    "enabled": true,
    "validation_passed": true,
    "errors": [],
    "warnings": [
      "Elasticsearch cluster status: yellow"
    ]
  }
}
```

#### Get Configuration Status
```bash
curl -X GET "http://localhost:8000/config-status" \
  -H "Authorization: Bearer your-admin-token"
```

Response:
```json
{
  "search_service": {
    "enabled": true,
    "hot_reload": true,
    "reload_stats": {
      "last_reload": "2023-01-01T00:00:00",
      "reload_count": 5,
      "watcher_running": true
    }
  }
}
```

### Common Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `At least one Elasticsearch host must be specified` | Empty ES_HOSTS | Set ES_HOSTS to valid host:port |
| `Host must include port` | Missing port in host | Use host:port format |
| `Invalid port number` | Non-numeric port | Use numeric port (1-65535) |
| `Timeout must be positive` | Negative timeout | Use positive timeout value |
| `Thresholds must be between 0.0 and 1.0` | Invalid threshold | Use value between 0.0 and 1.0 |
| `Escalation threshold should be greater than 0.5` | Low escalation threshold | Use threshold > 0.5 |
| `Fallback threshold should be greater than 0.1` | Low fallback threshold | Use threshold > 0.1 |
| `Vector similarity threshold should be greater than 0.3` | Low similarity threshold | Use threshold > 0.3 |
| `Embedding cache size should be at least 100` | Small cache size | Use cache size >= 100 |

## Hot-Reloading

### Overview

Configuration hot-reloading allows you to update settings without restarting the service. This is particularly useful for:

- Tuning search parameters
- Adjusting performance settings
- Updating Elasticsearch connection details
- Modifying cache settings

### How It Works

1. **File Watching**: The service watches configuration files for changes
2. **Environment Monitoring**: Environment variables are monitored for changes
3. **Automatic Reload**: Changes trigger automatic configuration reload
4. **Validation**: New configuration is validated before applying
5. **Rollback**: Invalid configuration triggers rollback to previous state

### Enabling Hot-Reloading

Hot-reloading is enabled by default for SearchConfig. The service automatically:

1. Watches `.env` file for changes
2. Watches `config/settings.py` for changes
3. Monitors environment variables for changes
4. Reloads configuration when changes are detected

### Manual Configuration Reload

You can manually trigger configuration reload:

```bash
curl -X POST "http://localhost:8000/reload-config" \
  -H "Authorization: Bearer your-admin-token"
```

Response:
```json
{
  "message": "Configuration reloaded successfully"
}
```

### Hot-Reloading Statistics

Monitor hot-reloading activity:

```bash
curl -X GET "http://localhost:8000/config-status" \
  -H "Authorization: Bearer your-admin-token"
```

### Best Practices for Hot-Reloading

1. **Test Changes**: Always test configuration changes in a development environment first
2. **Monitor Logs**: Watch service logs for configuration reload events
3. **Validate Changes**: Use the validation endpoint to check configuration before applying
4. **Backup Configuration**: Keep backups of working configurations
5. **Gradual Changes**: Make small, incremental changes rather than large updates

## Best Practices

### General Configuration

1. **Use Environment Variables**: Prefer environment variables over hardcoded values
2. **Validate Early**: Use validation endpoints to catch configuration errors early
3. **Monitor Performance**: Adjust settings based on performance metrics
4. **Document Changes**: Keep track of configuration changes and their impact

### Elasticsearch Configuration

1. **Multiple Hosts**: Use multiple Elasticsearch hosts for high availability
2. **Connection Pooling**: Adjust timeout and connection settings based on cluster size
3. **SSL/TLS**: Always use SSL/TLS in production environments
4. **Authentication**: Use strong authentication credentials

### Search Configuration

1. **Threshold Tuning**: Start with default thresholds and adjust based on results
2. **Fallback Strategy**: Always enable fallback for production environments
3. **Cache Sizing**: Size caches based on expected load and memory availability
4. **Performance Monitoring**: Monitor search performance and adjust accordingly

### Performance Tuning

1. **Concurrent Requests**: Adjust based on Elasticsearch cluster capacity
2. **Timeouts**: Set timeouts based on expected response times
3. **Cache TTL**: Balance cache hit rate with memory usage
4. **Vector Dimensions**: Use appropriate dimensions for your use case

## Troubleshooting

### Common Issues

#### Configuration Not Reloading

**Symptoms**: Changes to environment variables or config files don't take effect

**Solutions**:
1. Check if hot-reloading is enabled: `GET /config-status`
2. Verify file permissions for watched files
3. Check service logs for reload errors
4. Manually trigger reload: `POST /reload-config`

#### Validation Errors

**Symptoms**: Configuration validation fails with errors

**Solutions**:
1. Check error messages for specific validation failures
2. Use the validation endpoint to identify issues
3. Review configuration values against validation rules
4. Check for typos in environment variable names

#### Elasticsearch Connection Issues

**Symptoms**: Cannot connect to Elasticsearch cluster

**Solutions**:
1. Verify Elasticsearch hosts are accessible
2. Check authentication credentials
3. Verify SSL/TLS configuration
4. Check network connectivity and firewall rules

#### Performance Issues

**Symptoms**: Slow search performance or timeouts

**Solutions**:
1. Adjust timeout settings
2. Reduce concurrent request limits
3. Optimize Elasticsearch cluster
4. Enable and tune caching

### Debugging Configuration

#### Enable Debug Logging

Set log level to DEBUG to see detailed configuration information:

```bash
export LOG_LEVEL=DEBUG
```

#### Check Configuration Status

Use the configuration status endpoint to see current settings:

```bash
curl -X GET "http://localhost:8000/config-status" \
  -H "Authorization: Bearer your-admin-token"
```

#### Validate Configuration

Use the validation endpoint to check configuration:

```bash
curl -X POST "http://localhost:8000/validate-config" \
  -H "Authorization: Bearer your-admin-token"
```

### Log Analysis

Look for these log messages:

- `Configuration reloaded: SearchConfig (count: N)` - Successful reload
- `Configuration validation failed: <error>` - Validation error
- `Failed to update search service configuration: <error>` - Update error
- `Hot-reloading enabled for search configuration` - Hot-reload enabled
- `Search service configuration updated successfully` - Update success

## Migration Guide

### From Basic to Advanced Configuration

If you're upgrading from a basic configuration to use the advanced search features:

1. **Enable Search Service**: Set `ENABLE_SEARCH=true`
2. **Configure Elasticsearch**: Set up Elasticsearch connection
3. **Enable Hot-Reloading**: Hot-reloading is enabled by default
4. **Validate Configuration**: Use validation endpoints to check setup

### Configuration Migration Steps

1. **Backup Current Configuration**: Save your current environment variables
2. **Update Environment Variables**: Add new search-related variables
3. **Test Configuration**: Use validation endpoints to test new settings
4. **Deploy Gradually**: Deploy changes in stages
5. **Monitor Performance**: Watch for any performance impacts

### Example Migration

**Before** (Basic configuration):
```bash
# Basic service configuration
SERVICE_NAME=ai-service
LOG_LEVEL=INFO
```

**After** (Advanced configuration):
```bash
# Basic service configuration
SERVICE_NAME=ai-service
LOG_LEVEL=INFO

# Search service configuration
ENABLE_SEARCH=true
ES_HOSTS=localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=password
ENABLE_HYBRID_SEARCH=true
ENABLE_ESCALATION=true
ESCALATION_THRESHOLD=0.8
ENABLE_FALLBACK=true
FALLBACK_THRESHOLD=0.3
VECTOR_DIMENSION=384
VECTOR_SIMILARITY_THRESHOLD=0.7
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT_MS=5000
ENABLE_EMBEDDING_CACHE=true
EMBEDDING_CACHE_SIZE=1000
EMBEDDING_CACHE_TTL_SECONDS=3600
```

### Rollback Plan

If you need to rollback configuration changes:

1. **Restore Environment Variables**: Restore previous environment variables
2. **Reload Configuration**: Use `POST /reload-config` to apply changes
3. **Validate Configuration**: Use `POST /validate-config` to check setup
4. **Monitor Service**: Watch for any issues

## Conclusion

This configuration guide provides comprehensive information for setting up and managing the AI Service search layer. For additional support or questions, please refer to the service logs or contact the development team.

Remember to:
- Always validate configuration before applying changes
- Test changes in development environments first
- Monitor service performance after configuration changes
- Keep backups of working configurations
- Use hot-reloading for non-critical changes
- Restart the service for critical configuration changes
