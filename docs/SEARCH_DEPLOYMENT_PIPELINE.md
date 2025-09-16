# Search Integration Deployment Pipeline

GitHub Actions пайплайн для автоматического развертывания поисковой интеграции с Elasticsearch.

## 🎯 Цель

Автоматизированный, безопасный и идемпотентный процесс развертывания:
- **Сборка артефактов** и прогон unit тестов
- **Старт временного ES** (services)
- **Применение темплейтов** и создание индексов с алиасами `_current`
- **Bulk загрузка корпуса** из файлов артефакта
- **Rollover алиаса** `_current` → новый индекс
- **Warmup kNN и AC** запросами (top-10)
- **Smoke-тесты** на A/B: старый vs новый индекс
- **Артефакты**: отчёт метрик, p95 latency

## 🏗️ Архитектура пайплайна

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions                          │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  Build & Test   │  │      Integration Tests         │   │
│  │  - Unit tests   │  │      - Docker ES               │   │
│  │  - Artifacts    │  │      - AC/Vector tests         │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Deployment Jobs                             │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   Staging       │  │      Production                 │   │
│  │   - Deploy      │  │      - Deploy                   │   │
│  │   - Smoke tests │  │      - Smoke tests              │   │
│  │   - Report      │  │      - Report                   │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Rollback (if needed)                        │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   Alias Swap    │  │      Cleanup                    │   │
│  │   - Back to old │  │      - Remove new indices       │   │
│  │   - Verify      │  │      - Verify rollback          │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Триггеры

### Автоматические триггеры

```yaml
on:
  push:
    branches: [main, develop]
    paths:
      - 'src/ai_service/layers/search/**'
      - 'src/ai_service/layers/embeddings/indexing/elasticsearch_watchlist_adapter.py'
      - 'templates/elasticsearch/**'
      - 'scripts/elasticsearch_setup_and_warmup.py'
      - 'scripts/bulk_loader.py'
  pull_request:
    branches: [main, develop]
    paths: [same as above]
```

### Ручной триггер

```yaml
workflow_dispatch:
  inputs:
    environment:
      description: 'Deployment environment'
      required: true
      default: 'staging'
      type: choice
      options: [staging, production]
    skip_tests:
      description: 'Skip tests'
      required: false
      default: false
      type: boolean
    force_deploy:
      description: 'Force deployment even if tests fail'
      required: false
      default: false
      type: boolean
```

## 🔧 Конфигурация

### Переменные окружения

```yaml
env:
  PYTHON_VERSION: '3.10'
  ELASTICSEARCH_VERSION: '8.11.0'
  ES_URL: 'http://localhost:9200'
  ES_AUTH: ''
  ES_VERIFY_SSL: 'false'
```

### Secrets

```yaml
secrets:
  STAGING_ES_URL: "https://staging-es.example.com:9200"
  STAGING_ES_AUTH: "username:password"
  STAGING_ES_VERIFY_SSL: "true"
  
  PRODUCTION_ES_URL: "https://production-es.example.com:9200"
  PRODUCTION_ES_AUTH: "username:password"
  PRODUCTION_ES_VERIFY_SSL: "true"
```

## 🚀 Этапы пайплайна

### 1. Build and Test

```yaml
build-and-test:
  runs-on: ubuntu-latest
  steps:
    - Checkout code
    - Set up Python
    - Install dependencies
    - Build artifacts
    - Run unit tests
    - Upload artifacts
```

**Артефакты:**
- `search-artifacts/` - исходный код, темплейты, скрипты
- `test-results/` - результаты unit тестов
- `integration-test-results/` - результаты integration тестов

### 2. Integration Tests

```yaml
integration-tests:
  runs-on: ubuntu-latest
  services:
    elasticsearch:
      image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
      ports: [9200:9200]
  steps:
    - Wait for Elasticsearch
    - Run integration tests
    - Upload test results
```

### 3. Deploy to Staging

```yaml
deploy-staging:
  needs: [build-and-test, integration-tests]
  if: github.ref == 'refs/heads/develop'
  environment: staging
  steps:
    - Download artifacts
    - Deploy to staging
    - Run smoke tests
```

### 4. Deploy to Production

```yaml
deploy-production:
  needs: [build-and-test, integration-tests, deploy-staging]
  if: github.ref == 'refs/heads/main'
  environment: production
  steps:
    - Download artifacts
    - Deploy to production
    - Run smoke tests
    - Generate deployment report
```

### 5. Rollback (if needed)

```yaml
rollback:
  if: failure()
  environment: production-or-staging
  steps:
    - Rollback deployment
    - Verify rollback
    - Cleanup
```

## 📊 Скрипты развертывания

### `deploy_search_integration.py`

Основной скрипт развертывания:

```bash
python scripts/deploy_search_integration.py \
  --environment production \
  --artifacts-path artifacts/ \
  --es-url "$ES_URL" \
  --es-auth "$ES_AUTH" \
  --es-verify-ssl true \
  --dry-run false
```

**Функции:**
- Health check Elasticsearch
- Создание темплейтов
- Создание новых индексов
- Bulk загрузка данных
- Rollover алиасов
- Warmup запросы
- Smoke тесты

### `rollback_search_integration.py`

Скрипт отката:

```bash
python scripts/rollback_search_integration.py \
  --environment production \
  --es-url "$ES_URL" \
  --es-auth "$ES_AUTH" \
  --es-verify-ssl true
```

**Функции:**
- Обнаружение текущего состояния
- Rollback алиасов к старым индексам
- Очистка новых индексов
- Проверка отката
- Smoke тесты

### `smoke_test_search.py`

Smoke тесты:

```bash
python scripts/smoke_test_search.py \
  --environment production \
  --es-url "$ES_URL" \
  --es-auth "$ES_AUTH" \
  --output smoke-test-results.json
```

**Тесты:**
- Elasticsearch health
- Существование индексов
- AC поиск
- Vector поиск
- Производительность
- Обработка ошибок

### `generate_deployment_report.py`

Генерация отчета:

```bash
python scripts/generate_deployment_report.py \
  --environment production \
  --es-url "$ES_URL" \
  --es-auth "$ES_AUTH" \
  --output deployment-report.json
```

**Метрики:**
- Elasticsearch cluster info
- Информация об индексах
- Данные производительности
- Health метрики
- Сводка развертывания

## 🔄 Алгоритм развертывания

### 1. Подготовка

```python
# Health check
if not await health_check():
    raise Exception("Elasticsearch not available")

# Создание темплейтов
await create_templates(artifacts_path)
```

### 2. Создание индексов

```python
# Генерация новых имен индексов
timestamp = int(time.time())
persons_index = f"watchlist_persons_v{timestamp}"
orgs_index = f"watchlist_orgs_v{timestamp}"

# Создание индексов
await create_indices()
```

### 3. Загрузка данных

```python
# Bulk загрузка
await load_data(artifacts_path)

# Проверка загрузки
await verify_data_loaded()
```

### 4. Rollover алиасов

```python
# Получение старых алиасов
old_aliases = await get_current_aliases()

# Rollover
await rollover_aliases()

# Проверка rollover
await verify_rollover()
```

### 5. Warmup и тесты

```python
# Warmup запросы
await warmup_queries()

# Smoke тесты
await smoke_tests()

# Генерация отчета
await generate_report()
```

## 🛡️ Безопасность и откат

### Idempotent операции

- **Темплейты**: перезаписываются при каждом развертывании
- **Индексы**: создаются с уникальными именами
- **Алиасы**: атомарно переключаются
- **Данные**: bulk upsert (idempotent)

### Безопасный откат

```python
# Сохранение старых алиасов
old_aliases = {
    "persons": "watchlist_persons_v1234567890",
    "orgs": "watchlist_orgs_v1234567890"
}

# Rollback
await rollback_aliases(old_aliases)

# Очистка новых индексов
await cleanup_new_indices()

# Проверка отката
await verify_rollback()
```

### Проверки безопасности

- **Health check** перед развертыванием
- **Smoke тесты** после развертывания
- **Автоматический откат** при ошибках
- **Верификация** каждого шага

## 📈 Метрики и мониторинг

### Метрики развертывания

```json
{
  "deployment_id": "search-1234567890",
  "environment": "production",
  "timestamp": 1234567890.0,
  "deployment_time_seconds": 45.2,
  "metrics": {
    "templates_created": 3,
    "indices_created": 2,
    "documents_loaded": 15000,
    "warmup_queries": 5,
    "errors": []
  },
  "performance": {
    "p95_duration_ms": 75.5,
    "avg_duration_ms": 45.2,
    "max_duration_ms": 120.3
  }
}
```

### Health метрики

```json
{
  "health": {
    "cluster_status": "green",
    "indices_healthy": 5,
    "indices_yellow": 0,
    "indices_red": 0,
    "total_indices": 5
  }
}
```

### Performance метрики

```json
{
  "performance": {
    "p50_duration_ms": 25.5,
    "p95_duration_ms": 75.5,
    "p99_duration_ms": 120.3,
    "avg_duration_ms": 45.2,
    "max_duration_ms": 150.7
  }
}
```

## 🚀 Использование

### Автоматическое развертывание

```bash
# Push в develop → staging
git push origin develop

# Push в main → production
git push origin main
```

### Ручное развертывание

```bash
# Через GitHub Actions UI
# Actions → Search Integration Deployment → Run workflow

# Или через GitHub CLI
gh workflow run search-deployment.yml \
  --field environment=staging \
  --field skip_tests=false
```

### Локальное тестирование

```bash
# Dry run
python scripts/deploy_search_integration.py \
  --environment staging \
  --artifacts-path artifacts/ \
  --es-url "http://localhost:9200" \
  --dry-run true

# Smoke тесты
python scripts/smoke_test_search.py \
  --environment staging \
  --es-url "http://localhost:9200" \
  --output smoke-results.json
```

## 🔧 Troubleshooting

### Проблемы с Elasticsearch

```bash
# Проверка health
curl -f http://localhost:9200/_cluster/health

# Проверка индексов
curl -f http://localhost:9200/_cat/indices?v

# Проверка алиасов
curl -f http://localhost:9200/_aliases
```

### Проблемы с развертыванием

```bash
# Логи GitHub Actions
gh run view --log

# Локальная отладка
python scripts/deploy_search_integration.py --dry-run true

# Проверка smoke тестов
python scripts/smoke_test_search.py --es-url "http://localhost:9200"
```

### Откат

```bash
# Автоматический откат (при ошибке)
# GitHub Actions автоматически запустит rollback job

# Ручной откат
python scripts/rollback_search_integration.py \
  --environment production \
  --es-url "$ES_URL" \
  --es-auth "$ES_AUTH"
```

## 📋 Чек-лист готовности

- [x] GitHub Actions workflow
- [x] Скрипт развертывания
- [x] Скрипт отката
- [x] Smoke тесты
- [x] Генерация отчетов
- [x] Idempotent операции
- [x] Безопасный откат
- [x] Метрики и мониторинг
- [x] Документация

## 🎉 Результат

Создан полнофункциональный пайплайн развертывания, который:

1. **Автоматизирует** весь процесс развертывания
2. **Безопасен** с возможностью отката
3. **Idempotent** - можно запускать многократно
4. **Мониторит** производительность и здоровье
5. **Генерирует** подробные отчеты
6. **Готов к продакшену** с проверками безопасности

Пайплайн готов к использованию! 🚀
