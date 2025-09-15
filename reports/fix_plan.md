# План исправлений падающих тестов

## Этап 1: Быстрые победы (30 минут)

### 1.1 Установка зависимостей (5 минут)
```bash
source venv/bin/activate
pip install httpx spacy pytest-timeout
```

### 1.2 Исправление AsyncMock (15 минут)
**Файл:** `tests/unit/test_orchestrator_service_fixed.py`

**Найти и заменить:**
```python
# Было:
mock_smart_filter.return_value = False

# Стало:
from unittest.mock import AsyncMock
mock_smart_filter.return_value = AsyncMock(return_value=False)
```

**Применить ко всем async мокам в файле**

### 1.3 Добавление @pytest.mark.asyncio (10 минут)
**Файл:** `tests/unit/layers/test_normalization_contracts.py`

**Добавить в начало каждого async теста:**
```python
@pytest.mark.asyncio
async def test_name(self, service):
```

## Этап 2: Исправление типов данных (30 минут)

### 2.1 Исправление ukrainian_morphology.py
**Файл:** `src/ai_service/layers/normalization/morphology/ukrainian_morphology.py:158`

**Найти и заменить:**
```python
# Было:
return {'case': None, 'confidence': 0.8, 'gender': 'masc', 'lemma': 'сергій'}

# Стало:
return MorphologicalAnalysis(
    case=None,
    confidence=0.8,
    gender='masc',
    lemma='сергій'
)
```

### 2.2 Проверить другие morphology файлы
- `russian_morphology.py`
- `english_morphology.py`
- Исправить аналогичные проблемы

## Этап 3: Проверка и тестирование (15 минут)

### 3.1 Запуск тестов
```bash
# Проверить исправленные тесты
pytest tests/unit/test_orchestrator_service_fixed.py -v
pytest tests/unit/layers/test_normalization_contracts.py -v
pytest tests/unit/test_ukrainian_morphology.py -v
```

### 3.2 Полный прогон
```bash
pytest -c tmp/pytest.sane.ini --maxfail=10
```

## Ожидаемые результаты

### После Этапа 1:
- Снижение падающих тестов с 202 до ~150
- Исправление async проблем

### После Этапа 2:
- Снижение падающих тестов с 150 до ~120
- Исправление проблем с типами данных

### После Этапа 3:
- Снижение падающих тестов с 120 до ~50-80
- Останутся только реальные проблемы в бизнес-логике

## Дополнительные рекомендации

### 1. Добавить pre-commit хуки
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-asyncio-check
        name: Check async tests have @pytest.mark.asyncio
        entry: scripts/check_async_tests.py
        language: python
```

### 2. Добавить типизацию для моков
```python
from unittest.mock import AsyncMock
from typing import Any

def create_async_mock(return_value: Any) -> AsyncMock:
    return AsyncMock(return_value=return_value)
```

### 3. Создать утилиты для тестирования
```python
# tests/utils/async_mocks.py
from unittest.mock import AsyncMock, Mock

def create_service_mocks():
    return {
        'validation_service': Mock(),
        'smart_filter_service': AsyncMock(),
        'language_service': Mock(),
        # ...
    }
```

## Приоритизация по важности

1. **КРИТИЧНО:** Async/Await проблемы (блокируют основную функциональность)
2. **ВАЖНО:** pytest-asyncio проблемы (блокируют большинство тестов)
3. **СРЕДНЕ:** Проблемы с типами данных (влияют на морфологию)
4. **НИЗКО:** Отсутствующие зависимости (инфраструктурные проблемы)
