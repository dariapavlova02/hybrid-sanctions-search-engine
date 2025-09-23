# 🚀 Команды для безопасного деплоя

## ⚡ Быстрый деплой (TL;DR)

```bash
# 1. Бэкапы
cp env.production env.production.backup.$(date +%Y%m%d_%H%M%S)
curl -s http://localhost:9200/_cat/indices?v > elasticsearch-indices.before.txt

# 2. Обновление
git pull origin main
cp env.production.search env.production

# 3. Перезапуск ТОЛЬКО ai-service (НЕ трогаем Elasticsearch!)
docker-compose -f docker-compose.prod.yml stop ai-service
docker-compose -f docker-compose.prod.yml build --no-cache ai-service
docker-compose -f docker-compose.prod.yml up -d ai-service

# 4. Проверка
curl http://localhost:8000/health
curl -X POST http://localhost:8000/process -d '{"text":"test"}' | jq '.search_results'
```

## 🔍 Проверки после деплоя

```bash
# Elasticsearch не пострадал
curl http://localhost:9200/_cluster/health

# Поиск работает
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Порошенко Петр"}' | jq '.search_results'

# Нормализация работает
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Порошенка Петенька"}' | jq '.normalized_text'
```

## 🚨 Откат (если нужен)

```bash
# Быстрый откат конфигурации
cp env.production.backup.* env.production
docker-compose -f docker-compose.prod.yml restart ai-service
```

## ✅ Ожидаемый результат

После деплоя в API ответах должно появиться поле:
```json
{
  "search_results": {
    "query": "...",
    "results": [],
    "total_hits": 0,
    "search_type": "similarity_mock"
  }
}
```

**ВАЖНО**: Данные Elasticsearch НЕ затрагиваются! 🔒