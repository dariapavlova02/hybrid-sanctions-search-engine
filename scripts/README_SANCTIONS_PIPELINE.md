# Sanctions Data Automation Pipeline

**Дата:** 03.10.2025
**Назначение:** One-click автоматизация полного цикла обновления sanctions данных

---

## 🚀 Quick Start

### Вариант 1: Интерактивный режим (рекомендуется)

```bash
# Запустить интерактивное меню
python scripts/sanctions_pipeline.py
```

Появится меню:
```
[1] 🔧 Prepare data only (AC patterns + vectors)
[2] 📤 Deploy to Elasticsearch only (use existing data)
[3] 🚀 Full pipeline (prepare + deploy)
[4] ℹ️  Show help
[5] 🚪 Exit
```

### Вариант 2: Полная автоматизация

```bash
# Полный пайплайн: подготовка + загрузка в ES
python scripts/sanctions_pipeline.py \
  --full \
  --es-host localhost:9200
```

### Вариант 3: Отдельные этапы

```bash
# Этап 1: Подготовка данных (AC patterns + vectors)
python scripts/prepare_sanctions_data.py

# Этап 2: Загрузка в Elasticsearch
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200
```

---

## 📋 Описание скриптов

### 1. `prepare_sanctions_data.py` - Подготовка данных

**Что делает:**
- ✅ Генерирует AC patterns (4 тира, high-recall)
- ✅ Генерирует векторные эмбеддинги (384-dim)
- ✅ Создаёт deployment manifest
- ✅ Валидация входных файлов

**Входные данные:**
```
src/ai_service/data/
├── sanctioned_persons.json
├── sanctioned_companies.json
└── terrorism_black_list.json
```

**Результат:**
```
output/sanctions/
├── ac_patterns_YYYYMMDD_HHMMSS.json    # AC patterns с метаданными
├── vectors_persons_*.npy                # Векторные эмбеддинги
├── vectors_companies_*.npy
└── deployment_manifest.json             # Манифест для deploy
```

**Опции:**
```bash
# Только AC patterns (без векторов, быстрее)
python scripts/prepare_sanctions_data.py --skip-vectors

# Только паттерны, без templates
python scripts/prepare_sanctions_data.py --skip-templates

# Только AC patterns (минимальный набор)
python scripts/prepare_sanctions_data.py --patterns-only

# Кастомная выходная директория
python scripts/prepare_sanctions_data.py --output-dir ./custom_output

# Лимит паттернов на сущность
python scripts/prepare_sanctions_data.py --max-patterns 100
```

---

### 2. `deploy_to_elasticsearch.py` - Загрузка в ES

**Что делает:**
- ✅ Создаёт индексы с правильными mappings
- ✅ Bulk-загружает AC patterns
- ✅ Создаёт векторные индексы (опционально)
- ✅ Warmup queries
- ✅ Health checks и валидация

**Интерактивный режим:**
```bash
python scripts/deploy_to_elasticsearch.py
```

Скрипт попросит ввести Elasticsearch host:
```
Enter Elasticsearch host (examples):
  • localhost:9200        (local Docker)
  • 192.168.1.100:9200    (remote server)
  • es.example.com:9200   (production)

Elasticsearch host: _
```

**Автоматический режим:**
```bash
# Docker localhost
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200

# Удалённый сервер
python scripts/deploy_to_elasticsearch.py --es-host 192.168.1.100:9200

# Создать и векторные индексы
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --create-vector-indices

# Указать конкретный файл паттернов
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --patterns-file output/sanctions/ac_patterns_20251003_120000.json

# Пропустить warmup queries
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --skip-warmup
```

**Создаваемые индексы:**
```
sanctions_ac_patterns           # AC patterns (обязательный)
sanctions_vectors_persons       # Векторы персон (опц.)
sanctions_vectors_companies     # Векторы компаний (опц.)
sanctions_vectors_terrorism     # Векторы терроризм (опц.)
```

---

### 3. `sanctions_pipeline.py` - Главный wrapper

**Что делает:**
- 🎯 Интерактивное меню для выбора этапов
- 🚀 Полная автоматизация (prepare + deploy)
- 📊 Pretty-форматированный вывод
- ⚙️ Гибкая конфигурация

**Интерактивный режим:**
```bash
python scripts/sanctions_pipeline.py
```

**Автоматизированные режимы:**
```bash
# Полный пайплайн
python scripts/sanctions_pipeline.py --full --es-host localhost:9200

# Только подготовка
python scripts/sanctions_pipeline.py --prepare-only

# Только подготовка, без векторов
python scripts/sanctions_pipeline.py --prepare-only --skip-vectors

# Только deploy
python scripts/sanctions_pipeline.py --deploy-only --es-host localhost:9200
```

---

## 🔄 Типичные Сценарии

### Сценарий 1: Обновление sanctions списков

```bash
# 1. Заменить JSON файлы
cp /path/to/new/sanctioned_persons.json src/ai_service/data/
cp /path/to/new/sanctioned_companies.json src/ai_service/data/
cp /path/to/new/terrorism_black_list.json src/ai_service/data/

# 2. Запустить полный пайплайн
python scripts/sanctions_pipeline.py --full --es-host localhost:9200

# Или интерактивно
python scripts/sanctions_pipeline.py
# → выбрать [3] Full pipeline
```

### Сценарий 2: Быстрое тестирование (без векторов)

```bash
# Подготовка без векторов (быстрее)
python scripts/prepare_sanctions_data.py --skip-vectors

# Загрузка в тестовый ES
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200
```

### Сценарий 3: Production deployment

```bash
# 1. Подготовка с полным набором
python scripts/prepare_sanctions_data.py

# 2. Загрузка на production ES
python scripts/deploy_to_elasticsearch.py \
  --es-host production.es.example.com:9200 \
  --create-vector-indices
```

### Сценарий 4: Только пересоздать индексы

```bash
# Использовать ранее подготовленные данные
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --patterns-file output/sanctions/ac_patterns_20251003_120000.json
```

---

## 📊 Что генерируется

### AC Patterns JSON

```json
{
  "metadata": {
    "generated_at": "2025-10-03T12:00:00",
    "total_patterns": 50000,
    "sources": {
      "persons": 13192,
      "companies": 5821,
      "terrorism": 1024
    },
    "tier_distribution": {
      "0": 10000,   // Exact matches
      "1": 15000,   // High recall
      "2": 15000,   // Medium recall
      "3": 10000    // Low recall
    }
  },
  "patterns": [
    {
      "pattern": "путин владимир владимирович",
      "tier": 0,
      "confidence": 1.0,
      "entity_id": 12345,
      "entity_type": "person",
      "original_name": "Путин Владимир Владимирович",
      "variations": [...]
    }
  ]
}
```

### Deployment Manifest

```json
{
  "created_at": "2025-10-03T12:00:00",
  "version": "1.0",
  "input_files": {
    "persons": "src/ai_service/data/sanctioned_persons.json",
    "companies": "src/ai_service/data/sanctioned_companies.json",
    "terrorism": "src/ai_service/data/terrorism_black_list.json"
  },
  "generated_files": {
    "ac_patterns": "output/sanctions/ac_patterns_20251003_120000.json",
    "vectors": {
      "persons": "output/sanctions/vectors_persons_*.npy",
      "companies": "output/sanctions/vectors_companies_*.npy"
    }
  },
  "elasticsearch_config": {
    "index_prefix": "sanctions",
    "suggested_indices": [
      "sanctions_ac_patterns",
      "sanctions_vectors_persons",
      "sanctions_vectors_companies",
      "sanctions_vectors_terrorism"
    ]
  }
}
```

---

## 🔍 Верификация

### Проверка подготовленных данных

```bash
# Количество паттернов
jq '.patterns | length' output/sanctions/ac_patterns_*.json

# Распределение по tier'ам
jq '.patterns | group_by(.tier) | map({tier: .[0].tier, count: length})' \
  output/sanctions/ac_patterns_*.json

# Примеры паттернов
jq '.patterns[] | select(.original_name | contains("Путин"))' \
  output/sanctions/ac_patterns_*.json
```

### Проверка в Elasticsearch

```bash
# Количество документов
curl -X GET "localhost:9200/sanctions_ac_patterns/_count?pretty"

# Примеры документов
curl -X GET "localhost:9200/sanctions_ac_patterns/_search?pretty&size=5"

# Поиск по паттерну
curl -X GET "localhost:9200/sanctions_ac_patterns/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {
        "pattern": "путин"
      }
    }
  }'
```

---

## ⚙️ Конфигурация

### Environment Variables (опционально)

```bash
# .env или export
export ES_HOST=localhost:9200
export SANCTIONS_DATA_DIR=src/ai_service/data
export SANCTIONS_OUTPUT_DIR=output/sanctions
```

### Настройка лимитов AC patterns

```python
# В prepare_sanctions_data.py можно настроить
--max-patterns 50          # Максимум паттернов на сущность
--tier-limits "0:5,1:10,2:15,3:50"  # Лимиты по tier'ам
```

---

## 🚨 Troubleshooting

### Ошибка: "Cannot connect to Elasticsearch"

```bash
# Проверить, что ES запущен
curl http://localhost:9200/_cluster/health

# Проверить Docker container
docker ps | grep elasticsearch
```

### Ошибка: "File not found: sanctioned_persons.json"

```bash
# Проверить наличие файлов
ls -lh src/ai_service/data/sanctioned_*.json

# Указать кастомную директорию
python scripts/prepare_sanctions_data.py \
  --data-dir /path/to/custom/data
```

### Ошибка: "Index already exists"

При повторном запуске deploy скрипт спросит:
```
⚠️  Index already exists
Delete and recreate sanctions_ac_patterns? (y/n):
```

Ответить `y` для пересоздания или `n` для сохранения.

### Медленная генерация векторов

```bash
# Пропустить векторы (только AC patterns)
python scripts/prepare_sanctions_data.py --skip-vectors
```

---

## 📝 Checklist обновления sanctions

- [ ] Бэкап текущих JSON файлов
- [ ] Валидация новых JSON файлов
- [ ] Замена файлов в `src/ai_service/data/`
- [ ] Запуск `prepare_sanctions_data.py`
- [ ] Проверка сгенерированных паттернов (jq)
- [ ] Запуск `deploy_to_elasticsearch.py`
- [ ] Верификация индексов в ES (curl)
- [ ] Тестовые поисковые запросы
- [ ] Обновление документации (даты, статистика)

---

## 🔗 Связанные документы

- `docs/SANCTIONS_UPDATE_WORKFLOW.md` - Полный workflow обновления
- `docs/DATA_PIPELINE.md` - Архитектура data pipeline
- `scripts/export_high_recall_ac_patterns.py` - Legacy генератор (можно удалить)

---

## ✅ Итого

**Главное преимущество:** One-click automation вместо ручного 5-step workflow.

**Было:**
```bash
# 5 ручных шагов
1. python scripts/export_high_recall_ac_patterns.py ...
2. python scripts/generate_vectors.py ...
3. python scripts/load_ac_patterns.py ...
4. Ручная проверка
5. Warmup queries
```

**Стало:**
```bash
# 1 команда
python scripts/sanctions_pipeline.py --full --es-host localhost:9200
```

**Экономия времени:** ~15 минут → ~2 минуты (интерактивно) или ~30 секунд (автомат).
