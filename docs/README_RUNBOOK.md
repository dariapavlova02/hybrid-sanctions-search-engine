# Hybrid Search Runbook Documentation

This directory contains comprehensive documentation and tools for managing the hybrid search system.

## Files Overview

### Core Documentation
- **`hybrid-search-runbook.md`** - Main runbook with step-by-step procedures for SRE and developers
- **`README_RUNBOOK.md`** - This file, overview of runbook documentation

### Supporting Scripts
- **`../scripts/quick_test_search.py`** - Python script for quick search functionality testing
- **`../scripts/emergency_procedures.sh`** - Bash script for emergency procedures and recovery
- **`../scripts/health_check.sh`** - Comprehensive health check script for monitoring

### Related Documentation
- **`../SEARCH_INTEGRATION_README.md`** - Technical documentation for search integration
- **`../ELASTICSEARCH_WATCHLIST_ADAPTER.md`** - Documentation for Elasticsearch adapter
- **`../SEARCH_DEPLOYMENT_PIPELINE.md`** - CI/CD pipeline documentation

## Quick Start

### 1. Local Development Setup
```bash
# Start monitoring stack with Elasticsearch
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Verify services are running
./scripts/health_check.sh

# Load sample data
python scripts/bulk_loader.py --input sample_entities.jsonl --entity-type person --upsert
```

### 2. Testing Search Functionality
```bash
# Quick functionality test
python scripts/quick_test_search.py --test all

# Test specific components
python scripts/quick_test_search.py --test ac
python scripts/quick_test_search.py --test vector
```

### 3. Emergency Procedures
```bash
# Check system health
./scripts/emergency_procedures.sh health

# Emergency restart
./scripts/emergency_procedures.sh restart

# Enable fallback mode
./scripts/emergency_procedures.sh fallback
```

## Monitoring and Alerting

### Key Metrics to Monitor
- **Search Latency**: P95 < 120ms, P99 < 200ms
- **Search Success Rate**: > 95%
- **Error Rate**: < 2%
- **Elasticsearch Health**: Green or Yellow status
- **Memory Usage**: < 80%
- **Disk Usage**: < 80%

### Alert Thresholds
- **Critical**: P95 latency > 200ms, Error rate > 5%, ES cluster red
- **Warning**: P95 latency > 120ms, Error rate > 2%, ES cluster yellow
- **Info**: Memory > 70%, Disk > 70%, Low hit rates

### Dashboard Access
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

## Troubleshooting Guide

### Common Issues

#### 1. Elasticsearch Connection Errors
```bash
# Check ES health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Restart ES container
docker restart search-elasticsearch

# Check ES logs
docker logs search-elasticsearch --tail 100
```

#### 2. Search Performance Issues
```bash
# Clear ES caches
curl -X POST "localhost:9200/_cache/clear"

# Force merge indices
curl -X POST "localhost:9200/watchlist_persons_current/_forcemerge?max_num_segments=1"

# Check slow queries
curl -X GET "localhost:9200/_nodes/stats/indices/search?pretty"
```

#### 3. Memory Issues
```bash
# Check memory usage
free -h

# Check Docker memory usage
docker stats

# Restart services
docker-compose -f monitoring/docker-compose.monitoring.yml restart
```

### Emergency Procedures

#### Complete System Restart
```bash
# Stop all services
docker-compose -f monitoring/docker-compose.monitoring.yml down

# Clean up (CAUTION: deletes data)
docker volume prune -f

# Restart services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

#### Fallback to Local Index
```bash
# Disable Elasticsearch
export ELASTICSEARCH_ENABLED=false

# Restart search service
docker restart search-service
```

#### Data Recovery
```bash
# Create backup
./scripts/emergency_procedures.sh backup

# Restore from backup
./scripts/emergency_procedures.sh restore
```

## Development Workflow

### 1. Local Development
```bash
# Start development environment
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Run tests
python scripts/quick_test_search.py --test all

# Load test data
python scripts/bulk_loader.py --input test_data.jsonl --entity-type person --upsert
```

### 2. Testing Changes
```bash
# Test AC search
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["test"]}}]}}, "size": 10}'

# Test Vector search
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{"knn": {"field": "name_vector", "query_vector": [0.1]*384, "k": 10, "similarity": "cosine"}, "size": 10}'
```

### 3. Performance Testing
```bash
# Run performance tests
python scripts/quick_test_search.py --test performance

# Check metrics
curl -X GET "localhost:9090/api/v1/query?query=rate(hybrid_search_requests_total[5m])"
```

## Configuration Reference

### Environment Variables
```bash
# Elasticsearch
export ES_URL="http://localhost:9200"
export ES_USER=""
export ES_PASS=""
export ES_VERIFY_SSL="false"
export ES_TIMEOUT="30"

# Search Configuration
export DISABLE_VECTOR_SEARCH="false"
export ELASTICSEARCH_FALLBACK="false"
export ELASTICSEARCH_ENABLED="true"

# Monitoring
export PROMETHEUS_ENABLED="true"
export PROMETHEUS_PORT="8080"
```

### Docker Compose Services
- **search-elasticsearch**: Elasticsearch cluster
- **search-prometheus**: Metrics collection
- **search-grafana**: Dashboards and visualization
- **search-alertmanager**: Alert management
- **search-service**: Search service application

### Ports
- **9200**: Elasticsearch
- **9090**: Prometheus
- **3000**: Grafana
- **9093**: Alertmanager
- **8080**: Search Service

## Best Practices

### 1. Monitoring
- Set up alerts for critical metrics
- Monitor search latency and success rates
- Track resource usage (CPU, memory, disk)
- Regular health checks

### 2. Maintenance
- Regular index optimization (force merge)
- Cache clearing when needed
- Backup and recovery procedures
- Log rotation and cleanup

### 3. Development
- Test changes locally before deployment
- Use proper error handling and logging
- Follow configuration management best practices
- Document changes and procedures

### 4. Security
- Use proper authentication for production
- Enable SSL/TLS for external access
- Regular security updates
- Access control and monitoring

## Support and Escalation

### Support Contacts
- **Development Team**: dev-team@company.com
- **SRE Team**: sre-team@company.com
- **Emergency**: +1-555-EMERGENCY

### Escalation Procedures
1. **Level 1**: Check logs and basic health
2. **Level 2**: Run diagnostic scripts
3. **Level 3**: Emergency procedures
4. **Level 4**: Contact support team

### Documentation Updates
- Update runbook when procedures change
- Test all procedures regularly
- Keep contact information current
- Document new issues and solutions

## Version History

- **v1.0** (2024-01-15): Initial runbook creation
  - Comprehensive health checks
  - Emergency procedures
  - Monitoring setup
  - Troubleshooting guide

---

For technical details, see the main runbook: [hybrid-search-runbook.md](hybrid-search-runbook.md)
