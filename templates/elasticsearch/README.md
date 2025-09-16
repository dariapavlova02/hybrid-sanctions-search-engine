# Elasticsearch Templates for Watchlist Search

Шаблоны индексов Elasticsearch для гибридного поиска в watchlist с поддержкой AC (точного) и Vector (kNN) поиска.

## Файлы

- **elasticsearch_setup.sh** - Автоматическая установка всех шаблонов
- **elasticsearch_curl_commands.md** - Ручные cURL команды для установки
- **elasticsearch_templates.json** - Все шаблоны в одном файле
- **elasticsearch_component_template.json** - Component template с анализаторами
- **elasticsearch_persons_template.json** - Index template для людей
- **elasticsearch_orgs_template.json** - Index template для организаций

## Быстрая установка

```bash
# Установка всех шаблонов
chmod +x elasticsearch_setup.sh
./elasticsearch_setup.sh

# С аутентификацией
ES_HOST=localhost:9200 ES_USER=elastic ES_PASS=password ./elasticsearch_setup.sh
```

## Ручная установка

См. [elasticsearch_curl_commands.md](elasticsearch_curl_commands.md) для детальных cURL команд.

## Структура индексов

### Поля

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_id` | keyword | Уникальный идентификатор сущности |
| `entity_type` | keyword | Тип сущности: "person" или "org" |
| `dob` | date | Дата рождения (опционально) |
| `country` | keyword | Код страны |
| `normalized_name` | keyword | Нормализованное имя для точного поиска |
| `aliases` | keyword | Алиасы (множественные значения) |
| `name_text` | text | Полнотекстовый поиск с ICU анализатором |
| `name_ngrams` | text | N-grams для нечеткого поиска |
| `name_vector` | dense_vector | Dense вектор для kNN поиска (384 dims) |
| `meta` | object | Метаданные (гибкий объект) |

### Анализаторы

#### case_insensitive_normalizer
- **Назначение**: Точный поиск без учета регистра
- **Фильтры**: lowercase, asciifolding, icu_folding
- **Особенность**: Сохраняет кириллические символы при folding

#### icu_text_analyzer
- **Назначение**: Полнотекстовый поиск с поддержкой Unicode
- **Токенизатор**: icu_tokenizer
- **Фильтры**: icu_normalizer, icu_folding, lowercase

#### shingle_analyzer
- **Назначение**: Фразовый поиск с shingles
- **Токенизатор**: icu_tokenizer
- **Фильтры**: icu_normalizer, icu_folding, lowercase, shingle (2-3 граммы)

#### char_ngram_analyzer
- **Назначение**: N-grams для нечеткого поиска
- **Токенизатор**: keyword
- **Фильтры**: lowercase, asciifolding, char_ngram_filter (3-5 грамм)

## Типы поиска

### 1. AC (Точный) поиск
- Поиск по `normalized_name` и `aliases`
- Case-insensitive matching
- Fuzzy matching с fuzziness=1

### 2. Vector (kNN) поиск
- Поиск по `name_vector` с cosine similarity
- HNSW индекс для быстрого поиска
- 384-мерные векторы

### 3. Hybrid поиск
- Комбинация AC и Vector поиска
- Эскалация: AC → Vector при слабых результатах
- Взвешивание результатов

## Примеры использования

### Тестовые данные

```bash
# Добавить тестовую персону
curl -X POST "localhost:9200/watchlist_persons_v1/_doc" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "P001",
    "entity_type": "person",
    "dob": "1985-05-15",
    "country": "RU",
    "normalized_name": "Иван Петров",
    "aliases": ["И. Петров", "Ivan Petrov"],
    "name_text": "Иван Петров",
    "name_ngrams": "Иван Петров",
    "name_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
    "meta": {
      "source": "test",
      "confidence": 0.95
    }
  }'
```

### Поиск

```bash
# AC поиск
curl -X POST "localhost:9200/watchlist_persons_v1/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "multi_match": {
        "query": "Иван Петров",
        "fields": ["normalized_name^2.0", "aliases^1.5"],
        "type": "best_fields",
        "fuzziness": 1
      }
    }
  }'

# Vector поиск
curl -X POST "localhost:9200/watchlist_persons_v1/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
      "k": 10,
      "num_candidates": 100
    }
  }'
```

## Интеграция с AI Service

Эти шаблоны используются в слое поиска (Layer 9) AI Service:

- **ElasticsearchACAdapter**: Использует AC поля для точного поиска
- **ElasticsearchVectorAdapter**: Использует vector поля для kNN поиска
- **HybridSearchService**: Комбинирует оба типа поиска с эскалацией

## Требования

- Elasticsearch 8.0+
- ICU Analysis plugin (обычно включен по умолчанию)
- Достаточно памяти для HNSW индексов
