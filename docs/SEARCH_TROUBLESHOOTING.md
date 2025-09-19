# Search Troubleshooting Guide

## Overview

This guide helps diagnose and resolve common issues with the Search layer in the AI Service. It covers connection problems, performance issues, configuration errors, and provides step-by-step solutions.

## Quick Diagnostic Commands

### Health Check

```bash
# Check overall search service health
curl -X GET "http://localhost:8000/api/v1/search/health"

# Check Elasticsearch connectivity
curl -X GET "http://localhost:8000/api/v1/search/health/elasticsearch"

# Check cache status
curl -X GET "http://localhost:8000/api/v1/search/health/cache"
```

### Logs

```bash
# View search service logs
docker logs ai-service-search

# View Elasticsearch logs
docker logs elasticsearch

# View specific error logs
grep "ERROR" /var/log/ai-service/search.log
```

## Common Issues and Solutions

### 1. Elasticsearch Connection Issues

#### Problem: "Elasticsearch connection failed"

**Symptoms**:
- Search requests return 503 errors
- Health check shows "unhealthy" status
- Logs show connection timeout errors

**Diagnosis**:
```bash
# Test Elasticsearch connectivity
curl -X GET "http://localhost:9200/_cluster/health"

# Check if Elasticsearch is running
docker ps | grep elasticsearch

# Test from search service
curl -X GET "http://localhost:8000/api/v1/search/health/elasticsearch"
```

**Solutions**:

1. **Elasticsearch not running**:
   ```bash
   # Start Elasticsearch
   docker-compose up -d elasticsearch
   
   # Or start manually
   docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.0.0
   ```

2. **Wrong host/port configuration**:
   ```yaml
   # Check configuration
   search:
     elasticsearch:
       hosts: ["localhost:9200"]  # Ensure correct host:port
   ```

3. **Network connectivity issues**:
   ```bash
   # Test network connectivity
   telnet localhost 9200
   
   # Check firewall rules
   sudo ufw status
   ```

4. **Authentication issues**:
   ```yaml
   # Enable authentication if required
   search:
     elasticsearch:
       enable_elasticsearch_auth: true
       es_auth_type: "basic"
       es_username: "elastic"
       es_password: "password"
   ```

#### Problem: "Elasticsearch cluster is red"

**Symptoms**:
- Elasticsearch health check returns "red"
- Search performance is degraded
- Some indices are unavailable

**Solutions**:

1. **Check cluster status**:
   ```bash
   curl -X GET "http://localhost:9200/_cluster/health?pretty"
   ```

2. **Check node status**:
   ```bash
   curl -X GET "http://localhost:9200/_cat/nodes?v"
   ```

3. **Check indices**:
   ```bash
   curl -X GET "http://localhost:9200/_cat/indices?v"
   ```

4. **Restart Elasticsearch**:
   ```bash
   docker-compose restart elasticsearch
   ```

### 2. Search Performance Issues

#### Problem: Slow search response times

**Symptoms**:
- Search requests take > 1 second
- High CPU usage during searches
- Timeout errors

**Diagnosis**:
```bash
# Check search performance metrics
curl -X GET "http://localhost:8000/api/v1/search/stats/performance"

# Check Elasticsearch performance
curl -X GET "http://localhost:9200/_nodes/stats?pretty"
```

**Solutions**:

1. **Enable query optimization**:
   ```yaml
   search:
     enable_query_optimization: true
     ac_query_boost_factor: 1.2
     vector_query_boost_factor: 1.1
     bm25_query_boost_factor: 1.0
   ```

2. **Increase cache sizes**:
   ```yaml
   search:
     search_cache_size: 2000
     query_cache_size: 5000
     embedding_cache_size: 1000
   ```

3. **Optimize Elasticsearch settings**:
   ```yaml
   search:
     elasticsearch:
       maxsize: 50
       http_compress: true
       sniff_on_start: true
   ```

4. **Check Elasticsearch performance**:
   ```bash
   # Check cluster performance
   curl -X GET "http://localhost:9200/_cluster/stats?pretty"
   
   # Check node performance
   curl -X GET "http://localhost:9200/_nodes/stats?pretty"
   ```

#### Problem: High memory usage

**Symptoms**:
- High memory consumption
- Out of memory errors
- System slowdown

**Solutions**:

1. **Reduce cache sizes**:
   ```yaml
   search:
     search_cache_size: 100
     query_cache_size: 200
     embedding_cache_size: 500
   ```

2. **Optimize connection pooling**:
   ```yaml
   search:
     elasticsearch:
       maxsize: 10
       sniff_interval: 120
   ```

3. **Enable cache eviction**:
   ```yaml
   search:
     enable_search_cache: true
     search_cache_ttl_seconds: 600  # 10 minutes
   ```

### 3. Configuration Issues

#### Problem: "Invalid configuration"

**Symptoms**:
- Service fails to start
- Configuration validation errors
- Unexpected behavior

**Diagnosis**:
```bash
# Validate configuration
python -m ai_service.config.validate

# Check configuration syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

**Solutions**:

1. **Fix YAML syntax**:
   ```yaml
   # Ensure proper indentation
   search:
     enable_search: true
     elasticsearch:
       hosts: ["localhost:9200"]
   ```

2. **Validate required fields**:
   ```yaml
   # Ensure all required fields are present
   search:
     enable_search: true
     elasticsearch:
       hosts: ["localhost:9200"]
       timeout: 30
   ```

3. **Check data types**:
   ```yaml
   # Ensure correct data types
   search:
     search_cache_size: 500  # integer, not string
     default_threshold: 0.5  # float, not string
   ```

#### Problem: "Configuration hot-reload failed"

**Symptoms**:
- Configuration changes not applied
- Service needs restart for changes
- Hot-reload errors in logs

**Solutions**:

1. **Enable hot-reload**:
   ```yaml
   search:
     enable_hot_reload: true
     hot_reload_interval: 30
   ```

2. **Check file permissions**:
   ```bash
   # Ensure config file is readable
   chmod 644 config.yaml
   ```

3. **Validate configuration before reload**:
   ```bash
   # Test configuration before applying
   python -m ai_service.config.validate
   ```

### 4. Cache Issues

#### Problem: "Cache not working"

**Symptoms**:
- No cache hits in metrics
- Slow response times
- High Elasticsearch load

**Diagnosis**:
```bash
# Check cache statistics
curl -X GET "http://localhost:8000/api/v1/search/stats/cache"

# Check cache configuration
curl -X GET "http://localhost:8000/api/v1/search/health/cache"
```

**Solutions**:

1. **Enable caching**:
   ```yaml
   search:
     enable_search_cache: true
     enable_query_caching: true
     enable_embedding_cache: true
   ```

2. **Increase cache sizes**:
   ```yaml
   search:
     search_cache_size: 1000
     query_cache_size: 2000
     embedding_cache_size: 1000
   ```

3. **Check cache TTL**:
   ```yaml
   search:
     search_cache_ttl_seconds: 1800  # 30 minutes
     query_cache_ttl_seconds: 3600   # 1 hour
   ```

#### Problem: "Cache memory leak"

**Symptoms**:
- Continuously increasing memory usage
- Cache size exceeds limits
- System slowdown

**Solutions**:

1. **Enable cache eviction**:
   ```yaml
   search:
     enable_cache_eviction: true
     cache_eviction_policy: "lru"
   ```

2. **Reduce cache sizes**:
   ```yaml
   search:
     search_cache_size: 500
     query_cache_size: 1000
   ```

3. **Clear cache periodically**:
   ```bash
   # Clear search cache
   curl -X POST "http://localhost:8000/api/v1/search/cache/clear"
   ```

### 5. Authentication Issues

#### Problem: "Authentication failed"

**Symptoms**:
- 401 Unauthorized errors
- Elasticsearch connection refused
- Authentication errors in logs

**Solutions**:

1. **Check credentials**:
   ```yaml
   search:
     elasticsearch:
       enable_elasticsearch_auth: true
       es_username: "elastic"
       es_password: "password"
   ```

2. **Verify authentication type**:
   ```yaml
   search:
     elasticsearch:
       es_auth_type: "basic"  # or "api_key"
   ```

3. **Check Elasticsearch security**:
   ```bash
   # Test authentication
   curl -u elastic:password "http://localhost:9200/_cluster/health"
   ```

#### Problem: "Rate limit exceeded"

**Symptoms**:
- 429 Too Many Requests errors
- Rate limit warnings in logs
- Search requests blocked

**Solutions**:

1. **Increase rate limit**:
   ```yaml
   search:
     enable_rate_limiting: true
     rate_limit_requests_per_minute: 1000
   ```

2. **Disable rate limiting**:
   ```yaml
   search:
     enable_rate_limiting: false
   ```

3. **Implement client-side throttling**:
   ```python
   import time
   
   def search_with_throttle(query, delay=0.1):
       time.sleep(delay)
       return search_api.search(query)
   ```

### 6. Fallback Issues

#### Problem: "Fallback service unavailable"

**Symptoms**:
- Fallback errors in logs
- Search fails when Elasticsearch is down
- No fallback results

**Solutions**:

1. **Check fallback services**:
   ```bash
   # Check WatchlistIndexService
   curl -X GET "http://localhost:8000/api/v1/watchlist/health"
   
   # Check EnhancedVectorIndex
   curl -X GET "http://localhost:8000/api/v1/vector/health"
   ```

2. **Enable fallback**:
   ```yaml
   search:
     enable_fallback: true
     fallback_threshold: 0.3
   ```

3. **Check fallback configuration**:
   ```yaml
   search:
     fallback:
       watchlist_index:
         enabled: true
         timeout: 5
       vector_index:
         enabled: true
         timeout: 5
   ```

## Advanced Troubleshooting

### Performance Profiling

#### Enable detailed logging

```yaml
logging:
  level: DEBUG
  search:
    level: DEBUG
    elasticsearch: DEBUG
    cache: DEBUG
    performance: DEBUG
```

#### Monitor query performance

```bash
# Get query performance statistics
curl -X GET "http://localhost:8000/api/v1/search/stats/performance"

# Get detailed metrics
curl -X GET "http://localhost:8000/metrics" | grep search_
```

#### Profile Elasticsearch queries

```bash
# Enable query profiling
curl -X PUT "http://localhost:9200/search_index/_settings" -H "Content-Type: application/json" -d '{
  "index.profiling.enabled": true
}'

# Get profiling data
curl -X GET "http://localhost:9200/search_index/_profile"
```

### Memory Analysis

#### Check memory usage

```bash
# Check process memory
ps aux | grep ai-service

# Check Docker memory
docker stats ai-service

# Check Elasticsearch memory
docker stats elasticsearch
```

#### Analyze memory leaks

```python
# Enable memory profiling
import tracemalloc

tracemalloc.start()

# Run search operations
# ... search code ...

# Get memory snapshot
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

### Network Analysis

#### Check network connectivity

```bash
# Test Elasticsearch connectivity
telnet localhost 9200

# Check network latency
ping localhost

# Monitor network traffic
tcpdump -i lo port 9200
```

#### Analyze network performance

```bash
# Check connection pool status
curl -X GET "http://localhost:8000/api/v1/search/health/connection_pool"

# Monitor connection metrics
curl -X GET "http://localhost:8000/metrics" | grep connection
```

## Monitoring and Alerting

### Health Checks

```bash
# Comprehensive health check
curl -X GET "http://localhost:8000/api/v1/search/health" | jq '.'

# Check specific components
curl -X GET "http://localhost:8000/api/v1/search/health/elasticsearch"
curl -X GET "http://localhost:8000/api/v1/search/health/cache"
curl -X GET "http://localhost:8000/api/v1/search/health/fallback"
```

### Metrics Collection

```bash
# Get all search metrics
curl -X GET "http://localhost:8000/metrics" | grep search_

# Get specific metrics
curl -X GET "http://localhost:8000/api/v1/search/stats/performance"
curl -X GET "http://localhost:8000/api/v1/search/stats/cache"
```

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: search_alerts
    rules:
      - alert: SearchServiceDown
        expr: up{job="search-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Search service is down"
      
      - alert: ElasticsearchConnectionFailed
        expr: search_elasticsearch_connection_errors_total > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Elasticsearch connection errors"
      
      - alert: SearchHighLatency
        expr: search_request_duration_seconds{quantile="0.95"} > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Search latency is high"
      
      - alert: SearchLowCacheHitRate
        expr: rate(search_cache_hits_total[5m]) / rate(search_requests_total[5m]) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Search cache hit rate is low"
```

## Recovery Procedures

### Service Recovery

```bash
# Restart search service
docker-compose restart ai-service

# Restart Elasticsearch
docker-compose restart elasticsearch

# Full service restart
docker-compose down && docker-compose up -d
```

### Data Recovery

```bash
# Recreate Elasticsearch indices
curl -X DELETE "http://localhost:9200/search_index"
curl -X PUT "http://localhost:9200/search_index" -H "Content-Type: application/json" -d @index_mapping.json

# Reindex data
python -m ai_service.search.reindex
```

### Configuration Recovery

```bash
# Restore from backup
cp config.yaml.backup config.yaml

# Validate configuration
python -m ai_service.config.validate

# Restart service
docker-compose restart ai-service
```

## Support and Escalation

### Log Collection

```bash
# Collect all relevant logs
mkdir -p /tmp/search-debug
cp /var/log/ai-service/search.log /tmp/search-debug/
cp /var/log/elasticsearch/elasticsearch.log /tmp/search-debug/
docker logs ai-service > /tmp/search-debug/ai-service.log
docker logs elasticsearch > /tmp/search-debug/elasticsearch.log

# Create debug package
tar -czf search-debug-$(date +%Y%m%d-%H%M%S).tar.gz /tmp/search-debug/
```

### Information to Include

When reporting issues, include:

1. **Error messages and logs**
2. **Configuration files** (sanitized)
3. **Health check results**
4. **Performance metrics**
5. **System information** (OS, Docker version, etc.)
6. **Steps to reproduce**

### Contact Information

- **Documentation**: [Search API Docs](https://docs.example.com/search-api)
- **Support Email**: support@example.com
- **Issue Tracker**: [GitHub Issues](https://github.com/example/ai-service/issues)
- **Status Page**: [Service Status](https://status.example.com)
