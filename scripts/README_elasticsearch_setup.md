# Elasticsearch Setup and Warmup Script

Асинхронный Python-скрипт для создания индексов Elasticsearch и их прогрева.

## Возможности

- ✅ Создание component template с анализаторами и нормалайзерами
- ✅ Создание index templates для людей и организаций
- ✅ Создание индексов с алиасами `watchlist_persons_current`, `watchlist_orgs_current`
- ✅ Health check кластера
- ✅ Прогрев индексов типовыми запросами (AC + Vector поиск)
- ✅ Логирование длительностей и ошибок
- ✅ Параметризация через environment variables
- ✅ Четкие exit codes

## Установка

```bash
# Установка зависимостей
pip install -r scripts/requirements_elasticsearch.txt

# Или напрямую
pip install httpx>=0.24.0
```

## Использование

### Базовое использование

```bash
# Локальный Elasticsearch
python scripts/elasticsearch_setup_and_warmup.py

# С аутентификацией
ES_URL=http://localhost:9200 \
ES_USER=elastic \
ES_PASS=password \
python scripts/elasticsearch_setup_and_warmup.py
```

### Environment Variables

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `ES_URL` | URL Elasticsearch | `http://localhost:9200` |
| `ES_USER` | Имя пользователя | - |
| `ES_PASS` | Пароль | - |
| `ES_VERIFY_SSL` | Проверять SSL сертификаты | `true` |
| `ES_TIMEOUT` | Таймаут запросов (сек) | `30` |

### Примеры

```bash
# Production с SSL
ES_URL=https://elasticsearch.company.com:9200 \
ES_USER=elastic \
ES_PASS=secure_password \
ES_VERIFY_SSL=true \
python scripts/elasticsearch_setup_and_warmup.py

# Development без SSL
ES_URL=http://localhost:9200 \
ES_VERIFY_SSL=false \
python scripts/elasticsearch_setup_and_warmup.py

# С кастомным таймаутом
ES_URL=http://localhost:9200 \
ES_TIMEOUT=60 \
python scripts/elasticsearch_setup_and_warmup.py
```

## Что создается

### 1. Component Template
- **Имя**: `watchlist_analyzers`
- **Содержит**: Анализаторы, нормалайзеры, фильтры
- **Анализаторы**:
  - `icu_text_analyzer` - полнотекстовый поиск
  - `shingle_analyzer` - фразовый поиск
  - `char_ngram_analyzer` - нечеткий поиск
- **Нормалайзеры**:
  - `case_insensitive_normalizer` - без учета регистра

### 2. Index Templates
- **watchlist_persons_v1** - для физических лиц
- **watchlist_orgs_v1** - для организаций

### 3. Индексы с алиасами
- **watchlist_persons_v1_001** → `watchlist_persons_current`
- **watchlist_orgs_v1_001** → `watchlist_orgs_current`

### 4. Поля индексов
- `entity_id` - уникальный ID
- `entity_type` - тип сущности (person/org)
- `normalized_name` - нормализованное имя
- `aliases` - алиасы
- `name_text` - полнотекстовый поиск
- `name_ngrams` - n-grams для нечеткого поиска
- `name_vector` - dense вектор (384 dims)
- `meta` - метаданные

## Прогрев

Скрипт выполняет следующие типы запросов для прогрева:

### AC (Точный) поиск
- Exact match по `normalized_name`
- Fuzzy match с fuzziness=1,2
- Phrase search с shingles
- N-gram search

### Vector (kNN) поиск
- kNN поиск по `name_vector`
- Mock векторы 384 измерения
- Cosine similarity

## Exit Codes

| Код | Описание |
|-----|----------|
| `0` | Успешное выполнение |
| `1` | Ошибка настройки |
| `130` | Прерывание пользователем (Ctrl+C) |

## Логирование

Скрипт выводит подробные логи:
- Временные метки
- Уровни логирования (INFO, WARN, ERROR)
- Длительности операций
- Детали ошибок

Пример вывода:
```
2024-01-15 10:30:15 [ES-SETUP] [INFO] Checking Elasticsearch health...
2024-01-15 10:30:15 [ES-SETUP] [INFO] Cluster status: green
2024-01-15 10:30:15 [ES-SETUP] [INFO] Creating component template: watchlist_analyzers
2024-01-15 10:30:16 [ES-SETUP] [INFO] Component template created successfully
...
2024-01-15 10:30:25 [ES-SETUP] [INFO] Setup completed successfully in 10.45 seconds
```

## Требования

- Python 3.8+
- httpx >= 0.24.0
- Elasticsearch 8.0+
- ICU Analysis plugin (обычно включен)

## Интеграция с AI Service

Этот скрипт подготавливает Elasticsearch для слоя поиска (Layer 9):

1. **ElasticsearchACAdapter** использует AC поля для точного поиска
2. **ElasticsearchVectorAdapter** использует vector поля для kNN поиска
3. **HybridSearchService** комбинирует оба типа поиска

## Troubleshooting

### Ошибка подключения
```
[ERROR] Request failed: ConnectError
```
**Решение**: Проверьте ES_URL и доступность Elasticsearch

### Ошибка аутентификации
```
[ERROR] HTTP 401: Unauthorized
```
**Решение**: Проверьте ES_USER и ES_PASS

### Ошибка SSL
```
[ERROR] Request failed: SSL verification failed
```
**Решение**: Установите ES_VERIFY_SSL=false для development

### Таймаут
```
[ERROR] Request failed: ReadTimeout
```
**Решение**: Увеличьте ES_TIMEOUT
