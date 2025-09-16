# ElasticsearchWatchlistAdapter

Мост от локальных `WatchlistIndexService`/`EnhancedVectorIndex` к Elasticsearch с сохранением совместимых интерфейсов.

## 🎯 Цель

Предоставить адаптер, который:
- **Совместим** с существующими интерфейсами `WatchlistIndexService`
- **Делегирует** все операции в Elasticsearch (bulk upserts, kNN, AC запросы)
- **Не хранит** локальные матрицы - всё в ES
- **Поддерживает** fallback на локальный индекс при недоступности ES
- **Минимальные правки** в остальном коде

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Existing Code                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │ WatchlistIndex  │  │    EnhancedVectorIndex         │   │
│  │    Service      │  │                                │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ElasticsearchWatchlistAdapter                 │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   AC Search     │  │      Vector Search             │   │
│  │   (msearch)     │  │      (kNN)                     │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Elasticsearch                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  AC Indices     │  │    Vector Indices              │   │
│  │  (exact/phrase) │  │    (dense_vector)              │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Интерфейс

### Совместимые методы

```python
class ElasticsearchWatchlistAdapter:
    def ready(self) -> bool
    async def build_from_corpus(self, corpus, index_id=None) -> None
    async def set_overlay_from_corpus(self, corpus, overlay_id=None) -> None
    def clear_overlay(self) -> None
    async def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]
    def get_doc(self, doc_id: str) -> Optional[WatchlistDoc]
    async def save_snapshot(self, snapshot_dir: str, as_overlay: bool = False) -> Dict
    async def reload_snapshot(self, snapshot_dir: str, as_overlay: bool = False) -> Dict
    def status(self) -> Dict
```

### Алгоритм поиска

```python
async def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
    """
    1. AC поиск: msearch с exact/phrase/ngram запросами
    2. Если score < threshold → kNN поиск
    3. Объединение и дедупликация результатов
    4. Fallback на локальный индекс при недоступности ES
    """
```

## 🔧 Конфигурация

```python
@dataclass
class ElasticsearchWatchlistConfig:
    # Elasticsearch connection
    es_url: str = "http://localhost:9200"
    es_auth: Optional[str] = None
    es_verify_ssl: bool = False
    es_timeout: float = 30.0
    
    # Index configuration
    persons_index: str = "watchlist_persons_current"
    orgs_index: str = "watchlist_orgs_current"
    
    # Search configuration
    ac_threshold: float = 0.7  # Порог для AC поиска
    ac_weak_threshold: float = 0.5  # Порог для слабых AC результатов
    max_ac_results: int = 50
    max_vector_results: int = 100
    
    # Fallback configuration
    enable_fallback: bool = True
    fallback_timeout: float = 5.0
```

## 🚀 Использование

### Базовое использование

```python
from src.ai_service.layers.embeddings.indexing.elasticsearch_watchlist_adapter import (
    ElasticsearchWatchlistAdapter,
    ElasticsearchWatchlistConfig
)

# Конфигурация
config = ElasticsearchWatchlistConfig(
    es_url="http://localhost:9200",
    ac_threshold=0.7,
    max_ac_results=50
)

# Создание адаптера
adapter = ElasticsearchWatchlistAdapter(config)

# Построение индекса
corpus = [
    ("person_001", "иван петров", "person", {"country": "RU"}),
    ("org_001", "ооо приватбанк", "org", {"country": "UA"})
]
await adapter.build_from_corpus(corpus, "my_index")

# Поиск
results = await adapter.search("иван петров", top_k=10)
# Возвращает: [("person_001", 0.85), ...]

# Очистка
await adapter.close()
```

### С fallback сервисом

```python
from src.ai_service.layers.embeddings.indexing.watchlist_index_service import WatchlistIndexService
from src.ai_service.layers.embeddings.indexing.vector_index_service import VectorIndexConfig

# Создание fallback сервиса
fallback_config = VectorIndexConfig()
fallback_service = WatchlistIndexService(fallback_config)

# Адаптер с fallback
adapter = ElasticsearchWatchlistAdapter(config, fallback_service)

# При недоступности ES автоматически используется fallback
results = await adapter.search("иван петров", top_k=10)
```

### Использование factory функций

```python
from src.ai_service.layers.embeddings.indexing.elasticsearch_watchlist_adapter import (
    create_elasticsearch_watchlist_adapter,
    create_elasticsearch_enhanced_adapter
)

# Создание адаптера с WatchlistIndexService fallback
adapter = create_elasticsearch_watchlist_adapter(config, fallback_config)

# Создание адаптера с EnhancedVectorIndex fallback
adapter = create_elasticsearch_enhanced_adapter(config, enhanced_config)
```

## 🔍 Алгоритм поиска

### 1. AC поиск (многошаблонный msearch)

```python
# Exact search на normalized_name
{
    "query": {
        "terms": {
            "normalized_name": [query.lower().strip()]
        }
    }
}

# Phrase search на name_text
{
    "query": {
        "match_phrase": {
            "name_text": {
                "query": query,
                "slop": 1
            }
        }
    }
}

# N-gram search на name_ngrams
{
    "query": {
        "match": {
            "name_ngrams": {
                "query": query,
                "operator": "AND",
                "minimum_should_match": "100%"
            }
        }
    }
}
```

### 2. Escalation к Vector поиску

```python
if ac_results and ac_results[0][1] >= ac_threshold:
    # AC результаты достаточны
    return ac_results[:top_k]
else:
    # Escalation к kNN поиску
    vector_results = await _vector_search(query, entity_type)
    # Объединение и дедупликация
    return combined_results[:top_k]
```

### 3. Vector поиск (kNN)

```python
{
    "knn": {
        "field": "name_vector",
        "query_vector": query_vector,
        "k": max_vector_results,
        "num_candidates": max_vector_results * 2,
        "similarity": "cosine"
    }
}
```

## 📊 Метрики

Адаптер отслеживает следующие метрики:

```python
{
    "ac_searches": 0,           # Количество AC поисков
    "vector_searches": 0,       # Количество Vector поисков
    "escalations": 0,           # Количество escalations
    "fallbacks": 0,             # Количество fallback вызовов
    "errors": 0,                # Количество ошибок
    "total_searches": 0,        # Общее количество поисков
    "avg_search_time": 0.0      # Среднее время поиска
}
```

## 🔄 Snapshot операции

### Сохранение снимка

```python
result = await adapter.save_snapshot("/tmp/snapshot")
# Создает snapshot repository и snapshot в Elasticsearch
```

### Загрузка снимка

```python
result = await adapter.reload_snapshot("/tmp/snapshot")
# Восстанавливает snapshot из Elasticsearch
```

## 🛡️ Обработка ошибок

### Health Check

```python
# Автоматическая проверка доступности ES
if not await _health_check():
    # Использование fallback сервиса
    return fallback_service.search(query, top_k)
```

### Fallback стратегия

1. **ES недоступен** → использование локального индекса
2. **Ошибка поиска** → fallback на локальный сервис
3. **Таймаут** → graceful degradation

## 🧪 Тестирование

### Unit тесты

```bash
pytest tests/unit/test_elasticsearch_watchlist_adapter.py -v
```

### Integration тесты

```bash
# Требует запущенный Elasticsearch
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/test_elasticsearch_watchlist_adapter.py -v
```

## 📈 Производительность

### Оптимизации

- **Bulk операции** для индексации
- **Multi-search** для AC запросов
- **kNN** для vector поиска
- **Connection pooling** для HTTP клиента
- **Health check кэширование**

### Ожидаемая производительность

- **AC поиск**: < 50ms
- **Vector поиск**: < 100ms
- **Bulk индексация**: 1000 docs/sec
- **Fallback**: < 10ms overhead

## 🔧 Интеграция с существующим кодом

### Минимальные изменения

```python
# Было
watchlist_service = WatchlistIndexService(config)

# Стало
watchlist_service = ElasticsearchWatchlistAdapter(es_config, fallback_config)
```

### Совместимость

- ✅ **Тот же интерфейс** - никаких изменений в вызывающем коде
- ✅ **Тот же формат данных** - `List[Tuple[str, float]]`
- ✅ **Тот же API** - все методы работают одинаково
- ✅ **Fallback** - автоматический fallback при проблемах

## 🚀 Развертывание

### Требования

- Elasticsearch 8.11+
- Python 3.10+
- httpx для HTTP клиента

### Установка

```bash
pip install httpx numpy
```

### Конфигурация

```bash
export ES_URL="http://localhost:9200"
export ES_AUTH="username:password"  # опционально
export ES_VERIFY_SSL="false"
```

## 📝 Примеры

См. `examples/elasticsearch_watchlist_adapter_example.py` для полных примеров использования.

## 🎉 Результат

Создан адаптер, который:

1. **Совместим** с существующими интерфейсами
2. **Делегирует** все операции в Elasticsearch
3. **Поддерживает** fallback на локальные индексы
4. **Минимальные правки** в остальном коде
5. **Готов к продакшену** с мониторингом и обработкой ошибок

Мост от локальных индексов к Elasticsearch готов! 🚀
