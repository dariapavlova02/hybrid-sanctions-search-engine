# Search System Stability Documentation

## Overview

This document covers the comprehensive search system stability features implemented for the AI Service hybrid search system. The system includes robust ElasticSearch integration, search trace validation, hybrid search testing, and comprehensive monitoring.

## Components

### 1. Enhanced ElasticSearch Client (`enhanced_elasticsearch_client.py`)

#### Key Features

- **Health Monitoring**: Comprehensive cluster health checks with caching
- **Circuit Breaker**: Automatic failover for failed connections
- **Retry Logic**: Exponential backoff with jitter for failed operations
- **Connection Pooling**: Efficient connection management with cleanup
- **Performance Monitoring**: Detailed timing and resource usage tracking

#### Usage Example

```python
from src.ai_service.layers.search.enhanced_elasticsearch_client import EnhancedElasticsearchClient

# Initialize client
client = EnhancedElasticsearchClient()

# Perform health check
health = await client.enhanced_health_check()
print(f"Cluster status: {health['overall_status']}")

# Wait for cluster to become healthy
is_healthy = await client.wait_for_healthy(timeout=60.0)

# Check connection status
status = client.get_connection_status()
print(f"Active connections: {status['active_clients']}")
```

#### Configuration

```python
from src.ai_service.layers.search.enhanced_elasticsearch_client import RetryPolicy

# Custom retry policy
retry_policy = RetryPolicy(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

client = EnhancedElasticsearchClient(retry_policy=retry_policy)
```

#### Health Status Levels

- **GREEN**: All primary and replica shards are active
- **YELLOW**: All primary shards are active, but some replicas are not
- **RED**: Some primary shards are not active
- **UNREACHABLE**: Cannot connect to ElasticSearch cluster

### 2. Search Trace Validator (`search_trace_validator.py`)

#### Key Features

- **Deterministic Ordering**: Consistent hash generation for trace comparison
- **Comprehensive Validation**: Step ordering, timing, data integrity checks
- **Performance Analysis**: Timing patterns and bottleneck identification
- **Coverage Analysis**: Validation of search strategy completeness
- **Configurable Thresholds**: Customizable performance and error limits

#### Usage Example

```python
from src.ai_service.layers.search.search_trace_validator import SearchTraceValidator
from src.ai_service.contracts.trace_models import SearchTrace

# Initialize validator
validator = SearchTraceValidator(strict_mode=True)

# Create search trace (typically populated during search)
trace = SearchTrace(enabled=True)
trace.notes = [
    "AC search initiated for 'John Doe'",
    "AC search completed with 5 results in 25ms",
    "Vector search initiated for 'John Doe'",
    "Vector search completed with 7 results in 150ms",
    "Hybrid merge completed with 8 results in 5ms"
]

# Validate trace
report = validator.validate_trace(trace)

print(f"Trace valid: {report.is_valid}")
print(f"Issues found: {len(report.issues)}")
print(f"Coverage: {report.coverage_analysis['coverage_percentage']}%")
```

#### Validation Categories

1. **Step Ordering**: Logical sequence of search operations
2. **Timing Consistency**: Reasonable duration and timing relationships
3. **Data Integrity**: Consistent result counts and data flow
4. **Coverage Requirements**: Minimum required search components
5. **Performance Thresholds**: Latency and resource usage limits

#### Expected Search Patterns

```python
expected_patterns = {
    "ac_only": [TraceStepType.AC_SEARCH],
    "vector_only": [TraceStepType.VECTOR_SEARCH],
    "hybrid": [
        TraceStepType.AC_SEARCH,
        TraceStepType.VECTOR_SEARCH,
        TraceStepType.HYBRID_MERGE
    ],
    "fallback": [
        TraceStepType.AC_SEARCH,
        TraceStepType.FALLBACK_TRIGGERED,
        TraceStepType.VECTOR_SEARCH
    ]
}
```

### 3. Hybrid Search Integration Tests (`test_hybrid_search_integration.py`)

#### Test Categories

1. **ElasticSearch Health and Connectivity**
   - Comprehensive health checks
   - Circuit breaker functionality
   - Retry logic validation
   - Connection pool management

2. **Hybrid Search Integration**
   - AC search execution
   - Vector search execution
   - Hybrid search with fallback
   - Result consistency across calls

3. **Search Trace Validation**
   - Trace validator initialization
   - AC-only trace validation
   - Hybrid trace validation
   - Error detection and reporting
   - Deterministic hash consistency

4. **Search System Resilience**
   - Connection failure handling
   - Timeout handling
   - Large result set handling
   - Performance under load

5. **End-to-End Workflow**
   - Complete search workflow
   - Trace snapshot creation
   - Integration validation

#### Performance Tests

```python
@pytest.mark.performance
class TestSearchPerformance:
    async def test_concurrent_search_performance(self):
        """Test performance under concurrent load."""
        # 10 concurrent searches
        queries = [SearchQuery(text=f"test_{i}") for i in range(10)]

        # Execute concurrently
        results = await asyncio.gather(*[
            search_service.search(query, SearchTrace(enabled=True))
            for query in queries
        ])

        # Validate performance
        assert total_time < 30.0  # All searches complete in 30s
        assert successful_count >= 5  # At least 50% success rate
```

### 4. Search System Monitor (`search_monitoring.py`)

#### Key Features

- **Real-time Metrics**: Performance, error rates, resource usage
- **Alerting System**: Configurable thresholds and severity levels
- **Performance Windows**: Sliding window statistics (P50, P95, P99)
- **Comprehensive Logging**: Structured logs with trace correlation
- **Prometheus Export**: Metrics export for external monitoring

#### Usage Example

```python
from src.ai_service.layers.search.search_monitoring import get_search_monitor, monitor_search_operation

# Get global monitor
monitor = get_search_monitor()

# Manual metric recording
monitor.record_search_operation(
    query_text="John Doe",
    strategy="hybrid",
    latency_ms=150.0,
    result_count=8,
    success=True,
    search_trace=trace
)

# Decorator for automatic monitoring
@monitor_search_operation(strategy="hybrid")
async def search_with_monitoring(query: SearchQuery):
    return await hybrid_search_service.search(query)

# Get system health
health = monitor.get_system_health()
print(f"System status: {health['status']}")
```

#### Monitoring Metrics

##### Performance Metrics
- **search_latency_ms**: Search operation latency
- **elasticsearch_response_time_ms**: ES cluster response times
- **trace_validation_time_ms**: Trace validation duration
- **search_result_count**: Number of results returned
- **concurrent_searches**: Active concurrent search operations

##### Error Metrics
- **search_requests_total**: Total search requests
- **search_requests_failed**: Failed search requests
- **elasticsearch_errors_by_type**: ES errors by category
- **trace_validation_failures**: Trace validation failures

##### Health Metrics
- **memory_usage_mb**: Memory consumption
- **error_rate_percent**: Overall error rate
- **trace_validation_error_rate_percent**: Trace validation error rate

#### Alert Configuration

```python
from src.ai_service.layers.search.search_monitoring import configure_search_monitoring

def alert_callback(alert):
    """Custom alert handler."""
    print(f"ALERT: {alert.severity.value} - {alert.message}")
    # Send to external monitoring system

# Configure monitoring
monitor = configure_search_monitoring(
    enable_alerts=True,
    alert_callback=alert_callback,
    thresholds={
        "search_latency_p95_ms": 200.0,
        "error_rate_percent": 5.0,
        "memory_usage_mb": 500.0
    }
)
```

#### Performance Thresholds

```python
default_thresholds = {
    "search_latency_p95_ms": 200.0,      # P95 search latency
    "search_latency_p99_ms": 500.0,      # P99 search latency
    "elasticsearch_health_check_ms": 1000.0,  # ES health check timeout
    "error_rate_percent": 5.0,           # Maximum error rate
    "trace_validation_error_rate_percent": 10.0,  # Trace validation errors
    "concurrent_searches": 50,           # Maximum concurrent searches
    "memory_usage_mb": 500.0            # Memory usage threshold
}
```

## Integration with CI/CD

### Quality Gates Integration

The search stability components are integrated into the CI/CD pipeline through the `quality-gates.yml` workflow:

```yaml
search_integration:
  name: Search Integration Tests
  steps:
    - name: Run SearchTrace acceptance tests
      run: |
        pytest -q \
          tests/integration/test_search_trace_snapshots.py \
          tests/unit/test_search_trace_contracts.py \
          -m "search_trace"

    - name: Run hybrid search integration tests
      run: |
        pytest -q \
          tests/integration/test_hybrid_search_integration.py \
          --maxfail=3
```

### Monitoring Integration

The monitoring system integrates with Prometheus and Grafana:

```yaml
# In deployment.yml
- name: Setup monitoring configuration
  run: |
    # Export Prometheus metrics
    curl -f http://localhost:8000/metrics > artifacts/search-metrics.txt

    # Validate monitoring setup
    python -c "
    from src.ai_service.layers.search.search_monitoring import get_search_monitor
    monitor = get_search_monitor()
    health = monitor.get_system_health()
    assert health['status'] in ['healthy', 'degraded']
    "
```

## Best Practices

### 1. Search Operation Monitoring

Always wrap search operations with monitoring:

```python
from src.ai_service.layers.search.search_monitoring import monitor_search_operation

@monitor_search_operation(strategy="hybrid")
async def perform_search(query: SearchQuery, trace: SearchTrace) -> List[SearchResult]:
    """Monitored search operation."""
    return await search_service.search(query, trace)
```

### 2. Health Check Integration

Implement health checks in service initialization:

```python
async def initialize_search_service():
    client = EnhancedElasticsearchClient()

    # Wait for healthy cluster before proceeding
    if not await client.wait_for_healthy(timeout=60.0):
        raise RuntimeError("ElasticSearch cluster not healthy")

    return HybridSearchService(client)
```

### 3. Trace Validation

Always validate traces in production:

```python
async def search_with_validation(query: SearchQuery) -> SearchResult:
    trace = SearchTrace(enabled=True)
    results = await search_service.search(query, trace)

    # Validate trace
    validator = SearchTraceValidator()
    report = validator.validate_trace(trace)

    if not report.is_valid:
        logger.warning(f"Invalid search trace: {len(report.issues)} issues")
        # Log issues for debugging
        for issue in report.get_issues_by_severity(ValidationSeverity.ERROR):
            logger.error(f"Trace error: {issue.message}")

    return results
```

### 4. Circuit Breaker Handling

Handle circuit breaker states gracefully:

```python
try:
    health = await client.enhanced_health_check()
    if health["circuit_breakers_active"] > 0:
        # Some hosts are in circuit breaker mode
        logger.warning("Some ElasticSearch hosts are unavailable")
        # Implement fallback strategy

except Exception as e:
    # All hosts may be unavailable
    logger.error(f"ElasticSearch completely unavailable: {e}")
    # Implement complete fallback (cache, different service, etc.)
```

## Troubleshooting

### Common Issues

#### 1. ElasticSearch Connection Issues

**Symptoms**: Circuit breakers activated, connection timeouts

**Diagnosis**:
```python
client = EnhancedElasticsearchClient()
status = client.get_connection_status()
print(f"Circuit breakers: {status['circuit_breakers']}")
print(f"Connection failures: {status['connection_failures']}")
```

**Solutions**:
- Check ElasticSearch cluster health
- Verify network connectivity
- Adjust timeout configurations
- Review circuit breaker thresholds

#### 2. Search Trace Validation Failures

**Symptoms**: High trace validation error rates

**Diagnosis**:
```python
validator = SearchTraceValidator()
report = validator.validate_trace(trace)
for issue in report.issues:
    print(f"{issue.severity.value}: {issue.message}")
```

**Solutions**:
- Review search strategy implementation
- Check trace note formatting
- Validate timing consistency
- Ensure proper step ordering

#### 3. High Search Latency

**Symptoms**: P95/P99 latency alerts

**Diagnosis**:
```python
monitor = get_search_monitor()
health = monitor.get_system_health()
perf_stats = health["performance"]["search_latency_ms"]
print(f"P95 latency: {perf_stats['p95']}ms")
```

**Solutions**:
- Optimize ElasticSearch queries
- Review index configuration
- Scale ElasticSearch cluster
- Implement query caching
- Optimize vector search parameters

#### 4. Memory Usage Issues

**Symptoms**: High memory usage alerts

**Diagnosis**:
```python
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Memory usage: {memory_mb:.1f}MB")
```

**Solutions**:
- Review connection pool sizes
- Optimize result set handling
- Implement result pagination
- Monitor for memory leaks

## Performance Tuning

### ElasticSearch Client Tuning

```python
# Optimize connection settings
client = EnhancedElasticsearchClient()
client.es_config.timeout = 10.0  # Reduce timeout for faster failures
client.retry_policy.max_attempts = 3  # Reduce retry attempts
client.retry_policy.base_delay = 0.5  # Faster retry intervals
```

### Search Trace Optimization

```python
# Use trace selectively in production
trace_enabled = config.get("enable_search_trace", False)
trace = SearchTrace(enabled=trace_enabled) if trace_enabled else None
```

### Monitoring Configuration

```python
# Optimize monitoring for production
monitor = configure_search_monitoring(
    enable_alerts=True,
    thresholds={
        "search_latency_p95_ms": 100.0,  # Stricter latency requirements
        "error_rate_percent": 2.0,       # Lower error tolerance
    }
)

# Reduce metric retention for memory efficiency
monitor.performance_windows["search_latency_ms"].window_size = 50
```

## Metrics and Alerting

### Prometheus Metrics Export

The search monitoring system exports metrics in Prometheus format:

```prometheus
# Search operation metrics
search_requests_total{strategy="hybrid",success="true"} 1250
search_requests_failed{strategy="hybrid",error_type="timeout"} 15
search_latency_ms_p95 125.5
search_latency_ms_p99 245.2

# ElasticSearch metrics
elasticsearch_requests_total{operation="search",host="localhost:9200",success="true"} 890
elasticsearch_response_time_ms_avg 45.2

# Trace validation metrics
trace_validation_failures{strategy="hybrid"} 3
trace_coverage_percentage_avg 85.5
```

### Grafana Dashboard

Key dashboard panels:

1. **Search Performance**
   - Search latency percentiles (P50, P95, P99)
   - Request rate and success rate
   - Error rate by type

2. **ElasticSearch Health**
   - Cluster status and node count
   - Response times and error rates
   - Circuit breaker status

3. **Trace Validation**
   - Validation success rate
   - Coverage percentage
   - Issue distribution by severity

4. **System Resources**
   - Memory usage and trends
   - Concurrent search operations
   - Alert status and history

### Alert Rules

```yaml
# Prometheus alert rules
groups:
- name: search_system
  rules:
  - alert: HighSearchLatency
    expr: search_latency_ms_p95 > 200
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High search latency detected"

  - alert: SearchErrorRate
    expr: (search_requests_failed / search_requests_total) * 100 > 5
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High search error rate detected"
```

---

This documentation provides comprehensive coverage of the search system stability features. For implementation details, refer to the individual component documentation and test files.