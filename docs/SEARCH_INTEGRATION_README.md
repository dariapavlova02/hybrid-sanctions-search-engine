# Search Integration README

## Обзор

Этот документ описывает интеграцию HybridSearchService в существующий 9-слойный пайплайн AI Service без нарушения контрактов существующих слоёв.

## Архитектура интеграции

### Текущий пайплайн (9 слоёв):
1. **Validation & Sanitization** - валидация входных данных
2. **Smart Filter** - предварительная фильтрация (tier-0 lite)
3. **Language Detection** - определение языка
4. **Unicode Normalization** - нормализация Unicode
5. **Name Normalization** - морфологическая нормализация имён
6. **Signals** - извлечение и структурирование сущностей
7. **Variants** - генерация вариантов (опционально)
8. **Embeddings** - генерация эмбеддингов (опционально)
9. **Decision** - принятие решений на основе сигналов

### Новый слой поиска (Слой 6.5):
**HybridSearchService** - между Signals и Decision

## Ключевые принципы интеграции

### 1. Обратная совместимость
- ✅ Не изменяем контракты существующих слоёв
- ✅ SmartFilter остаётся tier-0 lite (без ES)
- ✅ Все существующие API работают без изменений
- ✅ Поиск включается через feature flag

### 2. Graceful degradation
- ✅ Если ES недоступен → продолжаем без поиска
- ✅ Если поиск падает → логируем и продолжаем
- ✅ Если нет кандидатов → пропускаем поиск

### 3. Конфигурируемость
- ✅ Все параметры через ENV переменные
- ✅ Веса и пороги настраиваются
- ✅ Тайм-ауты и ретраи настраиваются

## Файлы интеграции

### Новые файлы:
- `src/ai_service/contracts/search_contracts.py` - контракты поиска
- `src/ai_service/core/search_integration.py` - логика интеграции
- `src/ai_service/core/unified_orchestrator_with_search.py` - оркестратор с поиском
- `src/ai_service/core/orchestrator_factory_with_search.py` - фабрика с поиском
- `examples/search_integration_example.py` - пример использования

### Обновлённые файлы:
- `src/ai_service/contracts/decision_contracts.py` - добавлен SearchInfo
- `src/ai_service/config/settings.py` - добавлены веса поиска
- `src/ai_service/core/decision_engine.py` - обновлён скоринг
- `src/ai_service/exceptions.py` - добавлены исключения поиска

## Использование

### 1. Базовое использование

```python
from src.ai_service.core.orchestrator_factory_with_search import OrchestratorFactoryWithSearch

# Создать оркестратор с поиском
orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
    enable_hybrid_search=True,
    enable_decision_engine=True
)

# Обработать текст
result = await orchestrator.process(
    text="Иван Петров, дата рождения 15.05.1980",
    search_opts=SearchOpts(
        top_k=50,
        threshold=0.7,
        search_mode=SearchMode.HYBRID
    )
)
```

### 2. Конфигурация через ENV

```bash
# Включение поиска
ENABLE_HYBRID_SEARCH=true

# Elasticsearch
ES_URL=http://localhost:9200
ES_AUTH=elastic:password
ES_VERIFY_SSL=false

# Веса для Decision
AI_DECISION__W_SEARCH_EXACT=0.3
AI_DECISION__W_SEARCH_PHRASE=0.25
AI_DECISION__W_SEARCH_NGRAM=0.2
AI_DECISION__W_SEARCH_VECTOR=0.15

# Пороги
AI_DECISION__THR_SEARCH_EXACT=0.8
AI_DECISION__THR_SEARCH_PHRASE=0.7
AI_DECISION__THR_SEARCH_NGRAM=0.6
AI_DECISION__THR_SEARCH_VECTOR=0.5

# Бонусы
AI_DECISION__BONUS_MULTIPLE_MATCHES=0.1
AI_DECISION__BONUS_HIGH_CONFIDENCE=0.05
```

### 3. Обработка ошибок

```python
try:
    result = await orchestrator.process(text="...")
    
    # Проверить наличие поиска
    if "search" in result.metadata:
        search_info = result.metadata["search"]
        print(f"Найдено совпадений: {search_info['total_matches']}")
    
    # Проверить ошибки
    if result.errors:
        for error in result.errors:
            print(f"Ошибка: {error}")
            
except Exception as e:
    print(f"Обработка не удалась: {e}")
```

## Поток данных

### 1. Извлечение кандидатов
```python
# В SearchIntegration.extract_and_search()
search_candidates = extract_search_candidates(signals_result)
# Результат: ["Иван Петров", "ТОВ Приватбанк", ...]
```

### 2. Гибридный поиск
```python
# AC поиск → Vector поиск → Fusion
search_result = await hybrid_search_service.find_candidates(
    normalized=normalization_result,
    text=text,
    opts=search_opts
)
```

### 3. Создание SearchInfo
```python
# Для Decision слоя
search_info = create_search_info(search_result)
# Результат: SearchInfo с метриками и результатами
```

### 4. Обновление DecisionInput
```python
# Добавление поиска в Decision
decision_input = DecisionInput(
    text=text,
    language=language,
    smartfilter=smartfilter_info,
    signals=signals_info,
    similarity=similarity_info,
    search=search_info  # НОВОЕ
)
```

### 5. Обновлённый скоринг
```python
# В DecisionEngine._calculate_weighted_score()
if inp.search:
    # Exact matches (высший приоритет)
    if search.has_exact_matches and search.exact_confidence >= thr_exact:
        score += w_search_exact * search.exact_confidence
    
    # Phrase matches
    if search.has_phrase_matches and search.phrase_confidence >= thr_phrase:
        score += w_search_phrase * search.phrase_confidence
    
    # N-gram matches
    if search.has_ngram_matches and search.ngram_confidence >= thr_ngram:
        score += w_search_ngram * search.ngram_confidence
    
    # Vector matches
    if search.has_vector_matches and search.vector_confidence >= thr_vector:
        score += w_search_vector * search.vector_confidence
```

## Метрики и мониторинг

### Новые метрики:
- `processing.layer.hybrid_search` - время поиска
- `hybrid_search.total_matches` - количество совпадений
- `hybrid_search.high_confidence_matches` - высокоуверенные совпадения
- `processing.hybrid_search.failed` - ошибки поиска

### Алерты:
- Медленный поиск (>80% от тайм-аута)
- Пустые результаты поиска
- Ошибки подключения к ES

## Тестирование

### 1. Запуск примера
```bash
python examples/search_integration_example.py
```

### 2. Тестирование без ES
```python
# Поиск отключён
orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
    enable_hybrid_search=False
)
```

### 3. Тестирование с ошибками
```python
# ES недоступен
os.environ["ES_URL"] = "http://invalid:9200"
# Ожидаем graceful degradation
```

## Развёртывание

### 1. Постепенное включение
```bash
# Этап 1: Включить поиск для тестирования
ENABLE_HYBRID_SEARCH=true

# Этап 2: Настроить веса
AI_DECISION__W_SEARCH_EXACT=0.3

# Этап 3: Мониторинг и настройка
# Смотреть метрики и корректировать пороги
```

### 2. Мониторинг
- Следить за метриками поиска
- Настраивать пороги на основе результатов
- Корректировать веса для Decision

### 3. Откат
```bash
# Отключить поиск
ENABLE_HYBRID_SEARCH=false
# Система продолжит работать без поиска
```

## Производительность

### Ожидаемые задержки:
- AC поиск: ~100-200ms
- Vector поиск: ~200-500ms
- Fusion: ~10-50ms
- Общее время поиска: ~300-750ms

### Оптимизации:
- Кэширование результатов поиска
- Параллельное выполнение AC и Vector
- Индексация только релевантных полей
- Настройка num_candidates для kNN

## Безопасность

### Обработка данных:
- Поиск только по нормализованным данным
- Логирование поисковых запросов
- Аудит доступа к ES

### Ошибки:
- Не логируем чувствительные данные
- Graceful degradation при ошибках
- Валидация входных данных

## Заключение

Интеграция поиска обеспечивает:
- ✅ Обратную совместимость
- ✅ Graceful degradation
- ✅ Конфигурируемость
- ✅ Мониторинг и метрики
- ✅ Постепенное развёртывание

Система готова к продакшену с возможностью отката в любой момент.
