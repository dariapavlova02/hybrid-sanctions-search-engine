# Анализ TODO в проекте AI Service

## Общая статистика

Найдено **43 TODO комментария** в проекте, распределенных по следующим категориям:

### 1. Elasticsearch Integration (26 TODO)
**Файлы:** `src/ai_service/layers/search/elasticsearch_adapters.py`, `src/ai_service/layers/search/hybrid_search_service.py`

**Основные задачи:**
- Инициализация реального Elasticsearch клиента
- Реализация AC поиска через Elasticsearch
- Реализация векторного поиска через Elasticsearch kNN
- Интеграция с существующими слоями (WatchlistIndexService, EnhancedVectorIndex)
- Реализация fallback механизмов

**Приоритет:** ВЫСОКИЙ - критично для функциональности поиска

### 2. Checksum Validation (4 TODO)
**Файл:** `src/ai_service/data/patterns/identifiers.py`

**Задачи:**
- Реализация валидации контрольных сумм для:
  - IBAN
  - SWIFT/BIC
  - EIN
  - SSN

**Приоритет:** СРЕДНИЙ - улучшение качества валидации

### 3. Embedding Preprocessor (2 TODO)
**Файл:** `src/ai_service/services/embedding_preprocessor.py`

**Задачи:**
- Реализация режима `include_attrs=True`
- Настройка конфигурации для будущего использования

**Приоритет:** НИЗКИЙ - дополнительная функциональность

### 4. Test Integration (3 TODO)
**Файлы:** `tests/unit/test_unified_orchestrator.py`, `tests/integration/test_e2e_sanctions_screening.py`, `tests/e2e/test_sanctions_screening_pipeline.py`

**Задачи:**
- Исправление моков для signals
- Завершение интеграции санкционного скрининга
- Реализация MultiTierScreeningService

**Приоритет:** СРЕДНИЙ - завершение тестирования

### 5. Documentation (2 TODO)
**Файлы:** `docs/ARCHITECTURE_OVERVIEW_codex.md`, `docs/ARCHITECTURE_OVERVIEW.md`

**Задачи:**
- Документирование известных пробелов
- Обновление архитектурной документации

**Приоритет:** НИЗКИЙ - документация

## Детальный анализ по файлам

### `src/ai_service/layers/search/elasticsearch_adapters.py`
- **12 TODO** - все связаны с интеграцией Elasticsearch
- Заглушки для AC и Vector поиска
- Отсутствует реальный Elasticsearch клиент
- Нет health check реализации

### `src/ai_service/layers/search/hybrid_search_service.py`
- **8 TODO** - интеграция с существующими сервисами
- Fallback механизмы не реализованы
- Комбинирование результатов не завершено
- Фильтрация метаданных отсутствует

### `src/ai_service/data/patterns/identifiers.py`
- **4 TODO** - валидация контрольных сумм
- Только базовая валидация длины
- Нет проверки контрольных сумм для финансовых идентификаторов

### `src/ai_service/services/embedding_preprocessor.py`
- **2 TODO** - расширенная функциональность
- Режим include_attrs не реализован
- Конфигурация для будущего использования

## Рекомендации по приоритизации

### Немедленно (P0)
1. **Elasticsearch Client Integration** - критично для работы поиска
2. **Basic AC/Vector Search Implementation** - основная функциональность

### В ближайшее время (P1)
1. **Fallback Service Integration** - надежность системы
2. **Checksum Validation** - качество валидации данных
3. **Test Fixes** - завершение тестирования

### В будущем (P2)
1. **Advanced Features** - расширенная функциональность
2. **Documentation Updates** - улучшение документации

## Потенциальные риски

1. **Elasticsearch Dependency** - система поиска не работает без Elasticsearch
2. **Data Validation** - некорректная валидация финансовых идентификаторов
3. **Test Coverage** - неполное тестирование критических компонентов
4. **Fallback Reliability** - отсутствие резервных механизмов

## Следующие шаги

1. Создать план реализации Elasticsearch интеграции
2. Приоритизировать TODO по критичности
3. Назначить ответственных за каждый блок задач
4. Установить временные рамки для завершения
5. Регулярно обновлять статус TODO в процессе разработки
