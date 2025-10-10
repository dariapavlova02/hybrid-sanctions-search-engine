# Docker Entrypoint - Финальная сводка

## ✅ Что реализовано

### 1. Автоматическая инициализация Elasticsearch

**Файл**: `scripts/docker-entrypoint.sh`

**Что делает**:
```
1. Ждёт готовности Elasticsearch (до 60s)
2. Проверяет индексы (ac_patterns + vectors)
3. Если нужно - инициализирует:
   ✅ Ищет ac_patterns_*.json в output/sanctions/
   ✅ Ищет vectors_*.json в output/sanctions/
   ✅ Создаёт оба индекса
   ✅ Загружает AC patterns (~1.1GB, ~2.7M документов)
   ✅ Загружает vectors (~206MB)
   ✅ Делает warmup запросы
4. Устанавливает ENV: ES_AC_INDEX, ES_VECTOR_INDEX
5. Запускает приложение
```

### 2. Скрипт подготовки данных

**Файл**: `scripts/prepare_sanctions_data.py`

**Создаёт**:
- ✅ `ac_patterns_YYYYMMDD_HHMMSS.json` - AC patterns для Elasticsearch
- ✅ `vectors_YYYYMMDD_HHMMSS.json` - Vector embeddings для kNN search
- ✅ `deployment_manifest.json` - Манифест деплоя
- ✅ `templates/` - Шаблоны для дополнительной обработки

**Использование**:
```bash
# Полная подготовка (AC patterns + vectors + templates)
python scripts/prepare_sanctions_data.py

# Только AC patterns (быстрее)
python scripts/prepare_sanctions_data.py --skip-vectors

# С ограничениями
python scripts/prepare_sanctions_data.py --max-patterns 50 --filter-tiers "0,1,2"
```

### 3. Deployment скрипт

**Файл**: `scripts/deploy_to_elasticsearch.py`

**Функционал**:
- ✅ Создание индексов с правильными маппингами
- ✅ Bulk load AC patterns (batch 5000)
- ✅ Bulk load vectors
- ✅ Health checks
- ✅ Warmup queries (путин, газпром, ukraine, sanctions)
- ✅ Verification

**Использование**:
```bash
# Автоматически находит последние файлы
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200

# С конкретными файлами
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --patterns-file output/sanctions/ac_patterns_20251008_143122.json \
  --vectors-file output/sanctions/vectors_20251008_143219.json \
  --create-vector-indices
```

---

## 📊 Текущее состояние

### Подготовленные данные

```bash
output/sanctions/
├── ac_patterns_20251008_143122.json   # 1.1GB - Самый свежий ✅
├── vectors_20251008_143219.json       # 206MB - Самый свежий ✅
├── deployment_manifest.json           # 792B
└── templates/                         # Дополнительные шаблоны
```

### Production индексы

```
sanctions_ac_patterns    - 2,768,827 docs - 244.8mb (green) ✅
sanctions_vectors        - 0 docs (empty) ⚠️  НУЖНО ЗАГРУЗИТЬ
```

**Проблема**: Векторный индекс пустой, векторы не загружены.

---

## 🚀 Что нужно сделать для полного деплоя

### Вариант 1: Локальная подготовка + Production deployment

```bash
# 1. Локально: Подготовить свежие данные (если нужно)
python scripts/prepare_sanctions_data.py

# 2. Скопировать на production (если нужно)
scp output/sanctions/ac_patterns_*.json root@95.217.84.234:/opt/ai-service/output/sanctions/
scp output/sanctions/vectors_*.json root@95.217.84.234:/opt/ai-service/output/sanctions/

# 3. SSH на production
ssh root@95.217.84.234

# 4. Pull изменений
cd /opt/ai-service
git pull origin main

# 5. Rebuild Docker
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Entrypoint автоматически загрузит всё!
```

### Вариант 2: Прямая загрузка векторов (быстрее)

```bash
# На production сервере:
ssh root@95.217.84.234

cd /opt/ai-service

# Загрузить векторы вручную
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --vectors-file output/sanctions/vectors_20251008_143219.json \
  --create-vector-indices
```

---

## 🔍 Проверка после деплоя

### 1. Проверить индексы

```bash
curl http://localhost:9200/_cat/indices?v

# Ожидается:
# green  open  sanctions_ac_patterns    1  0  2768827  # ✅
# green  open  sanctions_vectors        1  0  XXXXXX   # ✅ Должно быть >0
```

### 2. Проверить логи Docker

```bash
docker logs ai-service | grep -A 20 "Elasticsearch"

# Должно быть:
# ✅ Elasticsearch готов
# 🔍 Проверка индексов...
#   ✅ sanctions_ac_patterns: 2768827 документов
#   ✅ sanctions_vectors: XXXXX документов
# ✅ Все индексы готовы
```

### 3. Тестовый запрос

```bash
curl -X POST http://95.217.84.234:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Дарья ПАвлова ИНН 2839403975",
    "generate_variants": false,
    "generate_embeddings": false
  }' | jq '.decision.risk_level, .sanctioned'

# Ожидается:
# "high"    # После фикса signals
# true
```

---

## 📝 Важные детали

### Размеры файлов

```
AC patterns:  ~1.1GB  → Elasticsearch: ~245MB (compressed)
Vectors:      ~206MB  → Elasticsearch: ~XXX MB
```

### Время загрузки

```
AC patterns:  ~30-60 секунд (batch 5000)
Vectors:      ~10-20 секунд
Warmup:       ~5 секунд
Итого:        ~1-2 минуты полная инициализация
```

### Переменные окружения

```yaml
# docker-compose.yml
environment:
  - ES_HOSTS=elasticsearch:9200
  - ES_INDEX_PREFIX=sanctions        # Префикс индексов
  - ES_STARTUP_TIMEOUT=60            # Таймаут ожидания ES
  - SKIP_ES_INIT=false               # false = авто-инициализация
```

---

## ⚠️ Известные проблемы

### 1. Векторный индекс пустой

**Статус**: На production векторы не загружены

**Решение**:
```bash
# Вариант A: Rebuild Docker (entrypoint загрузит автоматически)
docker-compose down && docker-compose build && docker-compose up -d

# Вариант B: Загрузить вручную
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --vectors-file output/sanctions/vectors_20251008_143219.json \
  --create-vector-indices
```

### 2. "ПАвлова" фильтрация в signals

**Статус**: Stop words исправлены ✅, но signals_service.py всё ещё фильтрует

**Следующий шаг**: Исследовать `src/ai_service/layers/signals/signals_service.py`

---

## 🎯 Итоговый чеклист

### Elasticsearch инициализация
- ✅ Entrypoint скрипт создан
- ✅ Автоматическое ожидание ES
- ✅ Проверка индексов
- ✅ Загрузка AC patterns
- ✅ Загрузка vectors
- ✅ Warmup queries
- ✅ ENV variables согласование
- ✅ Dockerfile обновлён
- ✅ docker-compose.yml обновлён

### Данные
- ✅ AC patterns подготовлены (1.1GB)
- ✅ Vectors подготовлены (206MB)
- ✅ Deployment manifest создан
- ⏳ Векторы на production (нужно загрузить)

### Документация
- ✅ ELASTICSEARCH_DEPLOYMENT.md (полная)
- ✅ ELASTICSEARCH_FIX_SUMMARY.md (сводка)
- ✅ ENTRYPOINT_SUMMARY.md (этот файл)

---

## 🚀 Быстрый старт

### Для локальной разработки

```bash
# 1. Убедиться что данные есть
ls -lh output/sanctions/ac_patterns*.json
ls -lh output/sanctions/vectors*.json

# 2. Запустить
docker-compose up -d

# 3. Проверить логи
docker logs ai-service | head -100
```

### Для production deployment

```bash
# 1. SSH
ssh root@95.217.84.234

# 2. Pull + Rebuild
cd /opt/ai-service
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 3. Мониторинг
docker logs -f ai-service
```

Всё готово для автоматического деплоя! 🎉
