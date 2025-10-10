# Автоматическая инициализация Elasticsearch

## Обзор

Начиная с этой версии, AI Service автоматически инициализирует Elasticsearch при запуске Docker контейнера. Больше не требуется ручных манипуляций с индексами.

## Как это работает

### 1. Последовательность запуска

```
Docker up → Ожидание Elasticsearch → Проверка индексов → Инициализация (если нужно) → Запуск сервиса
```

### 2. Entrypoint Script

**Файл**: `scripts/docker-entrypoint.sh`

**Что делает**:
1. Ждёт готовности Elasticsearch (с таймаутом)
2. Проверяет существование индексов
3. Если индексы пусты/отсутствуют - автоматически инициализирует:
   - Создаёт индексы с правильными маппингами
   - Загружает данные из `output/sanctions/` (если есть)
   - Или создаёт пустые индексы (если данных нет)
4. Устанавливает переменные окружения для соответствия индексов
5. Запускает приложение

### 3. Согласование имён индексов

**Проблема** (было):
- Deployment script создавал: `sanctions_ac_patterns`, `sanctions_vectors`
- Код ожидал: `ac_patterns`, `vectors`
- Результат: 404 ошибки при поиске

**Решение** (стало):
- Deployment script создаёт: `{PREFIX}_ac_patterns`, `{PREFIX}_vectors`
- Entrypoint устанавливает: `ES_AC_INDEX={PREFIX}_ac_patterns`, `ES_VECTOR_INDEX={PREFIX}_vectors`
- Код читает из env: `ES_AC_INDEX`, `ES_VECTOR_INDEX`
- Результат: полное согласование ✅

## Переменные окружения

### Обязательные

```yaml
ES_HOSTS: "elasticsearch:9200"  # Адрес Elasticsearch
```

### Опциональные

```yaml
ES_INDEX_PREFIX: "sanctions"       # Префикс имён индексов (default: sanctions)
ES_STARTUP_TIMEOUT: 60             # Таймаут ожидания ES (default: 60s)
SKIP_ES_INIT: false                # Пропустить инициализацию (default: false)
```

### Автоматически устанавливаемые

```yaml
ES_AC_INDEX: "{PREFIX}_ac_patterns"    # Устанавливается entrypoint
ES_VECTOR_INDEX: "{PREFIX}_vectors"    # Устанавливается entrypoint
```

## Использование

### Вариант 1: С данными (полная инициализация)

```bash
# 1. Подготовить данные
python scripts/prepare_sanctions_data.py

# 2. Запустить Docker
docker-compose up -d

# Entrypoint автоматически:
# - Найдёт output/sanctions/ac_patterns_*.json
# - Создаст индексы
# - Загрузит ~2.7M документов
```

**Логи при старте**:
```
==================================================
AI Service - Docker Entrypoint
==================================================

Конфигурация:
  Elasticsearch: elasticsearch:9200
  Index Prefix: sanctions
  Skip Init: false

🔄 Ожидание готовности Elasticsearch...
✅ Elasticsearch готов

🔍 Проверка индексов...
  ⚠️  sanctions_ac_patterns: не существует

🚀 Инициализация Elasticsearch...
📦 Найден файл паттернов: ac_patterns_20250110_123456.json
🏗️  Создание индекса: sanctions_ac_patterns
   ✅ Индекс создан успешно
📦 Загрузка паттернов...
   ✅ Успешно загружено 2,768,827 паттернов

✅ Elasticsearch инициализирован успешно

==================================================
🚀 Запуск AI Service
==================================================
```

### Вариант 2: Без данных (пустые индексы)

```bash
# Запустить Docker без подготовки данных
docker-compose up -d

# Entrypoint автоматически:
# - Создаст пустые индексы с правильными маппингами
# - Запустит сервис
```

**Логи при старте**:
```
🔍 Проверка индексов...
  ⚠️  sanctions_ac_patterns: не существует

🚀 Инициализация Elasticsearch...
⚠️  Файл с AC паттернами не найден
ℹ️  Создание индексов без загрузки данных...
🏗️  Создание индекса: sanctions_ac_patterns
   ✅ Индекс создан успешно
🏗️  Создание индекса: sanctions_vectors
   ✅ Индекс создан успешно

✅ Все индексы созданы успешно
```

### Вариант 3: Пропустить инициализацию

```yaml
# docker-compose.yml
environment:
  - SKIP_ES_INIT=true
```

```bash
docker-compose up -d

# Entrypoint пропустит инициализацию
# Полезно для отладки или когда индексы уже есть
```

## Структура файлов

### Новые файлы

```
scripts/
├── docker-entrypoint.sh          # Главный entrypoint для Docker
├── create_empty_indices.py       # Создание пустых индексов
└── deploy_to_elasticsearch.py    # Deployment script (уже был)
```

### Изменённые файлы

```
Dockerfile                         # Добавлен ENTRYPOINT
docker-compose.yml                 # Добавлены env variables
src/ai_service/layers/search/
├── config.py                      # Поддержка ES_AC_INDEX, ES_VECTOR_INDEX
└── elasticsearch_adapters.py      # Использует config вместо hardcoded
```

## Проверка работы

### 1. Проверить индексы

```bash
# Внутри Docker контейнера
curl http://elasticsearch:9200/_cat/indices?v

# Или с хоста
curl http://localhost:9200/_cat/indices?v
```

**Ожидаемый вывод**:
```
health status index                    pri rep docs.count
green  open   sanctions_ac_patterns      1   0    2768827
green  open   sanctions_vectors          1   0          0
```

### 2. Тестовый запрос

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Дарья ПАвлова ИНН 2839403975",
    "generate_variants": false,
    "generate_embeddings": false
  }' | jq '.decision.risk_level, .sanctioned'
```

**Ожидаемый вывод**:
```json
"high"
true
```

### 3. Проверить логи

```bash
# Логи entrypoint
docker logs ai-service | head -50

# Логи приложения
docker logs ai-service | grep "Elasticsearch"
```

## Troubleshooting

### Проблема: Elasticsearch не готов

**Симптомы**:
```
❌ Elasticsearch не готов после 60s
ℹ️  Запуск сервиса без Elasticsearch...
```

**Решение**:
```yaml
# Увеличить таймаут в docker-compose.yml
environment:
  - ES_STARTUP_TIMEOUT=120
```

### Проблема: Индексы не создаются

**Симптомы**:
```
❌ Ошибка создания: HTTP 400
```

**Диагностика**:
```bash
# Проверить здоровье Elasticsearch
curl http://localhost:9200/_cluster/health

# Проверить логи Elasticsearch
docker logs elasticsearch
```

**Решение**:
```bash
# Остановить и удалить volumes
docker-compose down -v

# Запустить заново
docker-compose up -d
```

### Проблема: Данные не загружаются

**Симптомы**:
```
⚠️  Файл с AC паттернами не найден
```

**Решение**:
```bash
# 1. Проверить наличие данных
ls -la output/sanctions/

# 2. Если нет - подготовить
python scripts/prepare_sanctions_data.py

# 3. Перезапустить контейнер
docker-compose restart ai-service
```

### Проблема: 404 ошибки при поиске

**Симптомы**:
```
NotFoundError(404, 'no such index [ac_patterns]'
```

**Решение**:
Это старая проблема, которая должна быть решена автоматически. Если всё ещё возникает:

```bash
# 1. Проверить переменные окружения внутри контейнера
docker exec ai-service env | grep ES_

# Должно быть:
# ES_AC_INDEX=sanctions_ac_patterns
# ES_VECTOR_INDEX=sanctions_vectors

# 2. Если не установлены - проверить docker-compose.yml
docker-compose config | grep ES_

# 3. Перезапустить с чистыми volumes
docker-compose down -v
docker-compose up -d
```

## Ручное управление (опционально)

### Создать индексы вручную

```bash
python scripts/create_empty_indices.py \
  --es-host localhost:9200 \
  --index-prefix sanctions
```

### Загрузить данные вручную

```bash
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --index-prefix sanctions \
  --patterns-file output/sanctions/ac_patterns_*.json
```

### Удалить индексы

```bash
curl -X DELETE http://localhost:9200/sanctions_ac_patterns
curl -X DELETE http://localhost:9200/sanctions_vectors
```

## Миграция со старой версии

### Если у вас были индексы `ac_patterns` и `vectors`

**Вариант 1: Создать aliases**

```bash
curl -X POST http://localhost:9200/_aliases -H 'Content-Type: application/json' -d'
{
  "actions": [
    { "add": { "index": "ac_patterns", "alias": "sanctions_ac_patterns" } },
    { "add": { "index": "vectors", "alias": "sanctions_vectors" } }
  ]
}'
```

**Вариант 2: Переиндексация**

```bash
# 1. Остановить сервис
docker-compose stop ai-service

# 2. Переиндексация
curl -X POST http://localhost:9200/_reindex -H 'Content-Type: application/json' -d'
{
  "source": { "index": "ac_patterns" },
  "dest": { "index": "sanctions_ac_patterns" }
}'

# 3. Удалить старые индексы
curl -X DELETE http://localhost:9200/ac_patterns
curl -X DELETE http://localhost:9200/vectors

# 4. Запустить сервис
docker-compose up -d
```

**Вариант 3: Полная переинициализация**

```bash
# Самый простой способ
docker-compose down -v
docker-compose up -d
```

## Кастомизация

### Изменить префикс индексов

```yaml
# docker-compose.yml
environment:
  - ES_INDEX_PREFIX=custom_prefix

# Будут созданы:
# - custom_prefix_ac_patterns
# - custom_prefix_vectors
```

### Использовать внешний Elasticsearch

```yaml
# docker-compose.yml
environment:
  - ES_HOSTS=95.217.84.234:9200
  - ES_USERNAME=elastic
  - ES_PASSWORD=changeme
```

### Отключить автоматическую инициализацию

```yaml
# docker-compose.yml
environment:
  - SKIP_ES_INIT=true

# Полезно когда:
# - Индексы уже созданы
# - Используется внешний Elasticsearch с готовыми данными
# - Отладка без Elasticsearch
```

## Best Practices

### Development

```yaml
# docker-compose.override.yml (для локальной разработки)
version: '3.8'
services:
  ai-service:
    environment:
      - ES_HOSTS=localhost:9200
      - SKIP_ES_INIT=true  # Индексы уже есть на localhost
```

### Production

```yaml
# docker-compose.yml
services:
  ai-service:
    environment:
      - ES_HOSTS=elasticsearch:9200
      - ES_INDEX_PREFIX=sanctions
      - ES_STARTUP_TIMEOUT=120  # Увеличенный таймаут для надёжности
    volumes:
      - ./output:/app/output:ro  # Read-only mount для безопасности
```

### CI/CD

```bash
# .github/workflows/deploy.yml
- name: Build and deploy
  run: |
    docker-compose build
    docker-compose up -d
    # Ждём инициализации
    sleep 30
    # Проверяем здоровье
    curl http://localhost:8002/health
```

## Заключение

Автоматическая инициализация Elasticsearch решает проблему:
- ✅ Согласования имён индексов
- ✅ Ручного создания индексов
- ✅ Загрузки данных при деплое
- ✅ "Работает из коробки"

Теперь деплой - это просто `docker-compose up -d` 🚀
