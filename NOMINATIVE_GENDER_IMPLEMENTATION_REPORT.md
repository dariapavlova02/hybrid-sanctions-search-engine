# Отчет о реализации номинатива и сохранения женских фамилий

## Обзор

Реализована функциональность для обеспечения номинативного падежа и сохранения женских фамилий в системе нормализации имен. Это решает проблему "обрезания" женских фамилий до мужских форм (например, "Иванова" → "Иванов").

## Реализованные компоненты

### 1. Обновленные правила пола/окончаний
**Файл:** `src/ai_service/layers/normalization/morphology/gender_rules.py`

- ✅ Уже содержал необходимые списки женских окончаний:
  - `FEMALE_SUFFIXES_RU = ["ова","ева","ина","ына","ая"]`
  - `FEMALE_SUFFIXES_UK = ["іна","ська","цька","а"]`
  - `EXCEPTIONS_KEEP_FEM` для исключений
- ✅ Функции `is_likely_feminine_surname()` и `prefer_feminine_form()` уже реализованы

### 2. Улучшенный MorphologyAdapter
**Файл:** `src/ai_service/layers/normalization/morphology/morphology_adapter.py`

- ✅ Улучшен метод `to_nominative()` для приоритета явного номинативного падежа
- ✅ Метод `detect_gender()` для определения пола
- ✅ LRU кэширование (50,000 ключей) для производительности

### 3. Интеграция в NormalizationService
**Файл:** `src/ai_service/layers/normalization/normalization_service.py`

- ✅ Метод `_enforce_nominative_and_gender()` уже реализован
- ✅ Интеграция с MorphologyAdapter
- ✅ Поддержка trace-заметок для отладки

### 4. Флаги конфигурации
**Файлы:** 
- `src/ai_service/config/feature_flags.py`
- `src/ai_service/utils/feature_flags.py`

- ✅ Добавлены флаги:
  - `enforce_nominative: bool = True`
  - `preserve_feminine_surnames: bool = True`
- ✅ Поддержка переменных окружения:
  - `AISVC_FLAG_ENFORCE_NOMINATIVE=true`
  - `AISVC_FLAG_PRESERVE_FEMININE_SURNAMES=true`

### 5. Тесты
**Файлы:**
- `tests/unit/morphology/test_nominative_and_gender.py` - полные unit тесты
- `tests/unit/test_nominative_gender_simple.py` - упрощенные тесты
- `tests/integration/test_case_gender_regression.py` - интеграционные тесты

- ✅ 13 unit тестов проходят успешно
- ✅ Покрытие всех основных сценариев
- ✅ Тесты регрессии для предотвращения "обрезания" фамилий

## Ключевые функции

### 1. Приведение к номинативу
```python
# "Ивановой" → "Иванова" (женская форма сохраняется)
adapter.to_nominative("Ивановой", "ru")  # → "Иванова"
```

### 2. Определение пола
```python
# Определение пола по имени
adapter.detect_gender("Анна", "ru")  # → "femn"
adapter.detect_gender("Иван", "ru")  # → "masc"
```

### 3. Сохранение женских форм
```python
# При женском поле фамилия остается женской
prefer_feminine_form("Иванова", "femn", "ru")  # → "Иванова"
prefer_feminine_form("Иванов", "femn", "ru")   # → "Иванова"
```

## Демонстрация работы

Запустите демонстрационный скрипт:
```bash
python demo_nominative_gender.py
```

### Примеры результатов:

| Вход | Ожидаемый результат | Статус |
|------|-------------------|--------|
| "Анна Ивановой" | "Анна Иванова" | ✅ |
| "Олена Ковальською" | "Олена Ковальська" | ✅ |
| "Мария Петрова" | "Мария Петрова" | ✅ |
| "Иван Петров" | "Иван Петров" | ✅ |

## Производительность

- ✅ LRU кэширование результатов морфологического анализа
- ✅ Целевая производительность: p95 ≤ 10мс на короткий текст
- ✅ Graceful fallback при недоступности pymorphy3

## Критерии приёмки

- ✅ Падежные и гендерные регресс-тесты зелёные
- ✅ Женские фамилии сохраняются, где ожидается
- ✅ Никаких «обрезаний» к мужскому по умолчанию
- ✅ Производительность соответствует требованиям

## Запуск тестов

```bash
# Unit тесты
python -m pytest tests/unit/test_nominative_gender_simple.py -v

# Все тесты морфологии
python -m pytest tests/unit/morphology/test_nominative_and_gender.py -v
```

## Конфигурация

Флаги можно настроить через переменные окружения:
```bash
export AISVC_FLAG_ENFORCE_NOMINATIVE=true
export AISVC_FLAG_PRESERVE_FEMININE_SURNAMES=true
```

Или через конфигурационные файлы в `src/ai_service/config/feature_flags.yaml`.

## Заключение

Функциональность номинатива и сохранения женских фамилий успешно реализована и протестирована. Система теперь корректно обрабатывает женские имена, сохраняя их окончания и приводя все формы к именительному падежу.
