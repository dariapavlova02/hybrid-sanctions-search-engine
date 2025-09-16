# Search Layer

Гибридный слой поиска для 9-слойной архитектуры AI Service, использующий Elasticsearch как бэкенд для двух режимов поиска:

1. **AC/точный поиск**: точные/почти-точные совпадения по нормализованным ФИО, алиасам и юридическим наименованиям
2. **Vector/векторный поиск**: kNN по dense_vector

## Архитектура

### Основные компоненты

- **HybridSearchService**: Главный сервис, реализующий стратегию эскалации
- **ElasticsearchACAdapter**: Адаптер для точного поиска через Elasticsearch
- **ElasticsearchVectorAdapter**: Адаптер для векторного поиска через Elasticsearch
- **SearchOpts**: Конфигурация параметров поиска
- **Candidate**: Модель результата поиска

### Стратегия эскалации

1. **Первый этап**: AC поиск для точных/почти-точных совпадений
2. **Эскалация**: Если AC не дал результата или дал слабый score → запуск векторного поиска
3. **Fallback**: Если Elasticsearch недоступен → использование локальных индексов

## Использование

### Базовое использование

```python
from ai_service.layers.search import HybridSearchService, SearchOpts
from ai_service.contracts.base_contracts import NormalizationResult

# Инициализация сервиса
search_service = HybridSearchService()

# Создание опций поиска
opts = SearchOpts(
    top_k=50,
    threshold=0.7,
    search_mode=SearchMode.HYBRID,
    enable_escalation=True
)

# Выполнение поиска
normalized_result = NormalizationResult(
    normalized="Иван Петров",
    tokens=["Иван", "Петров"],
    trace=[],
    errors=[]
)

candidates = await search_service.find_candidates(
    normalized=normalized_result,
    text="Иван Петров",
    opts=opts
)
```

### Конфигурация

```python
from ai_service.layers.search.config import HybridSearchConfig, ElasticsearchConfig

# Создание конфигурации
config = HybridSearchConfig(
    enable_escalation=True,
    escalation_threshold=0.8,
    elasticsearch=ElasticsearchConfig(
        hosts=["localhost:9200"],
        username="elastic",
        password="password"
    )
)

# Инициализация с конфигурацией
search_service = HybridSearchService(config)
```

## Конфигурация

### ElasticsearchConfig

- `hosts`: Список хостов Elasticsearch
- `username/password`: Учетные данные для аутентификации
- `timeout`: Таймаут соединения
- `max_retries`: Максимальное количество повторов

### ACSearchConfig

- `boost`: Коэффициент усиления для AC совпадений
- `fuzziness`: Уровень нечеткости (0=точный, 1-3=нечеткий)
- `min_score`: Минимальный порог score
- `field_weights`: Веса полей для мультиполевого поиска

### VectorSearchConfig

- `boost`: Коэффициент усиления для векторных совпадений
- `ef_search`: Параметр HNSW ef_search
- `similarity_type`: Тип сходства (cosine, dot_product, l2_norm)
- `vector_dimension`: Размерность векторов

## Метрики

Сервис собирает следующие метрики:

- **Счетчики запросов**: total_requests, ac_requests, vector_requests, hybrid_requests
- **Производительность**: avg_latency_ms, p95_latency_ms
- **Качество**: hit_rate, avg_score, avg_results_per_request
- **Эскалация**: escalation_triggered

```python
# Получение метрик
metrics = search_service.get_metrics()
print(f"Hit rate: {metrics.hybrid_hit_rate:.2%}")
print(f"P95 latency: {metrics.p95_latency_ms:.2f}ms")
```

## Health Check

```python
# Проверка состояния сервиса
health = await search_service.health_check()
print(f"Status: {health['status']}")
print(f"AC Adapter: {health['ac_adapter']['status']}")
print(f"Vector Adapter: {health['vector_adapter']['status']}")
```

## Интеграция с существующими слоями

### Слой нормализации (Layer 3)
- Использует `NormalizationResult` для извлечения нормализованных имен
- Применяет токены и trace для улучшения поиска

### Слой эмбеддингов (Layer 7)
- Интегрируется для генерации векторов запросов
- Использует существующие эмбеддинги для векторного поиска

### Слой decision (Layer 8)
- Предоставляет результаты поиска для принятия решений
- Интегрируется с системой скоринга

## Fallback механизмы

При недоступности Elasticsearch сервис автоматически переключается на локальные индексы:

- **WatchlistIndexService**: Для AC-подобного поиска
- **EnhancedVectorIndex**: Для векторного поиска

## TODO

См. [integration_todos.md](integration_todos.md) для полного списка задач интеграции.

## Требования

- Python 3.8+
- Elasticsearch 8.0+ (для production)
- Существующие слои AI Service (0-8)

## Установка

```bash
# Установка зависимостей Elasticsearch
pip install elasticsearch>=8.0.0

# Или через poetry
poetry add elasticsearch>=8.0.0
```

## Разработка

### Запуск тестов

```bash
# Запуск unit тестов
pytest tests/unit/layers/search/

# Запуск интеграционных тестов
pytest tests/integration/layers/search/
```

### Линтинг

```bash
# Проверка стиля кода
black src/ai_service/layers/search/
isort src/ai_service/layers/search/
flake8 src/ai_service/layers/search/
```
