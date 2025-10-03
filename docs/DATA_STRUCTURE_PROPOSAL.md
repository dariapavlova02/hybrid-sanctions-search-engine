# Data Structure Organization Proposal

**Дата:** 03.10.2025
**Проблема:** Две папки data/ с нелогичным разделением
**Статус:** Предложение по реорганизации

---

## 🎯 Текущая Проблема

### Сейчас у нас 2 папки без логики:

```
data/ (корень)
├── lexicons/           172 КБ (txt/json)    ✅ Используется
├── diminutives_*.json   95 КБ (json)        ✅ Используется
└── sanctions/           40 МБ               ❌ Дубликаты

src/ai_service/data/
├── dicts/              960 КБ (python)      ✅ Используется
├── patterns/           144 КБ (python)      ✅ Используется
└── *.json               8 МБ (sanctions)    ✅ Используется
```

### Проблемы:

1. **Нелогичное разделение:**
   - Lexicons в корне, dicts в src/
   - Diminutives JSON в корне, но доступ через `parents[4]` или `parents[5]` (хрупко!)
   - Sanctions дублируются

2. **Путаница в доступе:**
   ```python
   # Из разных мест разный путь:
   Path(__file__).parents[5] / "data" / "diminutives_ru.json"  # normalization_factory
   Path(__file__).parents[4] / "data" / "diminutives_ru.json"  # morphology_adapter
   Path(__file__).parent.parent.parent.parent.parent / "data"  # name_detector
   ```

3. **Нет единого источника истины**

---

## 🎯 Анализ Типов Данных

### По назначению:

| Тип | Назначение | Формат | Где сейчас |
|-----|------------|--------|------------|
| **Static Lexicons** | Стоп-слова, legal forms, titles | TXT/JSON | `data/lexicons/` |
| **Diminutives** | Уменьшительные имена | JSON | `data/` |
| **Name Dictionaries** | Имена (ru/uk/en/asian/etc) | Python | `src/ai_service/data/dicts/` |
| **Patterns** | Regex для signals (dates, IDs, legal) | Python | `src/ai_service/data/patterns/` |
| **Sanctions Data** | Большие JSON для поиска | JSON | `src/ai_service/data/` + дубли |

### По частоте изменений:

| Категория | Частота обновлений | Размер |
|-----------|-------------------|--------|
| Lexicons | Редко (ручные правки) | 172 КБ |
| Diminutives | Редко (ручные правки) | 95 КБ |
| Dictionaries (Python) | Средне (разработка) | 960 КБ |
| Patterns (Python) | Средне (разработка) | 144 КБ |
| Sanctions JSON | Часто (автоматически) | 8 МБ |

---

## 💡 Предложенная Структура

### Вариант 1: По типу данных (РЕКОМЕНДУЕТСЯ)

```
data/                                    # Все данные в одном месте
├── lexicons/                            # Лексиконы (редактируемые файлы)
│   ├── stopwords/
│   │   ├── stopwords_ru.txt
│   │   ├── stopwords_uk.txt
│   │   └── stopwords_en.txt
│   ├── legal_forms/
│   │   ├── legal_forms_ru.json
│   │   ├── legal_forms_uk.json
│   │   └── legal_forms_en.json
│   ├── diminutives/
│   │   ├── diminutives_ru.json
│   │   └── diminutives_uk.json
│   └── nicknames/
│       └── en_nicknames.json
│
├── dictionaries/                        # Python словари (код)
│   ├── names/
│   │   ├── russian_names.py
│   │   ├── ukrainian_names.py
│   │   ├── english_names.py
│   │   ├── asian_names.py
│   │   └── ...
│   ├── triggers/
│   │   ├── payment_triggers.py
│   │   └── company_triggers.py
│   └── patterns/
│       ├── stopwords.py
│       └── smart_filter_patterns.py
│
├── patterns/                            # Regex паттерны для signals
│   ├── dates.py
│   ├── identifiers.py
│   └── legal_forms.py
│
└── sanctions/                           # Большие данные
    ├── sanctioned_persons.json
    ├── sanctioned_companies.json
    └── terrorism_black_list.json
```

**Преимущества:**
- ✅ Логичная структура по типу
- ✅ Легко найти
- ✅ Единый корень для доступа
- ✅ Чистое разделение: lexicons (файлы) vs dictionaries (код)

**Доступ:**
```python
# Единый базовый путь
_project_root = Path(__file__).resolve()
while not (_project_root / "pyproject.toml").exists():
    _project_root = _project_root.parent

_data_dir = _project_root / "data"

# Примеры:
lexicons_path = _data_dir / "lexicons" / "diminutives" / "diminutives_ru.json"
sanctions_path = _data_dir / "sanctions" / "sanctioned_persons.json"
```

---

### Вариант 2: Разделение source/runtime

```
data/                           # Source данные (редактируемые)
├── lexicons/
├── diminutives/
└── dictionaries/               # Python модули

src/ai_service/
└── runtime_data/              # Runtime данные (генерируемые/большие)
    ├── sanctions/
    └── cache/
```

**Преимущества:**
- ✅ Разделение source/runtime
- ✅ Большие файлы отдельно

**Минусы:**
- ❌ Сложнее управление
- ❌ Два места для данных

---

### Вариант 3: Всё в src/ai_service/data/

```
src/ai_service/data/
├── lexicons/
├── dicts/
├── patterns/
└── sanctions/
```

**Преимущества:**
- ✅ Всё рядом с кодом
- ✅ Проще импорты

**Минусы:**
- ❌ Большие файлы в src/
- ❌ Смешивается код и данные
- ❌ Неудобно редактировать данные

---

## 🎯 Рекомендация: Вариант 1

### План миграции на Вариант 1:

#### Фаза 1: Реорганизация lexicons (низкий риск)

```bash
# 1. Создать новую структуру
mkdir -p data/lexicons/stopwords
mkdir -p data/lexicons/legal_forms
mkdir -p data/lexicons/diminutives
mkdir -p data/lexicons/nicknames

# 2. Переместить diminutives
mv data/diminutives_ru.json data/lexicons/diminutives/
mv data/diminutives_uk.json data/lexicons/diminutives/

# 3. Реорганизовать существующие lexicons
mv data/lexicons/stopwords*.txt data/lexicons/stopwords/
mv data/lexicons/legal_forms*.json data/lexicons/legal_forms/
mv data/lexicons/en_nicknames.json data/lexicons/nicknames/

# 4. Обновить пути в коде (см. ниже)
```

#### Фаза 2: Перенос Python модулей (средний риск)

```bash
# 1. Создать dictionaries/
mkdir -p data/dictionaries/names
mkdir -p data/dictionaries/triggers

# 2. Переместить из src/ai_service/data/dicts/
mv src/ai_service/data/dicts/*_names.py data/dictionaries/names/
mv src/ai_service/data/dicts/*_triggers.py data/dictionaries/triggers/
mv src/ai_service/data/dicts/stopwords.py data/dictionaries/patterns/

# 3. Обновить импорты
```

#### Фаза 3: Перенос patterns (низкий риск)

```bash
# Просто переместить директорию
mv src/ai_service/data/patterns data/patterns
```

#### Фаза 4: Sanctions (низкий риск)

```bash
# 1. Переместить в data/sanctions
mkdir -p data/sanctions
mv src/ai_service/data/sanctioned_*.json data/sanctions/
mv src/ai_service/data/terrorism_black_list.json data/sanctions/

# 2. Удалить дубликаты из старой data/sanctions/
# (уже есть в новой структуре)
```

---

## 🛠️ Изменения в коде

### 1. Создать utils/data_paths.py

```python
"""
Central data path management
"""
from pathlib import Path
from typing import Optional

def get_project_root() -> Path:
    """Find project root by looking for pyproject.toml"""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Project root not found")

# Constants
PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
LEXICONS_DIR = DATA_DIR / "lexicons"
DICTIONARIES_DIR = DATA_DIR / "dictionaries"
PATTERNS_DIR = DATA_DIR / "patterns"
SANCTIONS_DIR = DATA_DIR / "sanctions"

def get_diminutives_path(lang: str) -> Path:
    """Get path to diminutives file"""
    return LEXICONS_DIR / "diminutives" / f"diminutives_{lang}.json"

def get_stopwords_path(lang: str) -> Path:
    """Get path to stopwords file"""
    return LEXICONS_DIR / "stopwords" / f"stopwords_{lang}.txt"

def get_legal_forms_path(lang: str) -> Path:
    """Get path to legal forms file"""
    return LEXICONS_DIR / "legal_forms" / f"legal_forms_{lang}.json"
```

### 2. Обновить все файлы

**Старый код:**
```python
# ❌ Хрупкий путь
ru_path = Path(__file__).resolve().parents[5] / "data" / "diminutives_ru.json"
```

**Новый код:**
```python
# ✅ Централизованный доступ
from ...utils.data_paths import get_diminutives_path

ru_path = get_diminutives_path("ru")
```

---

## 📊 Сравнение вариантов

| Критерий | Вариант 1 (data/) | Вариант 2 (split) | Вариант 3 (src/) |
|----------|-------------------|-------------------|------------------|
| Логичность структуры | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Простота доступа | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Управляемость | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Разделение concerns | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Риск миграции | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

**Победитель: Вариант 1** ✅

---

## ⏱️ Оценка трудозатрат

| Фаза | Задачи | Время | Риск |
|------|--------|-------|------|
| **Фаза 0: Подготовка** | | | |
| - Удалить data/sanctions/ дубликаты | 5 мин | Низкий |
| - Создать utils/data_paths.py | 15 мин | Низкий |
| **Фаза 1: Lexicons** | | | |
| - Реорганизовать структуру | 10 мин | Низкий |
| - Обновить lexicon_loader.py | 20 мин | Низкий |
| - Обновить все diminutives импорты | 30 мин | Средний |
| - Тестирование | 30 мин | - |
| **Фаза 2: Dictionaries** | | | |
| - Переместить Python модули | 15 мин | Средний |
| - Обновить все импорты | 1 час | Средний |
| - Тестирование | 30 мин | - |
| **Фаза 3: Patterns** | | | |
| - Переместить patterns/ | 5 мин | Низкий |
| - Обновить импорты | 20 мин | Низкий |
| **Фаза 4: Sanctions** | | | |
| - Переместить JSON | 5 мин | Низкий |
| - Обновить sanctions_data_loader | 15 мин | Низкий |
| **Итого** | | **4-5 часов** | Средний |

---

## 🎯 Немедленные действия (прямо сейчас)

### Шаг 0: Очистка дубликатов

```bash
# Удалить 40 МБ дубликатов
rm -rf data/sanctions/

git add -A
git commit -m "chore: remove duplicate sanctions data (40 MB)

All sanctions files are duplicates of src/ai_service/data/ versions.
Keeping only the source files in src/ai_service/data/."
```

**Эффект:** Сразу освободим 40 МБ, подготовим к реорганизации

---

## 📋 Итоговая структура (после миграции)

```
ai-service/
├── data/                           # 📁 Все данные
│   ├── lexicons/                   # Редактируемые лексиконы
│   │   ├── stopwords/
│   │   ├── legal_forms/
│   │   ├── diminutives/
│   │   └── nicknames/
│   ├── dictionaries/               # Python словари
│   │   ├── names/
│   │   └── triggers/
│   ├── patterns/                   # Regex паттерны
│   └── sanctions/                  # Большие JSON
│
├── src/ai_service/
│   ├── utils/
│   │   └── data_paths.py          # 🔧 Централизованный доступ
│   └── ...
│
└── pyproject.toml
```

**Принципы:**
1. ✅ Единый корень `data/` для всех данных
2. ✅ Логичная структура по типу/назначению
3. ✅ Централизованный доступ через `utils/data_paths.py`
4. ✅ Чистое разделение: файлы vs код
5. ✅ Легко найти, легко обновить

---

## ✅ Рекомендация

**Сейчас:**
1. Удалить `data/sanctions/` (40 МБ дубликатов)
2. Создать issue для миграции на Вариант 1
3. Запланировать 4-5 часов на миграцию

**Приоритет:** Средний (не критично, но улучшит maintainability)

**ROI:** Высокий (чистая структура, меньше ошибок, легче поддержка)
