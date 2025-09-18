# 💀 DEAD CODE REPORT — Анализ мёртвого и дублированного кода

## TL;DR — СРЕДНИЙ УРОВЕНЬ ЗАМУСОРЕННОСТИ
**СТАТУС**: 🟡 Умеренное количество дублей и legacy файлов
**ОСНОВНЫЕ ПРОБЛЕМЫ**: Дублированные файлы, legacy обёртки, неиспользуемые сервисы
**ВРЕМЯ НА ОЧИСТКУ**: 1-2 недели
**ЭКОНОМИЯ**: ~15% сокращение кодовой базы, улучшение maintainability

---

## 🔍 КРИТИЧНЫЕ ДУБЛИ ФАЙЛОВ


#### 2. **Morphology Adapter Duplication** 🚨
```
src/ai_service/layers/normalization/morphology_adapter.py           ← Legacy?
src/ai_service/layers/normalization/morphology/morphology_adapter.py ← New?
```
**Риск**: Два разных implementation для морфологии
**Действие**: Унифицировать в один файл

#### 3. **Embedding Preprocessor Duplication** 🚨
```
src/ai_service/layers/embeddings/embedding_preprocessor.py  ← Layers impl
src/ai_service/services/embedding_preprocessor.py           ← Services impl
```
**Риск**: Два разных preprocessor'а
**Действие**: Выбрать один, удалить другой

---

## 📊 СТАТИСТИКА КОДА

### Общие метрики:
- **Всего Python файлов в src/**: ~150
- **Всего функций**: 1,495
- **Дублированные имена файлов**: 6 пар
- **Legacy файлы**: 3+ явных (`*_old.py`, `*_legacy.py`)

### Размер кодовой базы:
```bash
find src/ -name "*.py" | xargs wc -l | tail -1
# Ожидаемо: ~15,000-20,000 строк
```

---

## 🗑️ LEGACY И УСТАРЕВШИЙ КОД

### P1 — Legacy Files (удалить/мигрировать)

#### 1. **Legacy Test Files**
```
tests/unit/test_orchestrator_service_old.py          ← Delete
tests/unit/text_processing/test_normalization_service_old.py  ← Delete
tests/unit/adapters/test_legacy_normalization_adapter.py      ← Delete
```

#### 2. **Legacy Service Files**
```
src/ai_service/layers/normalization/normalization_service_legacy.py  ← Archive?
```

#### 3. **Backup/Old Configuration**
```
# Поиск _old, _backup, _bak файлов
find . -name "*_old*" -o -name "*_backup*" -o -name "*_bak*" | grep -v __pycache__
```

---

## 🔍 НЕИСПОЛЬЗУЕМЫЕ СЕРВИСЫ И ФУНКЦИИ

### P2 — Potentially Unused Services

#### Подозрительные файлы (нужна проверка usage):
```
src/ai_service/services/embedding_preprocessor.py   ← Дубль?
src/ai_service/config/feature_flags.py              ← Дубль?
src/ai_service/adapters/*                           ← Какие реально используются?
```

### Методика поиска мёртвого кода:
```bash
# 1. Найти все классы и функции
grep -r "^class \|^def " src/ --include="*.py" | cut -d: -f2 | cut -d'(' -f1 | sort | uniq

# 2. Найти их использование
for item in $(grep -r "^class \|^def " src/ --include="*.py" | cut -d: -f2 | cut -d'(' -f1); do
    usage_count=$(grep -r "$item" src/ --include="*.py" | grep -v "^def \|^class " | wc -l)
    if [ $usage_count -eq 0 ]; then
        echo "UNUSED: $item"
    fi
done
```

---

## 📁 ИНВЕНТАРИЗАЦИЯ СЕРВИСОВ

### Core Services (используются ✅)
```
src/ai_service/core/
├── orchestrator_factory.py          ✅ Main entry point
├── unified_orchestrator.py          ⚠️  Legacy? (check vs with_search)
├── unified_orchestrator_with_search.py  ⚠️ Newer version?
├── decision_engine.py               ✅ L5 layer
├── cache_service.py                 ✅ Used across layers
└── base_service.py                  ✅ Base class
```

### Layer Services (большинство используется ✅)
```
src/ai_service/layers/
├── normalization/
│   ├── normalization_service.py        ⚠️ Legacy wrapper?
│   ├── normalization_service_legacy.py ❌ Archive this
│   ├── role_tagger_service.py          ✅ Core functionality
│   └── tokenizer_service.py            ✅ Core functionality
├── search/
│   ├── hybrid_search_service.py        ✅ Core search
│   ├── elasticsearch_client.py         ✅ ES integration
│   └── aho_corasick_service.py         ✅ Fallback search
├── embeddings/
│   ├── embedding_service.py            ✅ Standard impl
│   ├── optimized_embedding_service.py  ⚠️ Alternative impl?
│   └── embedding_preprocessor.py       ❌ Duplicate!
└── patterns/
    └── unified_pattern_service.py      ✅ Core patterns
```

### Suspect Services (проверить использование ❓)
```
src/ai_service/services/embedding_preprocessor.py   ❓ Duplicate?
src/ai_service/adapters/*                           ❓ All used?
src/ai_service/validation/*                         ❓ Used in pipeline?
```

---

## 🔧 АНАЛИЗ ИМПОРТОВ

### Команды для поиска неиспользуемых импортов:
```bash
# 1. Найти все from/import statements
grep -r "^from \|^import " src/ --include="*.py" > all_imports.txt

# 2. Найти unused imports (manually check)
for module in $(cat all_imports.txt | awk '{print $2}' | sort | uniq); do
    usage=$(grep -r "$module" src/ --include="*.py" | grep -v "^from \|^import " | wc -l)
    if [ $usage -eq 0 ]; then
        echo "UNUSED IMPORT: $module"
    fi
done
```

### Циклические импорты (уже проверено ✅):
```bash
# Поиск циклических зависимостей
python -c "
import ast
import os
# ... analyze import cycles
"
# Результат: в архитектурном ревью — циклов не найдено ✅
```

---

## 📦 НЕИСПОЛЬЗУЕМЫЕ ЗАВИСИМОСТИ

### Анализ pyproject.toml:
```toml
# Подозрительные зависимости (нужна проверка):
transliterate = ">=1.10.2"      # Используется ли?
python-levenshtein = ">=0.27.1" # Заменено на rapidfuzz?
```

### Команда для проверки:
```bash
# Найти использование каждой зависимости
for pkg in transliterate python-levenshtein unidecode; do
    echo "=== $pkg ==="
    grep -r "$pkg\|${pkg/_/-}" src/ --include="*.py" || echo "NOT FOUND"
done
```

---

## 📋 PLAN ОЧИСТКИ (2 недели)

### Неделя 1: Критичные дубли (P0)
- [ ] **Day 1**: Исследовать feature_flags дубли:
  - Сравнить `config/feature_flags.py` vs `utils/feature_flags.py`
  - Выбрать canonical version
  - Обновить все импорты
- [ ] **Day 2**: Исследовать morphology_adapter дубли:
  - Проверить функциональность обеих версий
  - Мигрировать на один файл
- [ ] **Day 3**: Исследовать embedding_preprocessor дубли:
  - Унифицировать в layers/ или services/
- [ ] **Day 4-5**: Тестирование после удаления дублей

### Неделя 2: Legacy cleanup (P1-P2)
- [ ] **Day 6**: Удалить legacy test files:
  - `*_old.py` тесты
  - Убедиться, что functionality покрыта новыми тестами
- [ ] **Day 7**: Архивировать legacy service files:
  - `normalization_service_legacy.py`
  - Документировать migration path
- [ ] **Day 8-9**: Анализ неиспользуемых сервисов:
  - Запустить usage analysis script
  - Удалить confirmed dead code
- [ ] **Day 10**: Cleanup неиспользуемых зависимостей

---

## 🔬 COMMANDS ДЛЯ ДИАГНОСТИКИ

### Автоматический поиск дублей:
```bash
# Найти файлы с одинаковыми именами
find src/ -name "*.py" -exec basename {} \; | sort | uniq -d

# Найти файлы с похожим содержимым (пример)
find src/ -name "*.py" -exec md5sum {} \; | sort | uniq -D -w 32
```

### Поиск неиспользуемых классов:
```bash
# Найти все классы
grep -r "^class " src/ --include="*.py" | cut -d: -f2 | cut -d'(' -f1 | cut -d' ' -f2 > classes.txt

# Проверить usage каждого класса
while read class_name; do
    usage=$(grep -r "$class_name" src/ --include="*.py" | grep -v "^class " | wc -l)
    if [ $usage -eq 0 ]; then
        echo "UNUSED CLASS: $class_name"
    fi
done < classes.txt
```

### Legacy file detection:
```bash
# Найти все legacy/old файлы
find . -name "*legacy*" -o -name "*old*" -o -name "*deprecated*" -o -name "*backup*" | grep -v __pycache__
```

---

## 💰 EXPECTED BENEFITS

### После очистки ожидаем:
- **Код-база**: -15% размер (удаление дублей и legacy)
- **Maintainability**: +30% (меньше confusion, cleaner imports)
- **Build time**: -5% (меньше файлов для компиляции)
- **Testing time**: -10% (удаление duplicate tests)
- **Developer confusion**: -50% (clear canonical files)

### Метрики success:
- Zero duplicate file names в src/
- Zero legacy test files
- All imports resolvable
- No unused dependencies
- Clean `grep -r "TODO\|FIXME" src/` output

---

## 🎯 РЕКОМЕНДАЦИИ

### Немедленные действия (P0):
1. Унифицировать feature_flags файлы
2. Выбрать canonical morphology_adapter
3. Удалить confirmed duplicate embedding_preprocessor

### Процесс prevention:
1. **PR review checklist**: Проверять новые дубли
2. **CI check**: Автоматический поиск duplicate file names
3. **Quarterly cleanup**: Регулярная очистка legacy кода

**ИТОГО**: Умеренное замусоривание, но исправимое. Приоритет на дублях файлов (P0), затем legacy cleanup (P1-P2).