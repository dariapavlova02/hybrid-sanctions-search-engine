# AC Search Templates for Elasticsearch

Набор готовых ES DSL-запросов для AC-этапа поиска с многошаблонным поиском и скорингом.

## Возможности

- ✅ **3 типа поиска** в порядке убывания строгости
- ✅ **Exact поиск** по `normalized_name`/`aliases` (case-insensitive)
- ✅ **Phrase поиск** по `name_text` с shingles (slop=0..1)
- ✅ **Char-ngram поиск** по `name_ngrams` (operator=AND, 100% minimum_should_match)
- ✅ **Multi-search** с порогами и детекцией слабого сигнала
- ✅ **ACScore** с типом, score и matched_field
- ✅ **Best-hit** алгоритм для множественных кандидатов
- ✅ **Готовые JSON шаблоны** с параметризацией

## Типы поиска

### 1. Exact Match (Строгость: 4/4)

**Назначение**: Точные совпадения по нормализованным именам и алиасам

**Поля**: `normalized_name`, `aliases`
**Оператор**: `terms` с `boost`
**Порог**: `exact_threshold >= 1.0`

```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"entity_type": "person"}},
        {
          "bool": {
            "should": [
              {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}},
              {"terms": {"aliases": ["иван", "петров"], "boost": 1.5}}
            ],
            "minimum_should_match": 1
          }
        }
      ]
    }
  }
}
```

### 2. Phrase Match (Строгость: 3/4)

**Назначение**: Фразовые совпадения с учетом порядка слов

**Поля**: `name_text.shingle`
**Оператор**: `match_phrase` с `slop`
**Порог**: `phrase_threshold >= 0.8`

```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"entity_type": "person"}},
        {
          "match_phrase": {
            "name_text.shingle": {
              "query": "иван петров",
              "slop": 1,
              "boost": 1.8
            }
          }
        }
      ]
    }
  }
}
```

### 3. Char-ngram Match (Строгость: 2/4)

**Назначение**: Нечеткие совпадения по n-граммам

**Поля**: `name_ngrams`
**Оператор**: `match` с `operator=AND`
**Порог**: `ngram_threshold >= 0.6`

```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"entity_type": "person"}},
        {
          "match": {
            "name_ngrams": {
              "query": "иван петров",
              "operator": "AND",
              "minimum_should_match": "100%",
              "boost": 1.0
            }
          }
        }
      ]
    }
  }
}
```

## Multi-Search Template

### Структура запроса

```json
[
  {"index": "watchlist_persons_current", "search_type": "query_then_fetch"},
  { /* exact query */ },
  {"index": "watchlist_persons_current", "search_type": "query_then_fetch"},
  { /* phrase query */ },
  {"index": "watchlist_persons_current", "search_type": "query_then_fetch"},
  { /* ngram query */ }
]
```

### Пороги и слабый сигнал

| Тип | Порог | Описание |
|-----|-------|----------|
| `exact_threshold` | 1.0 | Минимальный score для exact совпадений |
| `phrase_threshold` | 0.8 | Минимальный score для phrase совпадений |
| `ngram_threshold` | 0.6 | Минимальный score для ngram совпадений |
| `weak_threshold` | 0.4 | Минимальный score для слабых сигналов |

**Слабый сигнал**: Нет exact/phrase совпадений, но есть ngram с score >= T_ng

## ACScore Format

```json
{
  "type": "exact|phrase|ngram|weak",
  "score": 2.0,
  "matched_field": "normalized_name|name_text.shingle|name_ngrams",
  "matched_text": "иван петров",
  "entity_id": "person_001",
  "entity_type": "person"
}
```

## Best-Hit Algorithm

### Приоритет типов
1. **Exact** (приоритет 4) - высший приоритет
2. **Phrase** (приоритет 3) - средний приоритет
3. **N-gram** (приоритет 2) - низкий приоритет
4. **Weak** (приоритет 1) - минимальный приоритет

### Алгоритм выбора
```python
def find_best_hit(ac_scores):
    # Сортировка по (приоритет_типа, score)
    return max(ac_scores, key=lambda s: (type_priority[s.type], s.score))
```

### Примеры

**Пример 1: Exact приоритет**
```json
{
  "candidates": [
    {"type": "exact", "score": 1.5, "matched_text": "иван петров"},
    {"type": "phrase", "score": 2.0, "matched_text": "иван петрович"}
  ],
  "best_hit": {"type": "exact", "score": 1.5, "matched_text": "иван петров"},
  "reason": "Exact match имеет высший приоритет независимо от score"
}
```

**Пример 2: Score приоритет**
```json
{
  "candidates": [
    {"type": "phrase", "score": 1.2, "matched_text": "иван петрович"},
    {"type": "ngram", "score": 1.8, "matched_text": "иван петровский"}
  ],
  "best_hit": {"type": "phrase", "score": 1.2, "matched_text": "иван петрович"},
  "reason": "Phrase match имеет высший приоритет, затем максимальный score"
}
```

**Пример 3: Слабый сигнал**
```json
{
  "candidates": [
    {"type": "ngram", "score": 0.8, "matched_text": "иван петровский"},
    {"type": "ngram", "score": 0.6, "matched_text": "петр иванов"}
  ],
  "best_hit": {"type": "ngram", "score": 0.8, "matched_text": "иван петровский"},
  "weak_signal": true,
  "reason": "Нет exact/phrase совпадений, но ngram с score >= T_ng (0.6)"
}
```

## Использование

### Python API

```python
from ac_search_templates import ACSearchTemplates

# Создание шаблонов
templates = ACSearchTemplates(
    exact_threshold=1.0,
    phrase_threshold=0.8,
    ngram_threshold=0.6,
    weak_threshold=0.4
)

# Создание запросов
search_terms = ["иван", "петров"]
entity_type = "person"

exact_query = templates.create_exact_query(search_terms, entity_type)
phrase_query = templates.create_phrase_query(search_terms, entity_type)
ngram_query = templates.create_ngram_query(search_terms, entity_type)
multi_search = templates.create_multi_search_template(search_terms, entity_type)

# Парсинг результатов
ac_scores = templates.parse_ac_results(msearch_response)
best_hit = templates.find_best_hit(ac_scores)
weak_signal = templates.detect_weak_signal(ac_scores)
```

### cURL команды

```bash
# Exact search
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}]}}, "size": 50}}'

# Multi-search
curl -X POST "localhost:9200/_msearch" \
  -H "Content-Type: application/x-ndjson" \
  -d '{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}]}}, "size": 50}}
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match_phrase": {"name_text.shingle": {"query": "иван петров", "slop": 1, "boost": 1.8}}}]}}, "size": 50}}
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match": {"name_ngrams": {"query": "иван петров", "operator": "AND", "minimum_should_match": "100%", "boost": 1.0}}}]}}, "size": 50}}'
```

### Демо скрипт

```bash
# Запуск демо
python scripts/demo_ac_search.py

# Генерация шаблонов
python scripts/ac_search_templates.py
```

## Параметризация

### Шаблоны с переменными

```json
{
  "exact_query_template": {
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "{{entity_type}}"}},
          {"terms": {"normalized_name": "{{search_terms}}", "boost": 2.0}}
        ]
      }
    }
  }
}
```

### Подстановка значений

```python
# Замена переменных в шаблоне
template = load_template("exact_query_template")
query = template.replace("{{entity_type}}", "person").replace("{{search_terms}}", ["иван", "петров"])
```

## Интеграция с AI Service

### Слой 9 (Search)

```python
# ElasticsearchACAdapter
class ElasticsearchACAdapter:
    def __init__(self, templates: ACSearchTemplates):
        self.templates = templates
    
    async def search(self, normalized: NormalizationResult, text: str) -> List[Candidate]:
        search_terms = self.extract_terms(normalized, text)
        entity_type = self.determine_entity_type(normalized)
        
        # Multi-search
        multi_search = self.templates.create_multi_search_template(search_terms, entity_type)
        response = await self.es_client.msearch(multi_search)
        
        # Parse results
        ac_scores = self.templates.parse_ac_results(response)
        best_hit = self.templates.find_best_hit(ac_scores)
        
        return self.convert_to_candidates(ac_scores)
```

### HybridSearchService

```python
# Escalation logic
if not ac_results or self.is_weak_signal(ac_results):
    # Escalate to vector search
    vector_results = await self.vector_adapter.search(normalized, text)
    return self.combine_results(ac_results, vector_results)
```

## Производительность

### Рекомендуемые настройки

| Параметр | Значение | Описание |
|----------|----------|----------|
| `size` | 50 | Количество результатов на запрос |
| `boost` | 2.0/1.5/1.0 | Веса для exact/phrase/ngram |
| `slop` | 0-1 | Максимальное расстояние для phrase |
| `minimum_should_match` | 1/100% | Минимальные совпадения |

### Оптимизация

1. **Используйте multi-search** для параллельного выполнения
2. **Настройте boost** в зависимости от важности полей
3. **Ограничьте size** для быстрого ответа
4. **Кэшируйте результаты** для повторяющихся запросов

## Мониторинг

### Метрики

- **Количество запросов** по типам (exact/phrase/ngram)
- **Время выполнения** каждого типа поиска
- **Hit rate** по порогам
- **Слабые сигналы** и эскалация к vector search

### Логирование

```python
logger.info(f"AC Search: {search_type} - {len(results)} hits - {best_score:.2f}")
logger.warning(f"Weak signal detected: {weak_signal}")
logger.debug(f"AC Scores: {[f'{s.type}:{s.score:.2f}' for s in ac_scores]}")
```

## Troubleshooting

### Частые проблемы

1. **Нет результатов**: Проверьте нормализацию и индексацию
2. **Низкие scores**: Настройте boost и пороги
3. **Медленные запросы**: Оптимизируйте multi-search
4. **Ложные срабатывания**: Увеличьте пороги

### Отладка

```bash
# Проверка индекса
curl -X GET "localhost:9200/watchlist_persons_current/_stats"

# Объяснение скоринга
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {...}, "explain": true}'

# Профилирование
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {...}, "profile": true}'
```
