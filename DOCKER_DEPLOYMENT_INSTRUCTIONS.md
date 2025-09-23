# 🐳 Docker Deployment Instructions для AI Service с поиском

## ✅ Что было исправлено

1. **Добавлена генерация частичных паттернов** - теперь поиск работает для "Порошенко Петро"
2. **Загружено 942,282 паттернов** в Elasticsearch, включая 220,241 partial_match паттернов
3. **Частично исправлен конфликт зависимостей** elasticsearch/httpx

## 🚀 Docker Deployment

### 1. Обновить код

```bash
git pull origin main
```

### 2. Обновить Dockerfile для исправления httpx конфликта

Создать или обновить `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копировать requirements
COPY requirements.txt .

# Установить совместимые версии библиотек для исправления httpx конфликта
RUN pip install --no-cache-dir httpx==0.25.2 elasticsearch==8.10.0

# Установить остальные зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копировать код
COPY src/ src/
COPY data/ data/

# Установить переменные окружения
ENV PYTHONPATH=/app/src
ENV ENABLE_SEARCH=true
ENV ENABLE_EMBEDDINGS=true

# Открыть порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Обновить docker-compose.yml

```yaml
version: '3.8'

services:
  ai-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENABLE_SEARCH=true
      - ENABLE_EMBEDDINGS=true
      - ELASTICSEARCH_HOST=95.217.84.234
      - ELASTICSEARCH_PORT=9200
      - ELASTICSEARCH_USER=elastic
      - ELASTICSEARCH_PASSWORD=AiServiceElastic2024!
    depends_on:
      - elasticsearch
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    restart: unless-stopped

volumes:
  elasticsearch_data:
```

### 4. Создать .dockerignore

```
.git
.gitignore
README.md
Dockerfile
.dockerignore
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
*.log
debug_*.py
test_*.py
upload_*.py
patterns_*.json
*_log.txt
SEARCH_ISSUE_DIAGNOSIS.md
DEPLOYMENT_*.md
```

## 🚀 Команды для deployment

### Вариант 1: Docker Compose (рекомендуется)

```bash
# Пересобрать образы
docker-compose build --no-cache

# Запустить сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Смотреть логи
docker-compose logs -f ai-service
```

### Вариант 2: Только AI Service (если ES уже запущен)

```bash
# Собрать образ
docker build -t ai-service:latest .

# Запустить контейнер
docker run -d \
  --name ai-service \
  -p 8000:8000 \
  -e ENABLE_SEARCH=true \
  -e ENABLE_EMBEDDINGS=true \
  -e ELASTICSEARCH_HOST=95.217.84.234 \
  -e ELASTICSEARCH_PORT=9200 \
  ai-service:latest

# Проверить логи
docker logs -f ai-service
```

## 🧪 Проверка работы

### 1. Проверить health endpoint

```bash
curl http://localhost:8000/health
```

### 2. Тест частичного поиска

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Порошенко Петро"}' | jq .search_results
```

**Ожидаемый результат**:
```json
{
  "search_results": {
    "total_hits": 3,
    "search_type": "ac_patterns",
    "results": [
      {
        "pattern": "Порошенко Петро",
        "canonical": "Порошенко Петро Олексійович",
        "pattern_type": "partial_match",
        "confidence": 0.75
      }
    ]
  }
}
```

### 3. Проверить подключение к ES

```bash
# Из контейнера
docker exec ai-service curl -s 95.217.84.234:9200/_cluster/health

# Проверить количество паттернов
docker exec ai-service curl -s 95.217.84.234:9200/ai_service_ac_patterns/_count
```

## 🔧 Диагностика проблем

### Если контейнер не запускается:

```bash
# Проверить логи
docker logs ai-service

# Проверить переменные окружения
docker exec ai-service env | grep ENABLE

# Зайти в контейнер
docker exec -it ai-service bash

# Проверить импорты в контейнере
docker exec ai-service python -c "import httpx; print(httpx.__version__)"
docker exec ai-service python -c "import elasticsearch; print('ES OK')"
```

### Если поиск не работает:

```bash
# Проверить подключение к ES
docker exec ai-service curl -s 95.217.84.234:9200/_cluster/health

# Проверить паттерны
docker exec ai-service curl -s 95.217.84.234:9200/ai_service_ac_patterns/_search?size=1
```

## 📝 Важные замечания для Docker

### Исправление httpx конфликта в Dockerfile:
```dockerfile
# КРИТИЧЕСКИ ВАЖНО: устанавливать совместимые версии ПЕРЕД requirements.txt
RUN pip install --no-cache-dir httpx==0.25.2 elasticsearch==8.10.0
RUN pip install --no-cache-dir -r requirements.txt
```

### Переменные окружения:
```bash
ENABLE_SEARCH=true          # Включить AC поиск
ENABLE_EMBEDDINGS=true      # Включить векторный поиск
ELASTICSEARCH_HOST=95.217.84.234
ELASTICSEARCH_PORT=9200
```

### Проверка портов:
- AI Service: `localhost:8000`
- Elasticsearch: `localhost:9200` (если локальный)

## 🆘 Troubleshooting

### Если ES недоступен:
```bash
# Проверить сеть
docker exec ai-service ping 95.217.84.234

# Временно отключить поиск
docker run -d \
  --name ai-service-no-search \
  -p 8000:8000 \
  -e ENABLE_SEARCH=false \
  ai-service:latest
```

### Если нужны дополнительные зависимости:
Обновить `requirements.txt` и пересобрать:
```bash
docker-compose build --no-cache ai-service
docker-compose up -d ai-service
```

## ✅ Финальная проверка

После deployment проверить:

1. ✅ Сервис запустился: `curl localhost:8000/health`
2. ✅ Поиск работает: тест с "Порошенко Петро"
3. ✅ ES доступен: проверка количества паттернов (должно быть 942,282)
4. ✅ Частичные паттерны найдены: результат содержит `"pattern_type": "partial_match"`