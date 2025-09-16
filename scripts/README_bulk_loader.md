# Bulk Loader for Sanctioned Entities

Утилита для массовой загрузки санкционированных лиц и организаций в Elasticsearch с автоматической генерацией эмбеддингов.

## Возможности

- ✅ **Поддержка форматов**: JSONL и YAML
- ✅ **Автоматическая генерация эмбеддингов** для сущностей без `name_vector`
- ✅ **Bulk операции** с ретраями и exponential backoff
- ✅ **Идемпотентность** по `entity_id`
- ✅ **Метрики**: количество апсертов, P95 латентность, кэш-хиты
- ✅ **CLI интерфейс** с гибкими флагами
- ✅ **Поддержка алиасов** и перестроения индексов

## Установка

```bash
# Установка зависимостей
pip install httpx pyyaml pydantic

# Или из requirements
pip install -r scripts/requirements_elasticsearch.txt
```

## Использование

### Базовое использование

```bash
# Загрузка лиц из JSONL
python scripts/bulk_loader.py --input entities.jsonl --entity-type person

# Загрузка организаций из YAML
python scripts/bulk_loader.py --input entities.yaml --entity-type org

# С upsert операциями
python scripts/bulk_loader.py --input entities.jsonl --entity-type person --upsert

# С перестроением алиаса
python scripts/bulk_loader.py --input entities.jsonl --entity-type person --rebuild-alias
```

### Продвинутые опции

```bash
# Настройка batch size и flush interval
python scripts/bulk_loader.py \
  --input entities.jsonl \
  --entity-type person \
  --batch-size 2000 \
  --flush-interval 0.5

# С аутентификацией Elasticsearch
python scripts/bulk_loader.py \
  --input entities.jsonl \
  --entity-type person \
  --es-url https://elasticsearch.company.com:9200 \
  --es-user elastic \
  --es-pass password

# С кастомной моделью эмбеддингов
python scripts/bulk_loader.py \
  --input entities.jsonl \
  --entity-type person \
  --embedding-model sentence-transformers/all-mpnet-base-v2
```

## Формат данных

### JSONL формат

```jsonl
{"entity_id": "person_001", "entity_type": "person", "normalized_name": "Иван Петров", "aliases": ["И. Петров", "Ivan Petrov"], "dob": "1980-05-15", "country": "RU", "meta": {"source": "sanctions", "list": "eu_sanctions"}}
{"entity_id": "org_001", "entity_type": "org", "normalized_name": "ООО Газпром", "aliases": ["Газпром", "Gazprom"], "country": "RU", "meta": {"source": "sanctions", "list": "eu_sanctions", "industry": "energy"}}
```

### YAML формат

```yaml
- entity_id: "person_001"
  entity_type: "person"
  normalized_name: "Иван Петров"
  aliases: ["И. Петров", "Ivan Petrov"]
  dob: "1980-05-15"
  country: "RU"
  meta:
    source: "sanctions"
    list: "eu_sanctions"

- entity_id: "org_001"
  entity_type: "org"
  normalized_name: "ООО Газпром"
  aliases: ["Газпром", "Gazprom"]
  country: "RU"
  meta:
    source: "sanctions"
    list: "eu_sanctions"
    industry: "energy"
```

### Обязательные поля

- `entity_id` - уникальный идентификатор сущности
- `entity_type` - тип сущности (`person` или `org`)
- `normalized_name` - нормализованное имя

### Опциональные поля

- `aliases` - список алиасов (массив строк)
- `dob` - дата рождения (строка в формате YYYY-MM-DD)
- `country` - код страны (строка)
- `meta` - метаданные (объект)
- `name_vector` - вектор эмбеддинга (массив из 384 чисел)

## CLI Параметры

### Обязательные параметры

| Параметр | Описание | Пример |
|----------|----------|--------|
| `--input`, `-i` | Путь к входному файлу | `--input entities.jsonl` |
| `--entity-type`, `-t` | Тип сущности | `--entity-type person` |

### Опциональные параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--upsert` | Использовать upsert операции | `False` |
| `--rebuild-alias` | Перестроить алиас после загрузки | `False` |
| `--batch-size` | Размер батча для bulk операций | `1000` |
| `--flush-interval` | Интервал между батчами (сек) | `1.0` |

### Конфигурация Elasticsearch

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--es-url` | URL Elasticsearch | `http://localhost:9200` |
| `--es-user` | Имя пользователя | - |
| `--es-pass` | Пароль | - |
| `--es-verify-ssl` | Проверять SSL сертификаты | `True` |
| `--es-timeout` | Таймаут запросов (сек) | `30` |

### Конфигурация эмбеддингов

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--embedding-model` | Модель для эмбеддингов | `sentence-transformers/all-MiniLM-L6-v2` |

## Environment Variables

```bash
# Elasticsearch
export ES_URL="http://localhost:9200"
export ES_USER="elastic"
export ES_PASS="password"
export ES_VERIFY_SSL="true"
export ES_TIMEOUT="30"

# Embeddings
export EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
```

## Метрики

Утилита выводит подробные метрики:

```
============================================================
BULK LOADER METRICS
============================================================
Total processed: 1000
Successful upserts: 995
Failed upserts: 5
Success rate: 99.5%
Throughput: 50.2 records/sec
Embeddings generated: 800
Embedding cache hits: 200
Cache hit rate: 20.0%
Embedding P95 latency: 0.045s
Bulk operations: 10
Bulk errors: 0
============================================================
```

### Описание метрик

- **Total processed** - общее количество обработанных записей
- **Successful upserts** - успешные upsert операции
- **Failed upserts** - неудачные upsert операции
- **Success rate** - процент успешных операций
- **Throughput** - скорость обработки (записей/сек)
- **Embeddings generated** - количество сгенерированных эмбеддингов
- **Embedding cache hits** - количество кэш-хитов для эмбеддингов
- **Cache hit rate** - процент кэш-хитов
- **Embedding P95 latency** - 95-й перцентиль латентности генерации эмбеддингов
- **Bulk operations** - количество bulk операций
- **Bulk errors** - количество ошибок bulk операций

## Примеры использования

### Загрузка санкционированных лиц

```bash
# Загрузка из EU санкций
python scripts/bulk_loader.py \
  --input eu_sanctions_persons.jsonl \
  --entity-type person \
  --upsert \
  --batch-size 2000

# Загрузка из US санкций
python scripts/bulk_loader.py \
  --input us_sanctions_persons.yaml \
  --entity-type person \
  --upsert \
  --rebuild-alias
```

### Загрузка организаций

```bash
# Загрузка компаний
python scripts/bulk_loader.py \
  --input companies.jsonl \
  --entity-type org \
  --upsert \
  --batch-size 1000 \
  --flush-interval 0.5
```

### Массовая загрузка с метриками

```bash
# Загрузка большого объема данных
python scripts/bulk_loader.py \
  --input large_dataset.jsonl \
  --entity-type person \
  --upsert \
  --batch-size 5000 \
  --flush-interval 2.0 \
  --es-timeout 60
```

## Интеграция с AI Service

Утилита интегрируется с 9-слойной архитектурой AI Service:

1. **Слой 9 (Search)** - использует загруженные данные для поиска
2. **ElasticsearchACAdapter** - точный поиск по `normalized_name` и `aliases`
3. **ElasticsearchVectorAdapter** - векторный поиск по `name_vector`
4. **HybridSearchService** - комбинированный поиск

## Troubleshooting

### Ошибка подключения к Elasticsearch

```
[ERROR] Request failed: ConnectError
```

**Решение**: Проверьте ES_URL и доступность Elasticsearch

### Ошибка аутентификации

```
[ERROR] HTTP 401: Unauthorized
```

**Решение**: Проверьте ES_USER и ES_PASS

### Ошибка формата данных

```
[ERROR] Missing required field: entity_id
```

**Решение**: Проверьте формат входного файла

### Медленная генерация эмбеддингов

```
[WARN] Embedding generation is slow
```

**Решение**: 
- Уменьшите batch_size
- Используйте более быструю модель эмбеддингов
- Включите кэширование

### Ошибки bulk операций

```
[ERROR] Bulk request failed with status 413
```

**Решение**:
- Уменьшите batch_size
- Увеличьте ES_TIMEOUT
- Проверьте размер документов

## Тестирование

```bash
# Запуск тестов
python scripts/test_bulk_loader.py

# Тест с sample данными
python scripts/bulk_loader.py --input scripts/sample_entities.jsonl --entity-type person --upsert
```

## Производительность

### Рекомендуемые настройки

| Размер данных | batch_size | flush_interval | Ожидаемая скорость |
|---------------|------------|----------------|-------------------|
| < 1K записей | 100 | 0.1 | 100+ записей/сек |
| 1K-10K записей | 1000 | 1.0 | 50+ записей/сек |
| 10K-100K записей | 2000 | 2.0 | 30+ записей/сек |
| > 100K записей | 5000 | 5.0 | 20+ записей/сек |

### Оптимизация

1. **Увеличьте batch_size** для больших объемов
2. **Уменьшите flush_interval** для быстрой загрузки
3. **Используйте кэширование** для повторяющихся эмбеддингов
4. **Настройте Elasticsearch** для bulk операций

## Безопасность

- Используйте HTTPS для production
- Настройте аутентификацию
- Ограничьте доступ к Elasticsearch
- Регулярно обновляйте зависимости
