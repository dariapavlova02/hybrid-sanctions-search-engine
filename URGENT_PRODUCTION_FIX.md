# 🚨 URGENT: Production Fix Required

## Проблема

**Статус**: 🔴 КРИТИЧЕСКИЙ
**Симптом**: Прямые совпадения AC search + decision engine не дают "high risk"
**Причина**: Два бага одновременно

---

## 📋 Что исправить

### 1. ✅ **Decision Engine Fix** (уже готов)
**Файл**: `src/ai_service/core/decision_engine.py`
**Строка**: 60
**Изменение**: Добавить `search=inp.search`

```python
# ДО (неправильно):
safe_input = DecisionInput(
    text=inp.text,
    language=inp.language,
    smartfilter=smartfilter,
    signals=signals,
    similarity=similarity
    # ОТСУТСТВУЕТ: search=inp.search
)

# ПОСЛЕ (правильно):
safe_input = DecisionInput(
    text=inp.text,
    language=inp.language,
    smartfilter=smartfilter,
    signals=signals,
    similarity=similarity,
    search=inp.search  # ← ДОБАВИТЬ ЭТУ СТРОКУ
)
```

### 2. ❓ **Elasticsearch Connectivity** (нужно проверить)
**Проблема**: На продакшене search возвращает 0 hits
**Возможные причины**:
- Неправильный `ELASTICSEARCH_HOST` в environment
- Неправильное имя индекса
- Отсутствуют environment переменные для поиска

---

## 🚀 Инструкции по деплою

### Шаг 1: Деплой Decision Engine Fix

```bash
# На продакшен сервере (95.217.84.234)
cd /root/ai-service

# Создать backup
cp src/ai_service/core/decision_engine.py src/ai_service/core/decision_engine.py.backup.$(date +%Y%m%d_%H%M%S)

# Отредактировать файл - добавить строку 60:
# search=inp.search

# Рестарт AI service
docker-compose restart ai-service
```

### Шаг 2: Проверить Environment переменные

```bash
# Проверить настройки Elasticsearch
docker exec ai-service env | grep ELASTICSEARCH
docker exec ai-service env | grep ENABLE_SEARCH

# Должно быть:
# ELASTICSEARCH_HOST=95.217.84.234 (или localhost если ES в том же контейнере)
# ELASTICSEARCH_PORT=9200
# ENABLE_SEARCH=true
# ENABLE_AHO_CORASICK=true
```

### Шаг 3: Тест после фикса

```bash
curl -X POST http://95.217.84.234:8002/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Петро Порошенко"}' | jq '.'
```

**Ожидаемый результат**:
```json
{
  "search_results": {
    "total_hits": 2,  // ← ДОЛЖНО БЫТЬ > 0
    "results": [...]
  },
  "decision": {
    "risk_level": "high",  // ← ДОЛЖНО БЫТЬ "high"
    "score_breakdown": {
      "search_contribution": 0.25,  // ← ДОЛЖНО ПРИСУТСТВОВАТЬ
      "smartfilter_contribution": 0.075,
      "person_contribution": 0.18
    }
  }
}
```

---

## 🔍 Диагностика проблем

### Если decision fix не работает:
```bash
# Проверить что файл был изменен
grep -A 5 -B 5 "search=inp.search" /root/ai-service/src/ai_service/core/decision_engine.py

# Должно показать строку с search=inp.search
```

### Если search не работает (total_hits: 0):

```bash
# 1. Проверить ES доступность
curl http://95.217.84.234:9200/_cluster/health

# 2. Проверить patterns в ES
curl "http://95.217.84.234:9200/ai_service_ac_patterns/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {"wildcard": {"pattern": "*порошенко*"}}, "size": 3}'

# 3. Проверить environment в контейнере
docker exec ai-service env | grep -E "(ELASTICSEARCH|ENABLE_SEARCH|ENABLE_AHO)"

# 4. Проверить логи AI service при старте
docker logs ai-service | grep -E "(search|Search|HybridSearchService)" | tail -10

# 5. Проверить что search service инициализировался
# В логах должно быть: "Search service initialized"
# Если "Failed to initialize search service" - проблема с подключением к ES
```

**Возможные проблемы с search:**
- ❌ `ELASTICSEARCH_HOST` не указан (default: localhost)
- ❌ `ENABLE_SEARCH=false` в environment
- ❌ Elasticsearch dependency ошибки при импорте
- ❌ Search service падает при инициализации → fallback на None

---

## 📊 Бизнес-эффект

**До фикса**: AC находит паттерны → но risk = "low" → FALSE NEGATIVE
**После фикса**: AC находит паттерны → risk = "high" → ПРАВИЛЬНОЕ ОБНАРУЖЕНИЕ

**Критичность**: Прямые совпадения с санкционными списками НЕ блокируются

---

## 📱 Уведомления

После успешного деплоя протестируйте:
1. `"Петро Порошенко"` → должен быть `"risk_level": "high"`
2. `"Иван Иванов"` → должен остаться `"risk_level": "low"`
3. Проверьте что `search_contribution` появился в score_breakdown

## 🔄 Проверка эскалации на вектора

Для проверки что эскалация работает, протестируйте с именем, которого НЕТ в AC patterns:

```bash
curl -X POST http://95.217.84.234:8002/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Василий Пупкин"}' | jq '.'
```

**Ожидаемый результат** (если вектора работают):
```json
{
  "search_results": {
    "total_hits": 0,  // AC не нашел
    "search_type": "hybrid",  // Но попробовал vector
    "processing_time_ms": > 0  // Время на поиск было
  },
  "decision": {
    "score_breakdown": {
      "search_contribution": 0.0,  // Нет AC matches
      "similarity_contribution": > 0.0  // Но есть vector similarity
    }
  }
}
```

**Настройки эскалации:**
- `ESCALATION_THRESHOLD=0.8` (default) - если AC score < 0.8, идет эскалация
- `ENABLE_ESCALATION=true` - включена ли эскалация
- `ENABLE_VECTOR_FALLBACK=true` - включен ли vector fallback

---

## 🔧 Файлы для деплоя

**Основной файл**: `src/ai_service/core/decision_engine.py` (строка 60)
**Backup создается автоматически** с timestamp

**Готов к деплою**: ✅ Локальный файл содержит исправление