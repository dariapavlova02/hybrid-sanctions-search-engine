# Детальный анализ причин падений тестов

## Группа 1: Async/Await проблемы

### Сигнатура
```
TypeError: object Mock can't be used in 'await' expression
```

### Анализ
**Файл:** `tests/unit/test_orchestrator_service_fixed.py:37`
**Проблема:** Мок для async метода `should_process` возвращает `False` вместо awaitable объекта

**Код проблемы:**
```python
mock_smart_filter.return_value = False  # Неправильно для async метода
```

**Правильное решение:**
```python
from unittest.mock import AsyncMock
mock_smart_filter.return_value = AsyncMock(return_value=False)
```

### Затронутые тесты
- `test_process_basic_functionality`
- Множественные тесты с async сервисами

### Приоритет: ВЫСОКИЙ
- Критично для основного функционала
- Блокирует тестирование orchestrator

## Группа 2: pytest-asyncio проблемы

### Сигнатура
```
async def functions are not natively supported
```

### Анализ
**Файл:** `tests/unit/layers/test_normalization_contracts.py`
**Проблема:** Async тесты без `@pytest.mark.asyncio` декоратора

**Код проблемы:**
```python
async def test_name(self, service):  # Отсутствует декоратор
    # тест
```

**Правильное решение:**
```python
@pytest.mark.asyncio
async def test_name(self, service):
    # тест
```

### Затронутые тесты
- Все 11 тестов в `test_normalization_contracts.py`
- Множественные тесты с async fixtures

### Приоритет: ВЫСОКИЙ
- Блокирует большинство тестов
- Массовая проблема

## Группа 3: Проблемы с типами данных

### Сигнатура
```
AssertionError: assert False
+ isinstance проверки
```

### Анализ
**Файл:** `src/ai_service/layers/normalization/morphology/ukrainian_morphology.py:158`
**Проблема:** Возвращается `dict` вместо объекта `MorphologicalAnalysis`

**Код проблемы:**
```python
return {'case': None, 'confidence': 0.8, 'gender': 'masc', 'lemma': 'сергій'}
```

**Правильное решение:**
```python
return MorphologicalAnalysis(
    case=None,
    confidence=0.8,
    gender='masc',
    lemma='сергій'
)
```

### Затронутые тесты
- `test_gender_detection_for_ukrainian_names` (8 тестов)
- Тесты морфологического анализа

### Приоритет: СРЕДНИЙ
- Влияет на морфологию
- Не критично для основного функционала

## Группа 4: Отсутствующие зависимости

### Сигнатура
```
ModuleNotFoundError: No module named 'httpx'
ModuleNotFoundError: No module named 'spacy'
```

### Анализ
**Проблема:** Не установлены необходимые зависимости

**Решение:**
```bash
source venv/bin/activate
pip install httpx spacy pytest-timeout
```

### Затронутые тесты
- Множественные тесты при первом запуске
- Решено установкой зависимостей

### Приоритет: НИЗКИЙ
- Инфраструктурная проблема
- Легко исправляется

## Группа 5: Конфигурация pytest

### Сигнатура
```
pytest-timeout не установлен
```

### Анализ
**Файл:** `pytest.ini`
**Проблема:** В конфигурации указан `pytest-timeout`, но пакет не установлен

**Решение:**
```bash
pip install pytest-timeout
# или удалить из pytest.ini
```

### Приоритет: НИЗКИЙ
- Не критично
- Легко исправляется
