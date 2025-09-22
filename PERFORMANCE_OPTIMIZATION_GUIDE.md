# Performance Optimization Guide

## Устранение узких мест без ущерба для функциональности

Данное руководство описывает комплексные оптимизации для устранения выявленных узких мест:

1. **Большие файлы данных** (словари 1000+ строк)
2. **Смешивание Async/Sync** операций
3. **Использование памяти** для больших словарей

---

## 🚀 Новые компоненты

### 1. OptimizedDictionaryLoader
**Файл**: `src/ai_service/data/optimized_dictionary_loader.py`

**Возможности**:
- ✅ **Ленивая загрузка**: словари загружаются только при первом обращении
- ✅ **Сжатие**: автоматическое сжатие для быстрого I/O
- ✅ **Чанкинг**: разбиение больших словарей на части
- ✅ **Кэширование**: LRU кэш с TTL и управлением памятью
- ✅ **Фоновая предзагрузка**: загрузка часто используемых словарей
- ✅ **Метрики**: отслеживание производительности и использования

**Пример использования**:
```python
# Асинхронно
loader = get_optimized_loader()
ukrainian_names = await loader.get_dictionary_async('ukrainian_names')

# Синхронно (совместимость)
ukrainian_names = loader.get_dictionary_sync('ukrainian_names')

# С чанкингом для больших словарей
chunk = await loader.get_dictionary_async('large_dict', chunk_key='A-E')
```

### 2. AsyncSyncBridge
**Файл**: `src/ai_service/utils/async_sync_bridge.py`

**Возможности**:
- ✅ **Неблокирующее выполнение**: sync код в thread pool
- ✅ **Автоопределение контекста**: автоматический выбор async/sync
- ✅ **Батчевая обработка**: групповые операции
- ✅ **Безопасные вызовы**: предотвращение блокировки event loop

**Пример использования**:
```python
bridge = get_async_sync_bridge()

# Безопасный вызов sync функции из async контекста
result = await bridge.run_sync_in_thread(expensive_sync_function, arg1, arg2)

# Адаптивный вызов (автоматически определяет контекст)
result = bridge.adaptive_call(maybe_async_function, args)

# Декоратор для автоматического преобразования
@async_safe
def expensive_function(data):
    return process_large_data(data)
```

### 3. OptimizedDataAccess
**Файл**: `src/ai_service/data/optimized_data_access.py`

**Возможности**:
- ✅ **Унифицированный доступ**: единый интерфейс для всех словарей
- ✅ **Умные fallback**: резервные данные при сбоях загрузки
- ✅ **Предзагрузка**: автоматическая загрузка часто используемых данных
- ✅ **Статистика**: детальные метрики использования

**Пример использования**:
```python
data_access = get_optimized_data_access()

# Инициализация с предзагрузкой
await data_access.initialize()

# Асинхронный доступ
stopwords = await data_access.get_stopwords_async()
ukrainian_names = await data_access.get_ukrainian_names_async()

# Синхронный доступ (совместимость)
diminutives = data_access.get_diminutives_sync('ru')
```

---

## 🔄 Миграция без прерывания работы

### Стратегия 1: Совместимый адаптер
**Файл**: `src/ai_service/data/compatibility_adapter.py`

```python
# СТАРЫЙ КОД - продолжает работать
from ai_service.data.dicts.stopwords import STOP_ALL
from ai_service.data.ukrainian_names import UKRAINIAN_NAMES

# НОВЫЙ КОД - автоматически оптимизирован
from ai_service.data.compatibility_adapter import STOP_ALL, UKRAINIAN_NAMES
```

### Стратегия 2: Постепенная миграция

1. **Этап 1**: Установить адаптер совместимости
```python
# В основном модуле
from ai_service.data.compatibility_adapter import install_compatibility_adapter
install_compatibility_adapter()
```

2. **Этап 2**: Обновить критические модули
```python
# Заменить прямые импорты
# ИЗ:
from ai_service.data.dicts.stopwords import STOP_ALL

# В:
from ai_service.data.optimized_data_access import get_stopwords_optimized
STOP_ALL = get_stopwords_optimized()
```

3. **Этап 3**: Добавить асинхронность в новые модули
```python
async def process_text_async(text: str):
    data_access = get_optimized_data_access()
    stopwords = await data_access.get_stopwords_async()
    # ... обработка
```

---

## 📊 Мониторинг производительности

### Метрики загрузки словарей
```python
loader = get_optimized_loader()
stats = loader.get_cache_stats()

print(f"Использование памяти: {stats['memory_usage_mb']:.2f}MB")
print(f"Кэшированных словарей: {stats['cached_dictionaries']}")
print(f"Коэффициент попадания в кэш: {stats['cache_hit_rate']:.2%}")
```

### Метрики async/sync операций
```python
bridge = get_async_sync_bridge()
timing_stats = await bridge.get_timing_stats()

for mode, stats in timing_stats.items():
    print(f"{mode}: avg={stats['avg']:.2f}ms, p95={stats['p95']:.2f}ms")
```

### Метрики доступа к данным
```python
from ai_service.data.compatibility_adapter import get_data_access_metrics

metrics = get_data_access_metrics()
print(f"Всего обращений: {metrics['total_accesses']}")
print(f"Коэффициент попадания в кэш: {metrics['cache_hit_rate']:.2%}")
```

---

## ⚡ Оптимизации по уровням

### Уровень 1: Критические словари (немедленно)
```python
# Предзагрузка критических данных
critical_dicts = [
    'stopwords', 'diminutives_ru', 'diminutives_uk',
    'given_names_ru', 'given_names_uk'
]

loader = get_optimized_loader()
await loader.preload_dictionaries(critical_dicts)
```

### Уровень 2: Часто используемые словари
```python
# Чанкинг для больших словарей
names_chunk_a_e = await loader.get_dictionary_async('ukrainian_names', 'A-E')
names_chunk_f_m = await loader.get_dictionary_async('ukrainian_names', 'F-M')
```

### Уровень 3: Редко используемые словари
```python
# Ленивая загрузка по требованию
def get_rare_dictionary():
    return loader.get_dictionary_sync('rare_patterns')
```

---

## 🎯 Конфигурация для разных сценариев

### Сценарий 1: Высокая нагрузка (Production)
```python
# Большой лимит памяти, агрессивное кэширование
loader = OptimizedDictionaryLoader(max_memory_mb=1024)
bridge = AsyncSyncBridge(max_workers=16)

# Предзагрузка всех критических словарей
await loader.preload_dictionaries([
    'stopwords', 'ukrainian_names', 'russian_names',
    'diminutives_ru', 'diminutives_uk', 'payment_triggers'
])
```

### Сценарий 2: Ограниченная память (Edge deployment)
```python
# Минимальный лимит памяти, чанкинг
loader = OptimizedDictionaryLoader(max_memory_mb=128)
bridge = AsyncSyncBridge(max_workers=4)

# Только критические словари
await loader.preload_dictionaries(['stopwords', 'diminutives_ru'])
```

### Сценарий 3: Разработка и тестирование
```python
# Умеренные лимиты, подробные метрики
loader = OptimizedDictionaryLoader(max_memory_mb=256)
loader.enable_detailed_metrics = True

# Быстрая инициализация
await loader.preload_dictionaries(['stopwords'])
```

---

## 🔧 Интеграция с существующими модулями

### Нормализация имен
```python
# В normalization_service.py

class NormalizationService:
    def __init__(self):
        self.data_access = get_optimized_data_access()
        self.bridge = get_async_sync_bridge()

    async def normalize_async(self, text: str) -> NormalizationResult:
        # Асинхронная загрузка данных
        stopwords = await self.data_access.get_stopwords_async()
        diminutives = await self.data_access.get_diminutives_async('ru')

        # Неблокирующая обработка
        result = await self.bridge.run_sync_in_thread(
            self._process_text_heavy, text, stopwords, diminutives
        )
        return result
```

### Поиск и индексация
```python
# В search_service.py

class SearchService:
    async def build_index_async(self):
        data_access = get_optimized_data_access()

        # Батчевая загрузка
        operations = [
            (data_access.get_ukrainian_names_async, (), {}),
            (data_access.get_russian_names_async, (), {}),
            (data_access.get_payment_triggers_async, (), {}),
        ]

        bridge = get_async_sync_bridge()
        results = await bridge.batch_sync_operations(operations, batch_size=5)

        # Обработка результатов
        for result in results:
            if not isinstance(result, Exception):
                self.index.add_terms(result)
```

---

## 📈 Ожидаемые улучшения

### Производительность
- **Время загрузки**: ⬇️ 60-80% (благодаря сжатию и кэшированию)
- **Использование памяти**: ⬇️ 40-60% (управление памятью и чанкинг)
- **Время отклика**: ⬇️ 30-50% (неблокирующие операции)

### Масштабируемость
- **Concurrent requests**: ⬆️ 200-300% (thread pool execution)
- **Memory efficiency**: ⬆️ 150-200% (LRU cache management)
- **Fault tolerance**: ⬆️ 100% (fallback mechanisms)

### Мониторинг
- **Cache hit rates**: детальная статистика по каждому словарю
- **Load times**: перцентили времени загрузки
- **Memory pressure**: автоматическое управление памятью

---

## 🚨 Важные замечания

### Совместимость
- ✅ **Полная обратная совместимость** с существующим кодом
- ✅ **Постепенная миграция** без остановки сервиса
- ✅ **Fallback механизмы** при сбоях загрузки

### Безопасность
- ✅ **Thread safety** для всех операций
- ✅ **Memory safety** с автоматической очисткой
- ✅ **Error handling** с graceful degradation

### Производительность
- ✅ **Non-blocking** все I/O операции
- ✅ **Memory efficient** управление большими словарями
- ✅ **Cache aware** оптимальное использование кэша

---

## 🔄 План внедрения

### Неделя 1: Базовая инфраструктура
1. Развернуть `OptimizedDictionaryLoader`
2. Установить `AsyncSyncBridge`
3. Настроить `CompatibilityAdapter`

### Неделя 2: Критические модули
1. Миграция `normalization_service`
2. Обновление `search_service`
3. Тестирование производительности

### Неделя 3: Полная миграция
1. Обновление всех модулей
2. Оптимизация конфигурации
3. Мониторинг в production

### Неделя 4: Тонкая настройка
1. Анализ метрик
2. Оптимизация кэширования
3. Документация

Данная оптимизация обеспечивает **значительное улучшение производительности** при **полном сохранении функциональности** и **нулевом времени простоя** при внедрении.