# Search Integration Monitoring

Комплексная система мониторинга для поисковой интеграции с Prometheus, Grafana и Alertmanager.

## 🎯 Цель

Создать полнофункциональную систему мониторинга, которая отслеживает:
- **Производительность поиска**: latency, throughput, hit rates
- **Качество поиска**: success rate, error rate, cache hit rate
- **Состояние Elasticsearch**: cluster health, connection errors
- **Ресурсы системы**: CPU, memory, active connections

## 📊 Метрики

### Основные метрики

```prometheus
# Запросы поиска
hybrid_search_requests_total{mode="ac|knn|hybrid"}

# Latency поиска (histogram)
hybrid_search_latency_ms_bucket{mode="ac|knn|hybrid"}

# AC hits по типам
ac_hits_total{type="exact|phrase|ngram"}
ac_weak_hits_total

# KNN и fusion hits
knn_hits_total
fusion_consensus_total

# Ошибки Elasticsearch
es_errors_total{type="timeout|conn|mapping|query|index"}

# Дополнительные метрики
search_success_rate
active_search_connections
search_cache_hit_rate
```

### Recording Rules

```prometheus
# Success rate over time
search_success_rate_5m = rate(hybrid_search_requests_total[5m]) / (rate(hybrid_search_requests_total[5m]) + rate(es_errors_total[5m]))

# Error rate over time
search_error_rate_5m = rate(es_errors_total[5m]) / rate(hybrid_search_requests_total[5m])

# Latency percentiles
search_latency_p50_5m = histogram_quantile(0.50, rate(hybrid_search_latency_ms_bucket[5m]))
search_latency_p95_5m = histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m]))
search_latency_p99_5m = histogram_quantile(0.99, rate(hybrid_search_latency_ms_bucket[5m]))
```

## 🚀 Быстрый старт

### 1. Запуск мониторинга

```bash
# Перейти в директорию мониторинга
cd monitoring/

# Запустить все сервисы
docker-compose -f docker-compose.monitoring.yml up -d

# Проверить статус
docker-compose -f docker-compose.monitoring.yml ps
```

### 2. Доступ к сервисам

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Alertmanager**: http://localhost:9093
- **Node Exporter**: http://localhost:9100
- **cAdvisor**: http://localhost:8080

### 3. Импорт дашборда

1. Открыть Grafana: http://localhost:3000
2. Перейти в **Dashboards** → **Import**
3. Загрузить файл `grafana_dashboard.json`
4. Выбрать datasource **Prometheus**

## 📈 Дашборд Grafana

### Панели дашборда

1. **Search Requests Rate** - скорость запросов по режимам
2. **Search Success Rate** - процент успешных запросов
3. **Search Latency P95** - 95-й перцентиль задержки
4. **Search Latency P99** - 99-й перцентиль задержки
5. **Search Latency by Mode** - задержка по режимам (P50/P95/P99)
6. **AC Hits by Type** - hits AC поиска по типам
7. **KNN and Fusion Hits** - hits KNN и fusion consensus
8. **Elasticsearch Errors** - ошибки ES по типам
9. **Error Rate** - процент ошибок
10. **Top Slow Queries** - топ медленных запросов
11. **Search Cache Hit Rate** - процент попаданий в кеш
12. **Active Search Connections** - активные соединения

### Настройка дашборда

```json
{
  "title": "Search Integration Dashboard",
  "tags": ["search", "elasticsearch", "prometheus"],
  "refresh": "5s",
  "time": {
    "from": "now-1h",
    "to": "now"
  }
}
```

## 🚨 Алерты

### Критические алерты

```yaml
# Высокая задержка P95
- alert: SearchLatencyHigh
  expr: histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m])) > 120
  for: 5m
  labels:
    severity: warning

# Критически высокая задержка P95
- alert: SearchLatencyCritical
  expr: histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m])) > 200
  for: 2m
  labels:
    severity: critical

# Высокий процент ошибок
- alert: SearchErrorRateHigh
  expr: rate(es_errors_total[5m]) / rate(hybrid_search_requests_total[5m]) * 100 > 2
  for: 3m
  labels:
    severity: warning

# Критически высокий процент ошибок
- alert: SearchErrorRateCritical
  expr: rate(es_errors_total[5m]) / rate(hybrid_search_requests_total[5m]) * 100 > 5
  for: 1m
  labels:
    severity: critical
```

### Все алерты

- **SearchLatencyHigh** - P95 > 120ms (5min)
- **SearchLatencyCritical** - P95 > 200ms (2min)
- **SearchErrorRateHigh** - Error rate > 2% (3min)
- **SearchErrorRateCritical** - Error rate > 5% (1min)
- **SearchSuccessRateLow** - Success rate < 95% (5min)
- **SearchSuccessRateCritical** - Success rate < 90% (2min)
- **ElasticsearchConnectionErrors** - ES connection errors
- **ElasticsearchTimeoutErrors** - ES timeout errors
- **SearchThroughputLow** - Throughput < 0.1 req/sec (10min)
- **SearchThroughputZero** - No requests (5min)
- **SearchCacheHitRateLow** - Cache hit rate < 70% (10min)
- **ACHitRateLow** - AC hit rate < 0.01 hits/sec (15min)
- **ACWeakHitsHigh** - AC weak hits > 50% (10min)
- **KNNHitRateLow** - KNN hit rate < 0.01 hits/sec (15min)
- **FusionConsensusLow** - Fusion consensus < 0.001/sec (20min)
- **ActiveConnectionsHigh** - Active connections > 100 (5min)
- **ActiveConnectionsCritical** - Active connections > 200 (2min)
- **ElasticsearchClusterYellow** - ES cluster yellow (5min)
- **ElasticsearchClusterRed** - ES cluster red (1min)
- **SearchServiceDown** - Service down (1min)
- **SearchServiceRestarted** - Service restarted
- **SearchMemoryUsageHigh** - Memory > 1GB (5min)
- **SearchMemoryUsageCritical** - Memory > 2GB (2min)
- **SearchCPUUsageHigh** - CPU > 80% (5min)
- **SearchCPUUsageCritical** - CPU > 95% (2min)

## 🔧 Конфигурация

### Prometheus (prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "prometheus_alerts.yml"

scrape_configs:
  - job_name: 'search-service'
    static_configs:
      - targets: ['search-service:8080']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

### Alertmanager (alertmanager.yml)

```yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@example.com'

route:
  group_by: ['alertname', 'service', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 5s
      group_interval: 5s
      repeat_interval: 30m
```

## 📱 Интеграция с поисковым сервисом

### 1. Установка зависимостей

```bash
pip install prometheus-client fastapi uvicorn
```

### 2. Инициализация экспортера

```python
from ai_service.monitoring.prometheus_exporter import get_exporter

# Получить глобальный экспортер
exporter = get_exporter()

# Записать метрики
exporter.record_search_request(SearchMode.HYBRID, 45.2, True)
exporter.record_ac_hits({ACHitType.EXACT: 5}, weak_hits=1)
exporter.record_knn_hits(8)
exporter.record_fusion_consensus(3)
exporter.record_es_error(ESErrorType.TIMEOUT)
```

### 3. FastAPI интеграция

```python
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return get_exporter().get_metrics()
```

### 4. Запуск примера

```bash
# Запустить пример
python examples/prometheus_integration_example.py

# Тестировать метрики
curl http://localhost:8000/metrics
curl "http://localhost:8000/search?query=test&mode=hybrid"
```

## 🐳 Docker Compose

### Полная конфигурация

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.45.0
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus_alerts.yml:/etc/prometheus/prometheus_alerts.yml:ro

  grafana:
    image: grafana/grafana:10.0.0
    ports: ["3000:3000"]
    volumes:
      - ./grafana_dashboard.json:/etc/grafana/provisioning/dashboards/search-dashboard.json:ro

  alertmanager:
    image: prom/alertmanager:v0.25.0
    ports: ["9093:9093"]
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
```

## 📊 Примеры запросов

### Prometheus запросы

```promql
# Запросы поиска по режимам
rate(hybrid_search_requests_total[5m])

# Latency P95
histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m]))

# Success rate
rate(hybrid_search_requests_total[5m]) / (rate(hybrid_search_requests_total[5m]) + rate(es_errors_total[5m]))

# Error rate
rate(es_errors_total[5m]) / rate(hybrid_search_requests_total[5m]) * 100

# AC hits по типам
rate(ac_hits_total[5m])

# KNN hits
rate(knn_hits_total[5m])

# Fusion consensus
rate(fusion_consensus_total[5m])

# ES errors по типам
rate(es_errors_total[5m])
```

### Grafana запросы

```promql
# Search latency by mode
histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m]))

# AC hits by type
rate(ac_hits_total[5m])

# Error rate
rate(es_errors_total[5m]) / rate(hybrid_search_requests_total[5m]) * 100

# Top slow queries
topk(10, histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m])))
```

## 🔍 Troubleshooting

### Проблемы с метриками

```bash
# Проверить доступность метрик
curl http://localhost:8080/metrics

# Проверить Prometheus targets
curl http://localhost:9090/api/v1/targets

# Проверить алерты
curl http://localhost:9090/api/v1/alerts
```

### Проблемы с Grafana

```bash
# Проверить datasources
curl http://localhost:3000/api/datasources

# Проверить дашборды
curl http://localhost:3000/api/dashboards
```

### Проблемы с Alertmanager

```bash
# Проверить конфигурацию
curl http://localhost:9093/api/v1/status

# Проверить алерты
curl http://localhost:9093/api/v1/alerts
```

## 📋 Чек-лист готовности

- [x] Prometheus экспортер метрик
- [x] Grafana дашборд с панелями
- [x] Alertmanager правила алертов
- [x] Docker Compose конфигурация
- [x] Примеры интеграции
- [x] Документация
- [x] Recording rules
- [x] Inhibit rules
- [x] Webhook интеграция
- [x] Email уведомления

## 🎉 Результат

Создана полнофункциональная система мониторинга, которая:

1. **Отслеживает** все ключевые метрики поиска
2. **Визуализирует** данные в удобном дашборде
3. **Алертит** о проблемах в реальном времени
4. **Интегрируется** с поисковым сервисом
5. **Масштабируется** для продакшена

Система мониторинга готова к использованию! 🚀
