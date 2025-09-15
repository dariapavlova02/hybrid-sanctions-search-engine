# Детальный анализ ошибок по модулям

## Топ-10 модулей с наибольшим количеством ошибок

### 1. test_advanced_normalization_service.py (27 ошибок)
**Основные проблемы:**
- `AttributeError: 'NormalizationService' object has no attribute 'language_co...'` (14 ошибок)
- `AttributeError: 'NormalizationService' object has no attribute '_analyze_si...'` (9 ошибок)
- `AttributeError: 'NormalizationService' object has no attribute 'normalize_a...'` (6 ошибок)

**Причина:** Серьезные изменения в API NormalizationService после рефакторинга
**Приоритет:** Высокий - основная функциональность

### 2. test_embedding_service_comprehensive.py (24 ошибки)
**Основные проблемы:**
- `AttributeError: <src.ai_service.layers.embeddings.embedding_service.Embeddi...` (8 ошибок)
- `TypeError: list indices must be integers or slices, not str` (5 ошибок)
- `TypeError: EmbeddingService._load_model() takes 1 positional argument but 2...` (2 ошибки)

**Причина:** Изменения в API EmbeddingService
**Приоритет:** Средний - функциональность поиска

### 3. test_orchestrator_service.py (21 ошибок)
**Основные проблемы:**
- `AttributeError: <module 'ai_service.layers.smart_filter.smart_filter_servic...` (13 ошибок)
- `AttributeError: 'UnifiedProcessingResult' object has no attribute 'smartfil...` (11 ошибок)

**Причина:** Изменения в структуре UnifiedProcessingResult и импортах
**Приоритет:** Высокий - основная оркестрация

### 4. test_name_detector.py (21 ошибок)
**Основные проблемы:**
- `AttributeError: <module 'ai_service.layers.smart_filter.name_detector' from...` (21 ошибок)

**Причина:** Неправильные импорты после рефакторинга
**Приоритет:** Низкий - легко исправить

### 5. test_normalization_service.py (20 ошибок)
**Основные проблемы:**
- `AttributeError: 'NormalizationService' object has no attribute 'language_co...'` (14 ошибок)
- `AttributeError: 'NormalizationService' object has no attribute '_analyze_si...'` (9 ошибок)

**Причина:** Изменения в API NormalizationService
**Приоритет:** Высокий - основная функциональность

### 6. test_russian_morphology_service.py (18 ошибок)
**Основные проблемы:**
- `TypeError: list indices must be integers or slices, not str` (5 ошибок)
- `AttributeError: 'MorphologicalAnalysis' object has no attribute 'get'` (3 ошибки)
- `TypeError: RussianMorphologyAnalyzer._generate_variants() got an unexpected...` (2 ошибки)

**Причина:** Изменения в структуре данных морфологического анализа
**Приоритет:** Средний - морфологическая обработка

### 7. test_metrics_service.py (17 ошибок)
**Основные проблемы:**
- `KeyError: 'sum'` (1 ошибка)
- `AttributeError: 'MetricsService' object has no attribute 'record_timing'` (1 ошибка)
- `AttributeError: 'MetricsService' object has no attribute 'max_metrics'` (1 ошибка)

**Причина:** Изменения в API MetricsService
**Приоритет:** Низкий - мониторинг

### 8. test_decision_engine.py (16 ошибок)
**Основные проблемы:**
- `AttributeError: 'UnifiedProcessingResult' object has no attribute 'smartfil...` (11 ошибок)
- `TypeError: DecisionEngine.decide() got an unexpected keyword argument 'cont...` (1 ошибка)
- `AttributeError: 'DecisionEngine' object has no attribute 'batch_decisions'` (1 ошибка)

**Причина:** Изменения в API DecisionEngine и структуре данных
**Приоритет:** Высокий - принятие решений

### 9. test_smart_filter_service.py (13 ошибок)
**Основные проблемы:**
- `AttributeError: <module 'ai_service.layers.smart_filter.smart_filter_servic...` (13 ошибок)

**Причина:** Неправильные импорты
**Приоритет:** Низкий - легко исправить

### 10. test_main_endpoints.py (11 ошибок)
**Основные проблемы:**
- `KeyError: 'tokens'` (2 ошибки)
- `TypeError: 'HTTPException' object is not callable` (2 ошибки)
- `assert 503 == 422` (1 ошибка)
- `RecursionError: maximum recursion depth exceeded` (1 ошибка)

**Причина:** Изменения в API endpoints и структуре ответов
**Приоритет:** Высокий - API интерфейс

## Анализ по типам проблем

### Проблемы с импортами (42 ошибки)
**Модули:** test_name_detector.py, test_smart_filter_service.py, test_orchestrator_service.py
**Решение:** Обновить пути импорта после рефакторинга

### Проблемы с API сервисов (89 ошибок)
**Модули:** test_advanced_normalization_service.py, test_normalization_service.py, test_embedding_service_comprehensive.py
**Решение:** Обновить тесты под новый API

### Проблемы со структурой данных (34 ошибки)
**Модули:** test_russian_morphology_service.py, test_decision_engine.py
**Решение:** Обновить тесты под новую структуру данных

### Проблемы с API endpoints (11 ошибок)
**Модули:** test_main_endpoints.py
**Решение:** Исправить API или обновить тесты

## План исправления по приоритетам

### Фаза 1: Критические ошибки (1-2 дня)
1. **RecursionError** в test_main_endpoints.py
2. **ServiceInitializationError** в test_orchestrator_factory.py
3. **Ошибки API endpoints** в test_main_endpoints.py

### Фаза 2: Основная функциональность (1 неделя)
1. **NormalizationService** - test_advanced_normalization_service.py, test_normalization_service.py
2. **DecisionEngine** - test_decision_engine.py
3. **UnifiedOrchestrator** - test_orchestrator_service.py, test_unified_orchestrator.py

### Фаза 3: Вспомогательные сервисы (1 неделя)
1. **EmbeddingService** - test_embedding_service_comprehensive.py, test_embedding_service_async.py
2. **MorphologyService** - test_russian_morphology_service.py
3. **MetricsService** - test_metrics_service.py

### Фаза 4: Импорты и технические ошибки (2-3 дня)
1. **Импорты** - test_name_detector.py, test_smart_filter_service.py
2. **Конструкторы** - test_decision_logic.py, test_pattern_service.py
3. **Атрибуты** - остальные модули

## Ожидаемые результаты

После исправления всех технических ошибок:
- **Проходящих тестов:** ~1400+ (95%+)
- **Не проходящих тестов:** ~60-80 (логические ошибки)
- **Покрытие тестами:** значительно улучшится

## Рекомендации

1. **Начать с Фазы 1** - исправить критические ошибки
2. **Использовать автоматизацию** - создать скрипты для массового исправления импортов
3. **Тестировать по модулям** - исправлять и тестировать по одному модулю
4. **Документировать изменения** - вести журнал изменений API
