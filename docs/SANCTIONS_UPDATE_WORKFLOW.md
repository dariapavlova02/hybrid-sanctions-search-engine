# Sanctions Data Update Workflow

**Дата:** 03.10.2025
**Цель:** Инструкция по обновлению sanctions данных и регенерации паттернов

---

## 🎯 Где заменять файлы

### ✅ ПРАВИЛЬНОЕ место (используется всеми скриптами):

```
src/ai_service/data/
├── sanctioned_persons.json      ← ЗАМЕНЯТЬ ЗДЕСЬ
├── sanctioned_companies.json    ← ЗАМЕНЯТЬ ЗДЕСЬ
└── terrorism_black_list.json    ← ЗАМЕНЯТЬ ЗДЕСЬ
```

### ❌ НЕправильное место (дубликаты, будем удалять):

```
data/sanctions/  ← НЕ ТРОГАТЬ (устарело, дубли)
```

---

## 📋 Workflow обновления данных

### Шаг 1: Замена исходных файлов

```bash
# 1. Сделать бэкап текущих файлов
cp src/ai_service/data/sanctioned_persons.json src/ai_service/data/sanctioned_persons.json.backup
cp src/ai_service/data/sanctioned_companies.json src/ai_service/data/sanctioned_companies.json.backup
cp src/ai_service/data/terrorism_black_list.json src/ai_service/data/terrorism_black_list.json.backup

# 2. Заменить новыми файлами
cp /path/to/new/sanctioned_persons.json src/ai_service/data/
cp /path/to/new/sanctioned_companies.json src/ai_service/data/
cp /path/to/new/terrorism_black_list.json src/ai_service/data/
```

### Шаг 2: Генерация AC паттернов (High-Recall)

```bash
# Генерировать паттерны из новых данных
python scripts/export_high_recall_ac_patterns.py \
  --output high_recall_ac_patterns.json \
  --persons-file src/ai_service/data/sanctioned_persons.json \
  --companies-file src/ai_service/data/sanctioned_companies.json \
  --terrorism-file src/ai_service/data/terrorism_black_list.json \
  --verbose

# Результат: high_recall_ac_patterns.json
# Содержит паттерны для Aho-Corasick поиска (4 tier'а)
```

**Параметры:**
- `--tier-limits` - лимиты на паттерны по tier'ам (например: `0:5,1:10,2:15,3:50`)
- `--max-patterns-per-entity` - максимум паттернов на сущность (по умолчанию: 50)
- `--filter-tiers` - только определенные tier'ы (например: `0,1,2`)
- `--sample-size` - для тестирования на N сущностях

### Шаг 3: Генерация векторных эмбеддингов

```bash
# Генерировать векторные представления
python scripts/generate_vectors.py \
  --input src/ai_service/data/sanctioned_persons.json \
  --output vectors_persons.npy \
  --model-name sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

python scripts/generate_vectors.py \
  --input src/ai_service/data/sanctioned_companies.json \
  --output vectors_companies.npy

# Результат: vectors_*.npy файлы с эмбеддингами
```

### Шаг 4: Загрузка в Elasticsearch

```bash
# Загрузить AC паттерны в Elasticsearch
python scripts/load_ac_patterns.py \
  --patterns-file high_recall_ac_patterns.json \
  --index-name sanctions_ac_patterns \
  --es-host localhost:9200

# Альтернатива: использовать bulk_loader
python scripts/bulk_loader.py \
  --data-dir src/ai_service/data \
  --index-name sanctions \
  --batch-size 1000
```

### Шаг 5: Генерация templates (опционально)

```bash
# Если нужны templates для дополнительной обработки
python src/ai_service/scripts/build_templates.py

# Результат: templates/ директория с:
# - sanctioned_persons_templates.json
# - sanctioned_companies_templates.json
# - terrorism_black_list_templates.json
# - aho_corasick_patterns.txt
# - processing_statistics.json
```

---

## 🔄 Полный Pipeline (автоматизация)

### Вариант A: Ручной запуск (step-by-step)

```bash
#!/bin/bash
# update_sanctions_pipeline.sh

set -e  # Exit on error

echo "=== Sanctions Data Update Pipeline ==="
echo ""

# 1. Backup
echo "1. Creating backups..."
cp src/ai_service/data/sanctioned_persons.json src/ai_service/data/sanctioned_persons.json.backup
cp src/ai_service/data/sanctioned_companies.json src/ai_service/data/sanctioned_companies.json.backup
cp src/ai_service/data/terrorism_black_list.json src/ai_service/data/terrorism_black_list.json.backup

# 2. Copy new files
echo "2. Copying new sanctions files..."
# cp /path/to/new/sanctioned_persons.json src/ai_service/data/
# cp /path/to/new/sanctioned_companies.json src/ai_service/data/
# cp /path/to/new/terrorism_black_list.json src/ai_service/data/

# 3. Generate AC patterns
echo "3. Generating AC patterns..."
python scripts/export_high_recall_ac_patterns.py \
  --output output/high_recall_ac_patterns_$(date +%Y%m%d).json \
  --verbose

# 4. Generate vectors
echo "4. Generating vector embeddings..."
python scripts/generate_vectors.py \
  --input src/ai_service/data/sanctioned_persons.json \
  --output output/vectors_persons_$(date +%Y%m%d).npy

python scripts/generate_vectors.py \
  --input src/ai_service/data/sanctioned_companies.json \
  --output output/vectors_companies_$(date +%Y%m%d).npy

# 5. Load to Elasticsearch
echo "5. Loading to Elasticsearch..."
python scripts/load_ac_patterns.py \
  --patterns-file output/high_recall_ac_patterns_$(date +%Y%m%d).json \
  --index-name sanctions_ac_patterns_$(date +%Y%m%d)

echo ""
echo "=== Pipeline completed successfully ==="
```

### Вариант B: Через API (для production)

```bash
# Upload через API endpoint
python scripts/upload_data_via_api.py \
  --api-url http://localhost:8000/api/admin/upload-sanctions \
  --persons-file src/ai_service/data/sanctioned_persons.json \
  --companies-file src/ai_service/data/sanctioned_companies.json \
  --terrorism-file src/ai_service/data/terrorism_black_list.json \
  --api-key YOUR_API_KEY

# Или через shell скрипт
./scripts/upload_via_api.sh \
  --env production \
  --data-dir src/ai_service/data
```

---

## 🔍 Верификация обновления

### Проверка AC паттернов

```bash
# Проверить количество паттернов
jq '.patterns | length' high_recall_ac_patterns.json

# Проверить распределение по tier'ам
jq '.patterns | group_by(.tier) | map({tier: .[0].tier, count: length})' high_recall_ac_patterns.json

# Проверить пример паттернов для конкретного имени
jq '.patterns[] | select(.original_name | contains("Путин"))' high_recall_ac_patterns.json
```

### Проверка в Elasticsearch

```bash
# Проверить загруженные данные
curl -X GET "localhost:9200/sanctions_ac_patterns/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"size": 10}'

# Проверить количество документов
curl -X GET "localhost:9200/sanctions_ac_patterns/_count?pretty"

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

### Проверка векторов

```python
import numpy as np

# Загрузить векторы
vectors = np.load('vectors_persons.npy')

print(f"Shape: {vectors.shape}")
print(f"Dimension: {vectors.shape[1]}")  # Должно быть 384 для MiniLM
print(f"Count: {vectors.shape[0]}")
```

---

## 📊 Структура генерируемых файлов

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
      "0": 10000,
      "1": 15000,
      "2": 15000,
      "3": 10000
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
      "variations": ["putin vladimir vladimirovich", "путін володимир..."]
    },
    ...
  ]
}
```

### Templates Output

```
data/templates/
├── sanctioned_persons_templates.json
├── sanctioned_companies_templates.json
├── terrorism_black_list_templates.json
├── all_templates.json
├── aho_corasick_patterns.txt            # Для прямой загрузки в AC
└── processing_statistics.json
```

---

## ⚙️ Конфигурация

### Environment Variables

```bash
# .env или export
export ES_HOST=localhost:9200
export ES_INDEX_PREFIX=sanctions
export VECTOR_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
export AC_TIER_LIMITS="0:5,1:10,2:15,3:50"
export MAX_PATTERNS_PER_ENTITY=50
```

### Config файл (config/sanctions_update.yaml)

```yaml
sources:
  persons: src/ai_service/data/sanctioned_persons.json
  companies: src/ai_service/data/sanctioned_companies.json
  terrorism: src/ai_service/data/terrorism_black_list.json

output:
  patterns: output/patterns/
  vectors: output/vectors/
  templates: data/templates/

elasticsearch:
  host: localhost:9200
  index_prefix: sanctions
  batch_size: 1000

ac_patterns:
  tier_limits:
    tier_0: 5
    tier_1: 10
    tier_2: 15
    tier_3: 50
  max_per_entity: 50
  filter_tiers: [0, 1, 2, 3]

vectors:
  model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  dimension: 384
  batch_size: 32
```

---

## 🚨 Важные замечания

### ⚠️ НЕ заменять в data/sanctions/

```bash
# ❌ НЕПРАВИЛЬНО (устаревшее место):
cp new_file.json data/sanctions/sanctioned_persons.json

# ✅ ПРАВИЛЬНО (источник для всех скриптов):
cp new_file.json src/ai_service/data/sanctioned_persons.json
```

### ⚠️ Формат входных данных

**Ожидаемая структура JSON:**

```json
// sanctioned_persons.json
[
  {
    "id": 1,
    "person_id": 12345,
    "name": "Путин Владимир Владимирович",
    "name_ru": "Путин Владимир Владимирович",
    "name_en": "Putin Vladimir Vladimirovich",
    "birthdate": "1952-10-07",
    "itn": "...",
    ...
  },
  ...
]

// sanctioned_companies.json
[
  {
    "id": 1,
    "name": "ООО \"Газпром\"",
    "name_ru": "...",
    "name_en": "...",
    ...
  },
  ...
]
```

### ⚠️ Валидация перед обновлением

```python
# validate_sanctions.py
import json

def validate_sanctions_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Проверки
    assert isinstance(data, list), "Must be array"
    assert len(data) > 0, "Empty data"
    assert all('id' in item for item in data), "Missing id field"
    assert all('name' in item for item in data), "Missing name field"

    print(f"✅ {filepath}: {len(data)} records validated")

# Запуск
validate_sanctions_file('src/ai_service/data/sanctioned_persons.json')
```

---

## 📝 Checklist обновления

- [ ] Бэкап текущих файлов
- [ ] Валидация новых JSON файлов
- [ ] Замена файлов в `src/ai_service/data/`
- [ ] Генерация AC паттернов
- [ ] Генерация векторных эмбеддингов
- [ ] Загрузка в Elasticsearch
- [ ] Верификация в ES (count, sample search)
- [ ] Проверка через API тестовых запросов
- [ ] Обновление документации (даты, статистика)
- [ ] Коммит изменений в git (если нужно)

---

## 🔗 Связанные файлы

**Скрипты:**
- `scripts/export_high_recall_ac_patterns.py` - AC паттерны
- `scripts/generate_vectors.py` - Векторизация
- `scripts/load_ac_patterns.py` - Загрузка в ES
- `scripts/bulk_loader.py` - Bulk загрузка
- `scripts/upload_data_via_api.py` - API upload
- `src/ai_service/scripts/build_templates.py` - Templates

**Данные:**
- `src/ai_service/data/sanctioned_persons.json` ← **ИСТОЧНИК**
- `src/ai_service/data/sanctioned_companies.json` ← **ИСТОЧНИК**
- `src/ai_service/data/terrorism_black_list.json` ← **ИСТОЧНИК**

**Конфигурация:**
- `config/sanctions_update.yaml` (опционально)
- `.env` - environment variables

---

## ✅ Итого

**Главное правило:**
> **Всегда заменяй файлы в `src/ai_service/data/`** — это единственный источник для всех скриптов генерации паттернов, векторов и загрузки данных.

**Workflow:**
1. Замена → 2. AC паттерны → 3. Векторы → 4. Elasticsearch → 5. Проверка
