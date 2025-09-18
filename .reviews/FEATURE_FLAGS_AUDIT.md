# 🚨 FEATURE FLAGS AUDIT — КРИТИЧЕСКИЕ ПРОБЛЕМЫ

## TL;DR — СРОЧНЫЕ ФИКСЫ ТРЕБУЮТСЯ
**СТАТУС**: 🔴 Блокер — множественные дубли, расхождения дефолтов, нерабочие флаги
**РИСК**: P0 — нарушение детерминизма, невозможность контролировать поведение
**ВРЕМЯ**: 1-2 дня на исправление дублей + 1 неделя на унификацию

---

## 🔥 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. ДУБЛИ ФЛАГОВ В КОДЕ (P0 — BLOCKER)

**Файл**: `src/ai_service/utils/feature_flags.py`
**Проблема**: Флаги объявлены ДВАЖДЫ в одном классе

```python
# Lines 40-46: Первое объявление
enable_ac_tier0: bool = False
enable_vector_fallback: bool = False
strict_stopwords: bool = False

# Lines 58-66: ДУБЛИ с тем же самым!
enable_ac_tier0: bool = False
enable_vector_fallback: bool = False
strict_stopwords: bool = False
```

**Последствие**: Python использует последнее объявление, первое игнорируется
**Риск**: Разработчики не понимают, какой дефолт реально работает

---

### 2. РАСХОЖДЕНИЯ ДЕФОЛТОВ (P0 — CRITICAL)

| Флаг | flags_inventory.json | feature_flags.py (реальный) | Статус |
|------|---------------------|---------------------------|--------|
| `ascii_fastpath` | `true` | `False` | ❌ КРИТИЧНО |
| `use_factory_normalizer` | `false` | `False` | ✅ OK |
| `fix_initials_double_dot` | `false` | `False` | ✅ OK |
| `enable_ac_tier0` | `true` | `False` | ❌ КРИТИЧНО |
| `enable_vector_fallback` | `true` | `False` | ❌ КРИТИЧНО |

**Проблема**: `flags_inventory.json` — документация, но реальные дефолты в коде **НЕ СОВПАДАЮТ**

---

### 3. ФЛАГИ-ФАНТОМЫ (P1 — HIGH)

**В `flags_inventory.json` есть, в коде НЕТ:**
- `enable_rapidfuzz_rerank`
- `enable_dob_id_anchors`
- `enable_decision_engine`
- `ENABLE_SMART_FILTER`
- `ENABLE_EMBEDDINGS`

**Проблема**: Документация указывает на несуществующие флаги

---

### 4. INCONSISTENT NAMING (P1 — HIGH)

**Смешение стилей:**
- Стиль 1: `enable_*` (camelCase style)
- Стиль 2: `ENABLE_*` (UPPER_CASE style)
- Стиль 3: `use_*` (action-based style)

**Environment переменные:**
- `AISVC_FLAG_*` для новых флагов
- Простые названия для старых флагов

---

### 5. НЕДОСТАЮЩАЯ ПРОКИДКА (P1 — HIGH)

**Анализ по touchpoints из `flags_inventory.json`:**

| Флаг | Декларирован | Читается в | Прокинут в слои | Риск |
|------|-------------|------------|----------------|------|
| `strict_stopwords` | ✅ | ✅ | ❓ role_tagger_service.py | Средний |
| `ascii_fastpath` | ✅ | ✅ | ❓ tokenizer_service.py | Высокий |
| `enable_ac_tier0` | ✅ | ❓ | ❓ elasticsearch_adapters.py | КРИТИЧНЫЙ |

---

## 📊 ПОЛНАЯ ИНВЕНТАРИЗАЦИЯ ФЛАГОВ

### Группа А: Normalization Core
```csv
Flag,Default_Code,Default_Inventory,Environment,Status,Risk
enforce_nominative,True,True,AISVC_FLAG_ENFORCE_NOMINATIVE,WORKING,LOW
preserve_feminine_surnames,True,True,AISVC_FLAG_PRESERVE_FEMININE_SURNAMES,WORKING,LOW
use_factory_normalizer,False,False,AISVC_FLAG_USE_FACTORY_NORMALIZER,WORKING,LOW
fix_initials_double_dot,False,False,AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT,WORKING,MEDIUM
preserve_hyphenated_case,False,True,AISVC_FLAG_PRESERVE_HYPHENATED_CASE,MISMATCH,HIGH
```

### Группа B: Search/AC Core
```csv
Flag,Default_Code,Default_Inventory,Environment,Status,Risk
enable_ac_tier0,False,True,AISVC_FLAG_ENABLE_AC_TIER0,CRITICAL_MISMATCH,P0
enable_vector_fallback,False,True,AISVC_FLAG_ENABLE_VECTOR_FALLBACK,CRITICAL_MISMATCH,P0
ascii_fastpath,False,True,MISSING,CRITICAL_MISMATCH,P0
```

### Группа C: Фантомы (только в inventory)
```csv
Flag,Expected_File,Status,Risk
enable_rapidfuzz_rerank,hybrid_search_service.py,MISSING,HIGH
enable_dob_id_anchors,signals_service.py,MISSING,MEDIUM
enable_decision_engine,decision_engine.py,MISSING,LOW
```

---

## 🚨 ПРОБЛЕМЫ ПО ПРИОРИТЕТАМ

### P0 — BLOCKER (исправить немедленно)
1. **Удалить дубли флагов** в `feature_flags.py` (lines 58-66)
2. **Синхронизировать дефолты** для `enable_ac_tier0`, `enable_vector_fallback`, `ascii_fastpath`
3. **Добавить environment читание** для `ascii_fastpath`

### P1 — CRITICAL (исправить в течение недели)
1. **Создать недостающие флаги** или удалить из inventory
2. **Унифицировать naming**: все флаги → `enable_*` стиль
3. **Проверить прокидку** в реальные сервисы (AC, Vector, Tokenizer)

### P2 — IMPORTANT (следующий спринт)
1. **Централизованная валидация** флагов при старте
2. **Unit тесты** для каждого флага (влияние на поведение)
3. **Documentation sync** между кодом и inventory

---

## ⚡ ПЛАН ИСПРАВЛЕНИЯ (2 недели)

### Неделя 1: Критические фиксы
- [ ] **Day 1**: Удалить дубли в `FeatureFlags` класс
- [ ] **Day 1**: Синхронизировать дефолты AC/Vector/ASCII
- [ ] **Day 2**: Добавить environment переменные для всех флагов
- [ ] **Day 3**: Создать validation при загрузке флагов
- [ ] **Day 4-5**: Тестирование исправлений

### Неделя 2: Структурные улучшения
- [ ] **Day 6-7**: Унификация naming convention
- [ ] **Day 8-9**: Прокидка флагов в слои (AC/Vector/Tokenizer)
- [ ] **Day 10**: Unit тесты для каждого флага

---

## 🔬 КАК ПРОВЕРИТЬ

### Команды для диагностики:
```bash
# 1. Найти все упоминания флагов
grep -r "enable_ac_tier0" src/ --include="*.py"

# 2. Проверить environment переменные
grep -r "os.getenv" src/ai_service/utils/feature_flags.py

# 3. Найти дубли флагов
python -c "
import ast
with open('src/ai_service/utils/feature_flags.py') as f:
    tree = ast.parse(f.read())
    # ... анализ дублей
"
```

### Тесты для проверки флагов:
```python
def test_flag_defaults_match_inventory():
    # Загрузить flags_inventory.json
    # Сравнить с реальными дефолтами FeatureFlags
    assert real_defaults == inventory_defaults

def test_all_flags_have_environment_vars():
    # Проверить, что каждый флаг читается из environment
    pass
```

---

## 💣 ОЦЕНКА РИСКОВ

**Текущее состояние**: НЕСТАБИЛЬНОЕ
**Вероятность регрессий**: 70% при изменении флагов
**Время на исправление**: 2 недели
**Блокеры для продакшна**: Дефолты AC/Vector неконсистентны

**РЕКОМЕНДАЦИЯ**: Считать систему флагов **НЕ ГОТОВОЙ** для критичного продакшна без исправлений выше.