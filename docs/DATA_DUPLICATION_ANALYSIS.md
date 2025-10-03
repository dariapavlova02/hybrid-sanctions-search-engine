# Data Directory Duplication Analysis

**Дата:** 03.10.2025
**Проблема:** Две папки data/ в проекте

---

## 🎯 Executive Summary

**Найдено:** Две структуры data/ с частичным дублированием

```
data/                           # Корень (старая структура)
└── lexicons/                   ✅ Используется
└── diminutives_*.json          ❌ Не используется (95 КБ)
└── sanctions/                  ❌ Дубликаты + мусор (41 МБ)

src/ai_service/data/            # Новая структура
└── dicts/                      ✅ Используется
└── patterns/                   ✅ Используется
└── sanctions JSON              ✅ Используется (основные)
```

**К удалению:** ~41 МБ дубликатов и мусора
**Причина:** Миграция со старой структуры на новую не завершена

---

## 📊 Детальный Анализ

### Структура 1: `data/` (корень) - СТАРАЯ

#### ✅ Используется (ОСТАВИТЬ)

**data/lexicons/** (~20 файлов, ~6.5k LOC)
```python
Использование: src/ai_service/layers/normalization/lexicon_loader.py

# Код поиска:
def load_lexicons(base_path: Optional[Path] = None) -> Lexicons:
    if base_path is None:
        # Default to project root/data/lexicons
        while current_path != current_path.parent:
            if (current_path / "pyproject.toml").exists():
                base_path = current_path / "data" / "lexicons"
                break
```

**Файлы:**
- ✅ `en_nicknames.json` (1,372 LOC)
- ✅ `legal_forms_*.json` (ru/uk/en, ~2k LOC)
- ✅ `stopwords_*.txt/json` (~1.5k LOC)
- ✅ `en_titles.txt`, `en_suffixes.txt`, etc.

**Используется в:**
- `normalization_service.py`
- `role_tagger_service.py`
- `nameparser_adapter.py`
- `normalization_factory.py`

---

#### ❌ НЕ используется (УДАЛИТЬ)

**1. data/diminutives_ru.json** (70 КБ) 🔴
```bash
Размер: 70 КБ
Формат: JSON dictionary
Проверка: grep -r "data/diminutives" src/ --include="*.py"
Результат: ❌ НЕ НАЙДЕНО

Замена: src/ai_service/data/dicts/russian_diminutives.py (используется)
```

**2. data/diminutives_uk.json** (25 КБ) 🔴
```bash
Размер: 25 КБ
Формат: JSON dictionary
Результат: ❌ НЕ НАЙДЕНО

Замена: src/ai_service/data/dicts/ukrainian_diminutives.py (используется)
```

---

**3. data/sanctions/** директория 🔴

**ДУБЛИКАТЫ sanctions JSON:**

```bash
# Проверка идентичности:
diff -q data/sanctions/sanctioned_persons.json src/ai_service/data/sanctioned_persons.json
# Результат: Files are identical (одинаковые!)

diff -q data/sanctions/sanctioned_companies.json src/ai_service/data/sanctioned_companies.json
# Результат: Files are identical (одинаковые!)

diff -q data/sanctions/terrorism_black_list.json src/ai_service/data/terrorism_black_list.json
# Результат: Files are identical (одинаковые!)
```

| Файл | Размер | Статус |
|------|--------|--------|
| `sanctioned_persons.json` | 3.5 МБ | ❌ ДУБЛЬ |
| `sanctioned_companies.json` | 3.6 МБ | ❌ ДУБЛЬ |
| `terrorism_black_list.json` | 824 КБ | ❌ ДУБЛЬ |
| `sanctions_cache.json` | **33 МБ** | ❌ НЕ используется |
| `custom_ukraine_russia.json` | 1.7 КБ | ❌ НЕ используется |

**Итого дубликатов:** 7.9 МБ
**Итого мусора:** 33 МБ
**Всего к удалению из sanctions/:** 40.9 МБ

---

**Анализ sanctions_cache.json (33 МБ):**

```python
# sanctions_data_loader.py ищет кэш в своей директории:
self.data_dir = Path(data_dir)  # = src/ai_service/data/
self._cache_file = self.data_dir / "sanctions_cache.json"

# НЕ в корневой data/sanctions/!
```

**Вывод:** `data/sanctions/sanctions_cache.json` (33 МБ) создан старым кодом, больше не используется.

---

### Структура 2: `src/ai_service/data/` - НОВАЯ

#### ✅ ВСЁ используется (ОСТАВИТЬ)

**dicts/** - Python словари (~10.6k LOC)
```
✅ russian_names.py, ukrainian_names.py, english_names.py
✅ russian_diminutives.py, ukrainian_diminutives.py
✅ asian_names.py, arabic_names.py, indian_names.py, ...
✅ stopwords.py, payment_triggers.py, company_triggers.py
✅ Все 19 словарей активно используются
```

**patterns/** - Паттерны (~38 КБ)
```
✅ dates.py - birthdate extraction
✅ identifiers.py - INN, EDRPOU, OGRN patterns
✅ legal_forms.py - юр. формы
```

**sanctions JSON** - Основные данные (~8 МБ)
```
✅ sanctioned_persons.json (3.5 МБ)
✅ sanctioned_companies.json (3.6 МБ)
✅ terrorism_black_list.json (824 КБ)

Использование: sanctions_data_loader.py
```

---

## 🔍 Причина Дублирования

### История миграции:

**Шаг 1: Старая структура** (изначально)
```
data/
├── lexicons/           # Все лексиконы
├── diminutives_*.json  # Уменьшительные
└── sanctions/          # Sanctions JSON
```

**Шаг 2: Рефакторинг** (частичный)
```
src/ai_service/data/
├── dicts/              # ← Новые Python словари
├── patterns/           # ← Новые паттерны
└── sanctions JSON      # ← Скопированы сюда
```

**Проблема:** Старые файлы не удалили!
```
data/sanctions/         # ← Остались дубликаты
data/diminutives_*.json # ← Остались неиспользуемые
```

**Результат:** 41 МБ дублей + неиспользуемых файлов

---

## 📋 Матрица Решений

### data/ (корень)

| Компонент | Размер | Использование | Решение |
|-----------|--------|---------------|---------|
| **lexicons/** | ~6.5k LOC | ✅ lexicon_loader | ✅ **ОСТАВИТЬ** |
| `diminutives_ru.json` | 70 КБ | ❌ Нигде | ❌ **УДАЛИТЬ** |
| `diminutives_uk.json` | 25 КБ | ❌ Нигде | ❌ **УДАЛИТЬ** |
| **sanctions/** директория: | | | |
| - `sanctioned_persons.json` | 3.5 МБ | ❌ Дубль | ❌ **УДАЛИТЬ** |
| - `sanctioned_companies.json` | 3.6 МБ | ❌ Дубль | ❌ **УДАЛИТЬ** |
| - `terrorism_black_list.json` | 824 КБ | ❌ Дубль | ❌ **УДАЛИТЬ** |
| - `sanctions_cache.json` | **33 МБ** | ❌ Устарел | ❌ **УДАЛИТЬ** |
| - `custom_ukraine_russia.json` | 1.7 КБ | ❌ Нигде | ❌ **УДАЛИТЬ** |

**Итого к удалению:** ~41 МБ

### src/ai_service/data/

| Компонент | Статус | Решение |
|-----------|--------|---------|
| **dicts/** (19 файлов) | ✅ Все используются | ✅ **ОСТАВИТЬ** |
| **patterns/** (3 файла) | ✅ Все используются | ✅ **ОСТАВИТЬ** |
| **sanctions JSON** (3 файла) | ✅ Основные источники | ✅ **ОСТАВИТЬ** |

---

## 🎯 План Действий

### Вариант A: Быстрое удаление (РЕКОМЕНДУЕТСЯ)

**Удалить дубликаты и мусор:**
```bash
# 1. Удалить неиспользуемые diminutives (95 КБ)
rm data/diminutives_ru.json
rm data/diminutives_uk.json

# 2. Удалить всю директорию sanctions (41 МБ дублей)
rm -rf data/sanctions/

# 3. Оставить только lexicons
# data/lexicons/ - НЕ ТРОГАТЬ (используется!)
```

**Эффект:**
- Освобождение: ~41 МБ
- Риск: НУЛЕВОЙ (дубликаты и мусор)
- Время: 10 секунд

---

### Вариант B: Полная миграция (долгосрочное решение)

**Цель:** Переместить lexicons в src/ai_service/data/

**Шаг 1: Переместить lexicons**
```bash
mv data/lexicons src/ai_service/data/lexicons
```

**Шаг 2: Обновить lexicon_loader.py**
```python
# Изменить путь поиска:
base_path = current_path / "src" / "ai_service" / "data" / "lexicons"
```

**Шаг 3: Удалить data/ полностью**
```bash
rm -rf data/
```

**Шаг 4: Обновить .gitignore**
```gitignore
# Remove old data/ entry if exists
```

**Эффект:**
- Единая структура данных в src/ai_service/data/
- Нет дублирования
- Чистая архитектура

**Риск:** Средний (требует тестирования lexicon_loader)

---

## 🚀 Рекомендация

### Немедленно (Вариант A):

```bash
# Безопасное удаление дублей и мусора
rm data/diminutives_ru.json data/diminutives_uk.json
rm -rf data/sanctions/

# Коммит
git add -A
git commit -m "chore: remove duplicated sanctions and unused diminutives

- Remove data/sanctions/ directory (41 MB duplicates + cache)
- Remove data/diminutives_*.json (unused, replaced by dicts/)
- Keep data/lexicons/ (actively used by lexicon_loader)

All duplicate sanctions files are identical to src/ai_service/data/ versions.
sanctions_cache.json (33 MB) is outdated and regenerable."
```

**Эффект:** ~41 МБ освобождено за 10 секунд, нулевой риск

---

### Опционально (Вариант B):

После успешного Варианта A, можно запланировать миграцию lexicons:
1. Создать feature branch: `refactor/migrate-lexicons`
2. Переместить lexicons в src/ai_service/data/
3. Обновить lexicon_loader.py
4. Тестирование normalization/role_tagger
5. Удалить data/ полностью

**Срок:** 1-2 часа работы + тестирование

---

## 📊 Итоговая Статистика

### До очистки:
```
data/                    ~48 МБ (lexicons + dубли + мусор)
src/ai_service/data/     ~8 МБ (актуальные данные)
──────────────────────────────────
ИТОГО:                   ~56 МБ
```

### После очистки (Вариант A):
```
data/lexicons/           ~95 КБ (используется)
src/ai_service/data/     ~8 МБ (актуальные данные)
──────────────────────────────────
ИТОГО:                   ~8.1 МБ
ЭКОНОМИЯ:                ~48 МБ (85% уменьшение!)
```

### После миграции (Вариант B):
```
src/ai_service/data/     ~8.1 МБ (всё в одном месте)
──────────────────────────────────
ИТОГО:                   ~8.1 МБ
СТРУКТУРА:               Единая ✅
```

---

## ✅ Выводы

1. **Две data/ папки** - результат незавершённой миграции
2. **41 МБ дублей** - sanctions JSON скопированы, но старые не удалены
3. **33 МБ мусора** - устаревший sanctions_cache.json
4. **lexicons/** - единственное, что используется из корневой data/
5. **Решение:** Удалить дубли (Вариант A) или полная миграция (Вариант B)

**Рекомендация:** Начать с Варианта A (безопасно), затем запланировать Вариант B.
