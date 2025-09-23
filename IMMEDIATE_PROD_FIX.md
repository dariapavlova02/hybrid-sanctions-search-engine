# 🚨 НЕМЕДЛЕННОЕ ИСПРАВЛЕНИЕ ПРОДАКШН ПРОБЛЕМ

## Обнаруженные проблемы

### ✅ Feature flags настроены ПРАВИЛЬНО!
- `PRESERVE_FEMININE_SURNAMES=true` ✅
- `ENABLE_ENHANCED_GENDER_RULES=true` ✅
- `PRESERVE_FEMININE_SUFFIX_UK=true` ✅
- `ALLOW_SMART_FILTER_SKIP=false` ✅

### 🔍 Реальная проблема: VERSION/CACHE

## Пошаговое исправление:

### 1. 🔄 Перестроить и перезапустить Docker контейнер

```bash
# На продакшн сервере:
cd /path/to/ai-service

# Остановить текущий контейнер
docker-compose -f docker-compose.prod.yml down

# Очистить кеш Docker (критично!)
docker system prune -f
docker builder prune -f

# Перестроить образ с нуля
docker-compose -f docker-compose.prod.yml build --no-cache ai-service

# Запустить заново
docker-compose -f docker-compose.prod.yml up -d

# Проверить логи
docker logs ai-service-prod -f
```

### 2. 🧹 Очистить кеши системы

```bash
# Очистить Redis/память кеши если есть
curl -X POST http://95.217.84.234:8000/admin/clear-cache

# Или перезапуск Elasticsearch для очистки индексов
docker-compose -f docker-compose.prod.yml restart elasticsearch
```

### 3. 🔍 Включить debug для диагностики

Временно изменить в `env.production`:
```bash
DEBUG_TRACING=true  # Включить для диагностики
```

Перезапустить:
```bash
docker-compose -f docker-compose.prod.yml restart ai-service
```

### 4. ✅ Протестировать исправления

```bash
# Тест 1: Украинское женское имя
curl -X POST http://95.217.84.234:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Павлової Дарʼї", "generate_variants": false}'

# Ожидаем: "normalized_text": "Павлова Дарʼя"

# Тест 2: Порошенко
curl -X POST http://95.217.84.234:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Порошенка Петенька", "generate_variants": false}'

# Ожидаем: "normalized_text": "Порошенко Петро"
```

### 5. 🔍 Проверить Elasticsearch поиск

```bash
# Проверить что индекс загружен
curl "http://95.217.84.234:9200/ac-patterns/_count"

# Должно вернуть: {"count": 430246} или подобное большое число
```

## Если проблема останется:

### 🐛 Дополнительная диагностика:

1. **Проверить версию кода в контейнере**:
```bash
docker exec ai-service-prod git log --oneline -5
```

2. **Проверить что все исправления применены**:
```bash
docker exec ai-service-prod grep -r "enable_en_nicknames" src/
```

3. **Проверить Python окружение**:
```bash
docker exec ai-service-prod python -c "
from src.ai_service.layers.normalization.morphology_adapter import MorphologyAdapter
m = MorphologyAdapter()
print('Павлової →', m.to_nominative('Павлової', 'uk'))
"
```

## Ожидаемые результаты после исправления:

```json
// "Павлової Дарʼї Юріївни"
{
  "normalized_text": "Павлова Дарʼя Юріївна",
  "decision": {"risk_level": "medium", "risk_score": 0.7}
}

// "Порошенка Петенька"
{
  "normalized_text": "Порошенко Петро",
  "decision": {"risk_level": "medium", "risk_score": 0.6}
}
```

⚠️ **Если после всех шагов проблема остается** - значит есть фундаментальная проблема в коде, которую нужно детально отлаживать через debug traces.