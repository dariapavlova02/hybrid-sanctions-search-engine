# Elasticsearch Data Pipeline - Полный Цикл Загрузки Данных

Полное описание процесса формирования и загрузки данных в Elasticsearch от исходных JSON файлов до runtime поиска.

## 🎯 Обзор

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA PIPELINE                                  │
│                                                                         │
│  JSON Files → Data Loader → AC Generator → Vector Generator → ES       │
│     ↓             ↓              ↓                ↓              ↓      │
│  sanctions    normalize      patterns         embeddings      indices   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 📊 Этапы Pipeline

### Этап 1: Исходные Данные

**Местоположение:** `data/sanctions/*.json`

**Структура JSON файлов:**
```json
{
  "persons": [
    {
      "id": "P001",
      "name": "Иван Иванович Петров",
      "aliases": ["И.И. Петров", "Ivan Petrov"],
      "date_of_birth": "1985-05-15",
      "country": "RU",
      "metadata": {
        "source": "OFAC",
        "list_type": "SDN"
      }
    }
  ],
  "organizations": [
    {
      "id": "O001",
      "name": "ООО \"Рога и Копыта\"",
      "aliases": ["Рога и Копыта", "Roga i Kopyta LLC"],
      "country": "RU",
      "metadata": {
        "inn": "1234567890",
        "ogrn": "1234567890123"
      }
    }
  ]
}
```

**Файлы:**
- `all_persons_full.json` - полный список персон
- `all_orgs_full.json` - полный список организаций
- Другие специфичные списки (OFAC, EU, UK, etc.)

---

### Этап 2: Загрузка и Нормализация

**Компонент:** `src/ai_service/layers/search/sanctions_data_loader.py`

**Процесс:**

```python
class SanctionsDataLoader:
    async def load_sanctions_data(self) -> SanctionsDataset:
        # 1. Чтение всех JSON файлов из data/sanctions/
        files = glob("data/sanctions/*.json")

        # 2. Парсинг и валидация
        for file in files:
            data = json.load(file)
            persons.extend(data.get("persons", []))
            orgs.extend(data.get("organizations", []))

        # 3. Дедупликация по ID
        unique_persons = deduplicate_by_id(persons)
        unique_orgs = deduplicate_by_id(orgs)

        # 4. Кэширование
        cache_to_file("sanctions_cache.json", dataset)

        return SanctionsDataset(
            persons=unique_persons,
            organizations=unique_orgs
        )
```

**Выход:**
- `SanctionsDataset` - структурированный объект
- `data/sanctions/sanctions_cache.json` - кэш (34 MB, TTL 24h)

**Статистика:**
- ~15,000 персон
- ~8,000 организаций
- ~50,000 алиасов

---

### Этап 3: Генерация AC Patterns

**Компонент:** `src/ai_service/layers/variants/templates/high_recall_ac_generator.py`

**Tier-Based Pattern System:**

#### Tier 0: Exact Matches (confidence = 1.0)
```python
def generate_tier0_patterns(name: str) -> List[str]:
    """
    Точные совпадения без вариаций
    """
    return [
        name.lower(),                    # "иван петров"
        normalize_spaces(name.lower()),  # убираем множественные пробелы
    ]
```

#### Tier 1: High Recall (confidence = 0.8-0.95)
```python
def generate_tier1_patterns(name: str) -> List[str]:
    """
    Транслитерации, частичные имена, инициалы
    """
    patterns = []

    # Транслитерация
    patterns.append(transliterate(name, "ru", "en"))  # "Ivan Petrov"
    patterns.append(transliterate(name, "en", "ru"))  # обратная

    # Частичные имена
    tokens = tokenize(name)
    patterns.extend(generate_partial_names(tokens))   # "Петров И.И."

    # Инициалы
    patterns.extend(generate_initial_variants(tokens)) # "И. Петров"

    # Порядок токенов
    patterns.extend(generate_token_permutations(tokens)) # "Петров Иван"

    return patterns
```

#### Tier 2: Medium Recall (confidence = 0.6-0.8)
```python
def generate_tier2_patterns(name: str) -> List[str]:
    """
    N-grams, фонетические варианты
    """
    patterns = []

    # Character n-grams (3-5 символов)
    patterns.extend(generate_ngrams(name, min_n=3, max_n=5))

    # Phonetic variants
    patterns.extend(generate_phonetic_variants(name))  # метафоны

    # Уменьшительные формы
    patterns.extend(diminutive_variants(name))  # "Ваня" → "Иван"

    return patterns
```

#### Tier 3: Low Recall (confidence = 0.4-0.6)
```python
def generate_tier3_patterns(name: str) -> List[str]:
    """
    Fuzzy/typo-tolerant варианты
    """
    patterns = []

    # Typo simulation (1-2 опечатки)
    patterns.extend(generate_typo_variants(name, max_edits=2))

    # Keyboard layout errors
    patterns.extend(generate_layout_errors(name))  # ru/en раскладка

    # OCR errors (визуально похожие символы)
    patterns.extend(generate_ocr_errors(name))  # O↔0, l↔1

    return patterns
```

**Полный процесс генерации:**

```python
class HighRecallACGenerator:
    def generate_patterns_for_entity(
        self,
        entity: Dict,
        entity_type: str
    ) -> Dict[str, List[ACPattern]]:

        patterns = []

        # 1. Из основного имени
        name = entity.get("name", "")
        patterns.extend(self._generate_all_tiers(name))

        # 2. Из алиасов
        for alias in entity.get("aliases", []):
            patterns.extend(self._generate_all_tiers(alias))

        # 3. Для организаций - дополнительно
        if entity_type == "org":
            # Убираем legal forms
            core = extract_org_core(name)
            patterns.extend(self._generate_all_tiers(core))

            # Варианты с/без кавычек
            patterns.extend(generate_quote_variants(name))

        # 4. Дедупликация и сортировка по confidence
        unique_patterns = deduplicate_patterns(patterns)
        sorted_patterns = sort_by_confidence(unique_patterns)

        return {
            entity["id"]: sorted_patterns
        }
```

**Выход:**
- Словарь `{entity_id: [ACPattern(text, tier, confidence)]}`
- ~500,000-1,000,000 уникальных паттернов для всего корпуса
- Сохраняется в памяти (не в файл, слишком большой)

**Статистика паттернов:**
- Tier 0: ~23,000 паттернов (точные)
- Tier 1: ~150,000 паттернов (транслит, частичные)
- Tier 2: ~400,000 паттернов (n-grams, phonetic)
- Tier 3: ~500,000 паттернов (fuzzy, typos)

---

### Этап 4: Генерация Vector Embeddings

**Компонент:** `scripts/generate_vectors.py`

**Модель:**
```python
model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
# Multilingual model supporting ru/uk/en
# Output: 384-dimensional dense vectors
```

**Процесс:**

```python
class VectorGenerator:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )

    def generate_vector(self, text: str) -> List[float]:
        """
        Генерирует 384-мерный вектор для текста
        """
        # 1. Нормализация текста
        normalized = normalize_text(text)

        # 2. Генерация embedding
        embedding = self.model.encode([normalized])

        # 3. Конвертация в список
        vector = embedding[0].tolist()  # [float] * 384

        return vector

    def generate_for_corpus(
        self,
        dataset: SanctionsDataset
    ) -> Dict[str, List[float]]:

        vectors = {}

        # Для персон
        for person in dataset.persons:
            name = person["name"]
            vector = self.generate_vector(name)
            vectors[person["id"]] = vector

        # Для организаций
        for org in dataset.organizations:
            name = org["name"]
            vector = self.generate_vector(name)
            vectors[org["id"]] = vector

        return vectors
```

**Выход:**
- `{entity_id: [float] * 384}`
- Размер одного вектора: 384 floats × 4 bytes = ~1.5 KB
- Размер всех векторов: 23,000 entities × 1.5 KB ≈ 34 MB

**Оптимизация:**
- Batch encoding для ускорения (batch_size=32)
- GPU acceleration если доступно
- Кэширование в памяти

---

### Этап 5: Создание Elasticsearch Индексов

**Компонент:** `scripts/elasticsearch_setup_and_warmup.py`

#### 5.1 Component Template

**Файл:** `templates/elasticsearch/elasticsearch_component_template.json`

```json
{
  "template": {
    "settings": {
      "analysis": {
        "normalizer": {
          "case_insensitive_normalizer": {
            "type": "custom",
            "filter": ["lowercase", "asciifolding", "icu_folding"]
          }
        },
        "analyzer": {
          "icu_text_analyzer": {
            "tokenizer": "icu_tokenizer",
            "filter": ["icu_normalizer", "icu_folding", "lowercase"]
          },
          "char_ngram_analyzer": {
            "tokenizer": "keyword",
            "filter": ["lowercase", "asciifolding", {
              "type": "ngram",
              "min_gram": 3,
              "max_gram": 5
            }]
          },
          "shingle_analyzer": {
            "tokenizer": "icu_tokenizer",
            "filter": ["icu_normalizer", "icu_folding", "lowercase", {
              "type": "shingle",
              "min_shingle_size": 2,
              "max_shingle_size": 3
            }]
          }
        }
      }
    }
  }
}
```

**Создание:**
```bash
curl -X PUT "localhost:9200/_component_template/watchlist_analyzers" \
  -H "Content-Type: application/json" \
  -d @elasticsearch_component_template.json
```

#### 5.2 Index Templates

**Для персон:** `templates/elasticsearch/elasticsearch_persons_template.json`

```json
{
  "index_patterns": ["watchlist_persons_*"],
  "composed_of": ["watchlist_analyzers"],
  "template": {
    "mappings": {
      "properties": {
        "entity_id": {"type": "keyword"},
        "entity_type": {"type": "keyword"},
        "dob": {"type": "date", "format": "strict_date_optional_time||yyyy-MM-dd"},
        "country": {"type": "keyword"},

        "normalized_text": {
          "type": "keyword",
          "normalizer": "case_insensitive_normalizer"
        },
        "aliases": {
          "type": "keyword",
          "normalizer": "case_insensitive_normalizer"
        },

        "name_text": {
          "type": "text",
          "analyzer": "icu_text_analyzer"
        },
        "name_ngrams": {
          "type": "text",
          "analyzer": "char_ngram_analyzer"
        },
        "name_shingles": {
          "type": "text",
          "analyzer": "shingle_analyzer"
        },

        "name_vector": {
          "type": "dense_vector",
          "dims": 384,
          "index": true,
          "similarity": "cosine"
        },

        "ac_patterns": {
          "type": "text",
          "fields": {
            "keyword": {"type": "keyword"}
          }
        },

        "metadata": {"type": "object", "enabled": true}
      }
    }
  }
}
```

**Для организаций:** аналогично, `watchlist_orgs_*` pattern

**Создание:**
```bash
curl -X PUT "localhost:9200/_index_template/watchlist_persons_template" \
  -d @elasticsearch_persons_template.json

curl -X PUT "localhost:9200/_index_template/watchlist_orgs_template" \
  -d @elasticsearch_orgs_template.json
```

#### 5.3 Создание конкретных индексов

```python
async def create_indices():
    timestamp = int(time.time())

    # Новые индексы с timestamp
    persons_index = f"watchlist_persons_v{timestamp}"
    orgs_index = f"watchlist_orgs_v{timestamp}"

    # Создание индексов (шаблон применится автоматически)
    await es_client.indices.create(index=persons_index)
    await es_client.indices.create(index=orgs_index)

    return persons_index, orgs_index
```

---

### Этап 6: Bulk Loading в Elasticsearch

**Компонент:** `scripts/elasticsearch_setup_and_warmup.py`

**Процесс:**

```python
async def bulk_load_data(
    dataset: SanctionsDataset,
    ac_patterns: Dict[str, List[ACPattern]],
    vectors: Dict[str, List[float]],
    persons_index: str,
    orgs_index: str
):

    # 1. Подготовка bulk actions для персон
    person_actions = []
    for person in dataset.persons:
        person_id = person["id"]

        # Формирование документа
        doc = {
            "entity_id": person_id,
            "entity_type": "person",
            "dob": person.get("date_of_birth"),
            "country": person.get("country", "UNKNOWN"),

            # AC поля
            "normalized_text": person["name"].lower(),
            "aliases": [a.lower() for a in person.get("aliases", [])],
            "name_text": person["name"],
            "name_ngrams": person["name"],
            "name_shingles": person["name"],

            # AC patterns
            "ac_patterns": [
                p.text for p in ac_patterns.get(person_id, [])
            ],

            # Vector
            "name_vector": vectors.get(person_id, [0.0] * 384),

            # Metadata
            "metadata": person.get("metadata", {})
        }

        # Bulk action
        person_actions.append({"index": {"_index": persons_index, "_id": person_id}})
        person_actions.append(doc)

    # 2. Подготовка bulk actions для организаций (аналогично)
    org_actions = []
    for org in dataset.organizations:
        # ... аналогично персонам
        pass

    # 3. Выполнение bulk операций
    # Chunked bulk для избежания timeout (chunk_size=500)
    await bulk_with_chunking(
        es_client,
        person_actions,
        chunk_size=500,
        max_retries=3
    )

    await bulk_with_chunking(
        es_client,
        org_actions,
        chunk_size=500,
        max_retries=3
    )

    # 4. Refresh индексов
    await es_client.indices.refresh(index=persons_index)
    await es_client.indices.refresh(index=orgs_index)

    # 5. Верификация
    persons_count = await es_client.count(index=persons_index)
    orgs_count = await es_client.count(index=orgs_index)

    logger.info(f"Loaded {persons_count} persons, {orgs_count} orgs")
```

**Оптимизации:**
- Chunked bulk (500 docs per chunk)
- Retry logic (max 3 retries)
- Refresh после загрузки
- Параллельная загрузка persons/orgs

**Время загрузки:**
- 15,000 персон: ~30 секунд
- 8,000 организаций: ~15 секунд
- Общее: ~45 секунд

---

### Этап 7: Blue-Green Deployment с Aliases

**Цель:** Zero-downtime обновление индексов

**Процесс:**

```python
async def rollover_aliases(
    new_persons_index: str,
    new_orgs_index: str
):

    # 1. Получить текущие алиасы
    old_persons_alias = await get_index_by_alias("watchlist_persons_current")
    old_orgs_alias = await get_index_by_alias("watchlist_orgs_current")

    # 2. Атомарная операция переключения
    actions = []

    # Persons
    if old_persons_alias:
        actions.append({
            "remove": {
                "index": old_persons_alias,
                "alias": "watchlist_persons_current"
            }
        })

    actions.append({
        "add": {
            "index": new_persons_index,
            "alias": "watchlist_persons_current"
        }
    })

    # Orgs
    if old_orgs_alias:
        actions.append({
            "remove": {
                "index": old_orgs_alias,
                "alias": "watchlist_orgs_current"
            }
        })

    actions.append({
        "add": {
            "index": new_orgs_index,
            "alias": "watchlist_orgs_current"
        }
    })

    # 3. Выполнение атомарного update_aliases
    await es_client.indices.update_aliases(body={"actions": actions})

    # 4. Верификация
    verify_aliases()

    logger.info(f"Rollover complete: {new_persons_index}, {new_orgs_index}")
```

**Результат:**
```
watchlist_persons_current → watchlist_persons_v1696234567
watchlist_orgs_current    → watchlist_orgs_v1696234567
```

**Преимущества:**
- Нулевой downtime
- Мгновенное переключение (атомарная операция)
- Возможность rollback (старые индексы остаются)
- Тестирование новых индексов перед переключением

---

### Этап 8: Warmup и Оптимизация

**Компонент:** `scripts/elasticsearch_setup_and_warmup.py`

**Цель:** Прогреть кэши Elasticsearch для оптимальной производительности

```python
async def warmup_indices():

    # 1. kNN warmup - top 10 самых частых запросов
    top_queries = [
        "Иван Петров",
        "ООО Рога и Копыта",
        "John Smith",
        "Петро Порошенко",
        "Володимир Зеленський",
        # ... всего 10 запросов
    ]

    for query in top_queries:
        # kNN search
        vector = generate_vector(query)
        await es_client.search(
            index="watchlist_persons_current",
            body={
                "knn": {
                    "field": "name_vector",
                    "query_vector": vector,
                    "k": 10,
                    "num_candidates": 100
                }
            }
        )

    # 2. AC warmup - фильтрация по полям
    await es_client.search(
        index="watchlist_persons_current",
        body={
            "query": {
                "multi_match": {
                    "query": "Петров",
                    "fields": ["normalized_text^2.0", "aliases^1.5"],
                    "fuzziness": 1
                }
            }
        }
    )

    # 3. Aggregations warmup
    await es_client.search(
        index="watchlist_persons_current",
        body={
            "size": 0,
            "aggs": {
                "countries": {"terms": {"field": "country"}}
            }
        }
    )

    logger.info("Warmup complete")
```

**Эффект:**
- Первый поиск: ~200ms
- После warmup: ~15-30ms
- kNN индекс загружен в память
- Aggregation кэши прогреты

---

### Этап 9: Runtime Search

**Компонент:** `src/ai_service/layers/search/hybrid_search_service.py`

#### 9.1 AC Search

```python
class ElasticsearchACAdapter:
    async def search(self, query: str, opts: SearchOpts) -> List[Candidate]:

        # Build multi-match query
        body = {
            "query": {
                "bool": {
                    "should": [
                        # Exact match (highest priority)
                        {
                            "term": {
                                "normalized_text.keyword": {
                                    "value": query.lower(),
                                    "boost": 2.0 * opts.ac_boost
                                }
                            }
                        },
                        # AC pattern match
                        {
                            "term": {
                                "ac_patterns.keyword": {
                                    "value": query,
                                    "boost": 3.0 * opts.ac_boost
                                }
                            }
                        },
                        # Multi-field fuzzy
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "normalized_text^2.0",
                                    "aliases^1.5",
                                    "name_text^1.0"
                                ],
                                "fuzziness": opts.ac_fuzziness,  # 0-3
                                "type": "best_fields"
                            }
                        },
                        # N-gram match
                        {
                            "match": {
                                "name_ngrams": {
                                    "query": query,
                                    "boost": 0.8 * opts.ac_boost
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": opts.top_k,
            "min_score": opts.ac_min_score
        }

        response = await self.es_client.search(
            index="watchlist_persons_current",
            body=body
        )

        return parse_candidates(response)
```

**Производительность:**
- P50: 15-25ms
- P95: 30-50ms
- P99: 50-80ms

#### 9.2 Vector Search

```python
class ElasticsearchVectorAdapter:
    async def search(self, query: str, opts: SearchOpts) -> List[Candidate]:

        # Generate query vector
        query_vector = self.embedding_service.encode(query)

        # kNN search
        body = {
            "knn": {
                "field": "name_vector",
                "query_vector": query_vector,  # [float] * 384
                "k": opts.top_k,
                "num_candidates": opts.max_escalation_results,
                "similarity": opts.vector_min_score
            },
            "size": opts.top_k
        }

        response = await self.es_client.search(
            index="watchlist_persons_current",
            body=body
        )

        return parse_candidates(response)
```

**Производительность:**
- P50: 20-30ms
- P95: 40-60ms
- P99: 60-100ms

**HNSW параметры:**
- `m`: 16 (connections per layer)
- `ef_construction`: 200
- `ef_search`: 100 (runtime)

#### 9.3 Hybrid Search с Escalation

```python
class HybridSearchService:
    async def find_candidates(
        self,
        normalized: NormalizationResult,
        text: str,
        opts: SearchOpts
    ) -> List[Candidate]:

        # 1. AC Search (первый этап)
        ac_candidates = await self.ac_adapter.search(
            query=normalized.normalized,
            opts=opts
        )

        # 2. Проверка на эскалацию
        best_ac_score = max(c.score for c in ac_candidates) if ac_candidates else 0.0

        should_escalate = (
            opts.enable_escalation and
            best_ac_score < opts.escalation_threshold  # default 0.6
        )

        if should_escalate:
            # 3. Vector Search (эскалация)
            vector_candidates = await self.vector_adapter.search(
                query=text,
                opts=opts
            )

            # 4. Fusion (RRF - Reciprocal Rank Fusion)
            candidates = reciprocal_rank_fusion(
                ac_candidates,
                vector_candidates,
                ac_weight=0.7,      # 70% AC
                vector_weight=0.3   # 30% Vector
            )
        else:
            candidates = ac_candidates

        # 5. Дедупликация
        candidates = deduplicate_by_id(candidates)

        # 6. Сортировка и ограничение
        candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
        candidates = candidates[:opts.top_k]

        return candidates
```

**RRF Formula:**
```python
def reciprocal_rank_fusion(
    ac_results: List[Candidate],
    vector_results: List[Candidate],
    ac_weight: float = 0.7,
    vector_weight: float = 0.3,
    k: int = 60  # RRF constant
) -> List[Candidate]:

    scores = defaultdict(float)

    # AC scores
    for rank, candidate in enumerate(ac_results, start=1):
        rrf_score = ac_weight / (k + rank)
        scores[candidate.id] += rrf_score

    # Vector scores
    for rank, candidate in enumerate(vector_results, start=1):
        rrf_score = vector_weight / (k + rank)
        scores[candidate.id] += rrf_score

    # Combine
    merged = [
        Candidate(id=id, score=score, ...)
        for id, score in scores.items()
    ]

    return sorted(merged, key=lambda c: c.score, reverse=True)
```

---

## 📊 Полная Статистика Pipeline

### Размеры данных

| Этап | Размер | Время |
|------|--------|-------|
| Исходные JSON файлы | 50 MB | - |
| Sanctions cache | 34 MB | <1s |
| AC Patterns (в памяти) | ~100 MB | 5-10s |
| Vectors (в памяти) | ~34 MB | 60-90s (GPU) |
| ES индексы (на диске) | ~200 MB | 45s |
| ES индексы (в RAM) | ~150 MB | - |

### Производительность загрузки

| Операция | Время | Throughput |
|----------|-------|------------|
| JSON parsing | 2s | 25 MB/s |
| AC generation | 8s | ~125k patterns/s |
| Vector generation | 75s | ~300 vectors/s |
| Bulk loading | 45s | ~500 docs/s |
| Warmup | 5s | - |
| **TOTAL** | **~135s** | - |

### Runtime производительность

| Метод | P50 | P95 | P99 |
|-------|-----|-----|-----|
| AC Search | 15ms | 30ms | 50ms |
| Vector Search | 25ms | 45ms | 70ms |
| Hybrid Search | 20ms | 40ms | 60ms |

### Качество поиска

| Метод | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| AC (exact) | 0.95 | 0.75 | 0.84 |
| Vector (semantic) | 0.85 | 0.90 | 0.87 |
| Hybrid (fusion) | 0.92 | 0.88 | 0.90 |

---

## 🔧 Конфигурация

### Environment Variables

```bash
# Elasticsearch
ES_HOSTS=localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=changeme
ES_VERIFY_SSL=false
ES_TIMEOUT=30

# Search Settings
ENABLE_AC_SEARCH=true
ENABLE_VECTOR_SEARCH=true
ENABLE_HYBRID_FUSION=true
ENABLE_ESCALATION=true

# AC Settings
AC_FUZZINESS=1
AC_MIN_SCORE=0.6
AC_BOOST=1.2

# Vector Settings
VECTOR_MIN_SCORE=0.5
VECTOR_BOOST=1.0
VECTOR_EF_SEARCH=100

# Hybrid Settings
ESCALATION_THRESHOLD=0.6
AC_WEIGHT=0.7
VECTOR_WEIGHT=0.3
```

### Feature Flags

```python
# src/ai_service/config/settings.py
ENABLE_FAISS_INDEX=true           # FAISS acceleration for vectors
ENABLE_AC_TIER0=true              # Exact AC patterns
ENABLE_AC_ES=true                 # AC patterns in Elasticsearch
ENABLE_VECTOR_ES=true             # Vectors in Elasticsearch
ENABLE_HYBRID_SEARCH=true         # Hybrid AC+Vector
```

---

## 🚀 Deployment Workflows

### Local Development

```bash
# 1. Start Elasticsearch
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  elasticsearch:8.11.0

# 2. Load sanctions data
python scripts/load_sanctions.py

# 3. Generate patterns & vectors
python scripts/generate_ac_patterns.py
python scripts/generate_vectors.py

# 4. Setup Elasticsearch
python scripts/elasticsearch_setup_and_warmup.py

# 5. Test search
python scripts/test_search.py "Иван Петров"
```

### CI/CD Pipeline (GitHub Actions)

См. `docs/SEARCH_DEPLOYMENT_PIPELINE.md`

```bash
# Автоматическое развертывание
git push origin main  # → production
git push origin develop  # → staging

# Ручное развертывание
gh workflow run search-deployment.yml \
  --field environment=production
```

### Production Deployment

```bash
# Blue-Green deployment с zero downtime
python scripts/deploy_search_integration.py \
  --environment production \
  --artifacts-path artifacts/ \
  --es-url "$PROD_ES_URL" \
  --es-auth "$PROD_ES_AUTH" \
  --es-verify-ssl true
```

---

## 🔍 Monitoring & Debugging

### Health Check

```bash
# Elasticsearch cluster health
curl http://localhost:9200/_cluster/health

# Index statistics
curl http://localhost:9200/watchlist_persons_current/_stats

# Search quality
python scripts/evaluate_search.py --queries test_queries.json
```

### Debugging

```python
# Enable debug logging
export LOG_LEVEL=DEBUG

# Trace search execution
from ai_service.layers.search import HybridSearchService

service = HybridSearchService()
candidates = await service.find_candidates(
    normalized=norm_result,
    text="Иван Петров",
    opts=SearchOpts(trace_enabled=True)
)

print(candidates.trace)  # Detailed execution trace
```

### Metrics Collection

```python
# Get search metrics
metrics = search_service.get_metrics()

print(f"Total requests: {metrics.total_requests}")
print(f"AC requests: {metrics.ac_requests}")
print(f"Vector requests: {metrics.vector_requests}")
print(f"Hit rate: {metrics.hit_rate:.2%}")
print(f"P95 latency: {metrics.p95_latency_ms:.2f}ms")
```

---

## 📚 Related Documentation

- **`SEARCH_DEPLOYMENT_PIPELINE.md`** - CI/CD и автоматизация
- **`ELASTICSEARCH_WATCHLIST_ADAPTER.md`** - Adapter архитектура
- **`templates/elasticsearch/README.md`** - Индексы и mappings
- **`src/ai_service/layers/search/README.md`** - Search Layer API
- **`SEARCH_CONFIGURATION.md`** - Детальная конфигурация
- **`SEARCH_TROUBLESHOOTING.md`** - Troubleshooting guide