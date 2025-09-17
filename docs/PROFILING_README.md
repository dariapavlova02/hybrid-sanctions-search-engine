# Профилирование AI Service Normalization Factory

Этот документ описывает систему профилирования производительности для factory-пути нормализации.

## Обзор

Система профилирования предназначена для выявления узких мест в производительности
NormalizationServiceFactory на коротких строках и предоставления конкретных
рекомендаций по оптимизации.

## Компоненты системы

### 1. Скрипты профилирования

- **`scripts/profile_normalization.py`** - Профилирование с cProfile + pstats
- **`scripts/profile_normalization_pyinstrument.py`** - Профилирование с pyinstrument (HTML-отчёты)
- **`scripts/generate_profile_report.py`** - Генерация markdown-отчёта с рекомендациями

### 2. Утилиты профилирования

- **`src/ai_service/utils/profiling.py`** - Дешёвые счётчики, таймеры и контекстные менеджеры

### 3. Интеграция в сервисы

Профилирование интегрировано в ключевые компоненты:
- `TokenProcessor.strip_noise_and_tokenize`
- `MorphologyProcessor.normalize_slavic_token`
- `RoleClassifier.tag_tokens`
- `NormalizationFactory.normalize_text`

## Быстрый старт

### Установка зависимостей

```bash
make -f Makefile.profile install-profile-deps
```

### Запуск полного профилирования

```bash
make -f Makefile.profile profile
```

### Быстрое профилирование

```bash
make -f Makefile.profile profile-quick
```

## Детальное использование

### 1. cProfile профилирование

```bash
python scripts/profile_normalization.py [iterations]
```

**Параметры:**
- `iterations` - количество итераций на фразу (по умолчанию: 100)

**Результаты:**
- `artifacts/profile_stats.prof` - бинарный файл с результатами cProfile
- Консольный вывод с TOP-50 функций по cumtime/tottime

### 2. pyinstrument профилирование

```bash
python scripts/profile_normalization_pyinstrument.py [iterations]
```

**Параметры:**
- `iterations` - количество итераций на фразу (по умолчанию: 20)

**Результаты:**
- `artifacts/profile_async.html` - HTML-отчёт асинхронного профилирования
- `artifacts/profile_sync.html` - HTML-отчёт синхронного профилирования
- `artifacts/profile_detail_*.html` - детальные отчёты для отдельных фраз

### 3. Генерация отчёта

```bash
python scripts/generate_profile_report.py
```

**Результаты:**
- `artifacts/profile_report.md` - детальный markdown-отчёт с рекомендациями

## Тестовые данные

Система использует фиксированный набор из 20 тестовых фраз:

### Русские имена
- "Іван Петров"
- "ООО 'Ромашка' Иван И."
- "Анна Сергеевна Иванова"
- "Петр Петрович Петров"
- "Мария Александровна Сидорова"

### Украинские имена
- "Петро Порошенко"
- "Володимир Зеленський"
- "Олена Піддубна"
- "ТОВ 'Київ' Олександр О."
- "Наталія Вікторівна Коваленко"

### Английские имена
- "John Smith"
- "Mary Johnson"
- "Robert Brown"
- "Elizabeth Davis"
- "Michael Wilson"

### Смешанные случаи
- "Dr. John Smith"
- "Prof. Maria Garcia"
- "Mr. Петр Петров"
- "Ms. Анна Иванова"
- "Іван I. Петров"

## Метрики и анализ

### Собираемые метрики

1. **Время выполнения** (p50, p95, p99, среднее, минимум, максимум)
2. **Количество вызовов** функций
3. **Накопленное время** (cumtime)
4. **Собственное время** (tottime)
5. **Использование памяти** (при включённой трассировке)

### Типы горячих точек

1. **Tokenization** - токенизация и обработка строк
2. **Morphology** - морфологический анализ
3. **Role Classification** - классификация ролей токенов
4. **Normalization** - процесс нормализации
5. **Regex** - регулярные выражения

## Рекомендации по оптимизации

### 1. Кэширование морфологического анализа

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _morph_nominal_cached(token: str, language: str) -> str:
    # Кэшированная версия морфологического анализа
    pass
```

**Ожидаемый эффект**: Снижение времени на 30-50%

### 2. Предкомпиляция регулярных выражений

```python
import re

# На уровне модуля
TOKEN_SPLIT_PATTERN = re.compile(r"([,])")
INITIALS_PATTERN = re.compile(r"^((?:[A-Za-zА-Яа-яІЇЄҐіїєґ]\.){2,})([A-Za-zА-Яа-яІЇЄҐіїєґ].*)$")
```

**Ожидаемый эффект**: Снижение времени на 10-20%

### 3. Оптимизация поиска в словарях

```python
# Использовать set вместо list для O(1) поиска
STOP_WORDS_SET = set(STOP_ALL)
```

**Ожидаемый эффект**: Снижение времени на 5-15%

### 4. Кэширование результатов классификации ролей

```python
from functools import lru_cache

@lru_cache(maxsize=500)
def _classify_token_cached(token: str, language: str) -> str:
    # Кэшированная классификация роли
    pass
```

**Ожидаемый эффект**: Снижение времени на 20-40%

## Интерпретация результатов

### HTML-отчёты pyinstrument

1. Откройте `artifacts/profile_async.html` в браузере
2. Изучите flame graph для визуализации call stack
3. Обратите внимание на функции с наибольшим временем выполнения
4. Ищите узкие места в критическом пути

### Markdown-отчёт

1. Откройте `artifacts/profile_report.md`
2. Изучите таблицу TOP-10 горячих точек
3. Обратите внимание на рекомендации по оптимизации
4. Следуйте приоритизации (high/medium/low priority)

## Интеграция в CI/CD

### GitHub Actions

```yaml
- name: Run Performance Profiling
  run: |
    make -f Makefile.profile profile-quick
    # Загрузить artifacts/profile_report.md как артефакт
```

### Локальная разработка

```bash
# Перед коммитом
make -f Makefile.profile profile-quick

# Проверить результаты
make -f Makefile.profile show-profile
```

## Ограничения и предупреждения

1. **Профилирование влияет на производительность** - не используйте в production
2. **Результаты могут варьироваться** - запускайте несколько раз для стабильности
3. **Память** - pyinstrument может потреблять много памяти на больших наборах данных
4. **Зависимости** - убедитесь, что все опциональные зависимости установлены

## Troubleshooting

### Ошибка "pyinstrument не установлен"

```bash
pip install pyinstrument
```

### Ошибка "ModuleNotFoundError"

```bash
# Убедитесь, что вы в корневой директории проекта
cd /path/to/ai-service
python scripts/profile_normalization.py
```

### Нет результатов профилирования

```bash
# Очистите кэш и перезапустите
make -f Makefile.profile clean-profile
make -f Makefile.profile profile
```

## Дополнительные ресурсы

- [cProfile документация](https://docs.python.org/3/library/profile.html)
- [pyinstrument документация](https://pyinstrument.readthedocs.io/)
- [Python profiling best practices](https://docs.python.org/3/library/profile.html#profile-stats)
