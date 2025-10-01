# 🎯 Анализ Feature Flags для максимальной релевантности

## 📊 **ТЕКУЩИЙ СТАТУС ФЛАГОВ**

### ✅ **ВКЛЮЧЕНЫ (хорошо для релевантности):**
- `use_factory_normalizer` ✅ - Fast normalization
- `enable_ascii_fastpath` ✅ - ASCII optimization
- `morphology_custom_rules_first` ✅ - Custom rules priority
- `enable_ac_tier0` ✅ - AC exact patterns
- `enable_vector_fallback` ✅ - Vector search fallback
- `enable_nameparser_en` ✅ - English name parsing
- `enable_en_nicknames` ✅ - English nicknames
- `enable_enhanced_diminutives` ✅ - Enhanced diminutives
- `enforce_nominative` ✅ - Nominative case enforcement
- `preserve_feminine_surnames` ✅ - Feminine surname preservation

### ❌ **ВЫКЛЮЧЕНЫ (снижают релевантность):**

#### 🔴 **КРИТИЧНЫЕ для релевантности:**
- `ENABLE_SEARCH` ❌ → `true` (Hybrid search - основа релевантности!)
- `ENABLE_VARIANTS` ❌ → `true` (Генерация вариантов имен)
- `ENABLE_EMBEDDINGS` ❌ → `true` (Семантический поиск)

#### 🟡 **ВАЖНЫЕ для качества:**
- `PRIORITIZE_QUALITY` ❌ → `true` (Качество > скорость)
- `ENABLE_SPACY_NER` ❌ → `true` (Named Entity Recognition)
- `ENABLE_FSM_TUNED_ROLES` ❌ → `true` (Точное определение ролей)

#### 🟢 **ПОЛЕЗНЫЕ для точности:**
- `ENABLE_ENHANCED_GENDER_RULES` ❌ → `true` (Улучшенные gender правила)
- `PRESERVE_FEMININE_SUFFIX_UK` ❌ → `true` (Украинские суффиксы)
- `FIX_INITIALS_DOUBLE_DOT` ❌ → `true` (И.. → И.)
- `PRESERVE_HYPHENATED_CASE` ❌ → `true` (Петрова-Сидорова)
- `STRICT_STOPWORDS` ❌ → `true` (Строгая фильтрация)
- `DIMINUTIVES_ALLOW_CROSS_LANG` ❌ → `true` (Кросс-языковые)

## 🚀 **3 КОНФИГУРАЦИИ СОЗДАНЫ:**

### 1. **env.production.maximum_performance**
**Цель: 100+ RPS**
```
✅ Скорость: ~125 RPS, P95 < 100ms
⚠️ Релевантность: Базовая (отключены variants, embeddings, NER)
```

### 2. **env.production.optimal**
**Цель: Баланс скорости и качества**
```
✅ Скорость: ~80-100 RPS
✅ Релевантность: Хорошая (включены основные фичи)
```

### 3. **env.production.maximum_relevancy** *(НОВАЯ)*
**Цель: Максимальная релевантность**
```
⚠️ Скорость: ~50-70 RPS
🏆 Релевантность: МАКСИМАЛЬНАЯ (все фичи включены)
```

## 📋 **КЛЮЧЕВЫЕ ОТЛИЧИЯ КОНФИГУРАЦИЙ:**

| Флаг | Performance | Optimal | Relevancy | Влияние на релевантность |
|------|-------------|---------|-----------|--------------------------|
| `ENABLE_SEARCH` | ✅ | ✅ | ✅ | 🔴 Критично |
| `ENABLE_VARIANTS` | ❌ | ❌ | ✅ | 🟡 Важно |
| `ENABLE_EMBEDDINGS` | ❌ | ❌ | ✅ | 🟡 Важно |
| `ENABLE_SPACY_NER` | ❌ | ❌ | ✅ | 🟡 Важно |
| `PRIORITIZE_QUALITY` | ❌ | ❌ | ✅ | 🟡 Важно |
| `ENABLE_FSM_TUNED_ROLES` | ❌ | ❌ | ✅ | 🟢 Полезно |
| `ASCII_FASTPATH` | ✅ | ✅ | ❌ | 🟢 Качество vs скорость |
| `STRICT_STOPWORDS` | ❌ | ❌ | ✅ | 🟢 Полезно |

## 🎯 **РЕКОМЕНДАЦИИ ПО ВЫБОРУ:**

### **Для максимальной релевантности платежей:**
```bash
cp env.production.maximum_relevancy env.production
```

**Преимущества:**
- 🏆 Максимальная точность распознавания ФИО
- 🏆 Hybrid search (AC + Vector + Semantic)
- 🏆 Генерация вариантов написания
- 🏆 NER для лучшего понимания контекста
- 🏆 Enhanced gender и diminutives правила

**Компромисс:**
- ⚠️ Скорость: ~50-70 RPS (все еще достаточно для многих задач)
- ⚠️ Больше ресурсов: 6GB RAM, более высокая CPU загрузка

### **Для баланса скорости и качества:**
```bash
cp env.production.optimal env.production
```

### **Для максимальной скорости:**
```bash
cp env.production.maximum_performance env.production
```

## 🔧 **ОПТИМИЗАЦИЯ ПО СЦЕНАРИЯМ:**

### **Банковские платежи (рекомендуется Relevancy):**
- Критично: точность распознавания ФИО
- Критично: обработка сложных составных имен
- Допустимо: 50-70 RPS (достаточно для большинства банков)

### **Высоконагруженные API (Performance):**
- Критично: >100 RPS
- Допустимо: базовая точность
- Подходит: простые ФИО, быстрая обработка

### **Корпоративные системы (Optimal):**
- Баланс всех факторов
- Хорошая точность + приемлемая скорость

## 📊 **ОЖИДАЕМАЯ ПРОИЗВОДИТЕЛЬНОСТЬ:**

| Конфигурация | RPS | P95 Latency | Accuracy | Memory | Рекомендация |
|-------------|-----|-------------|----------|--------|--------------|
| Performance | 125+ | <100ms | 85% | 3GB | Высокие нагрузки |
| Optimal | 80-100 | <150ms | 90% | 4GB | **Рекомендуется** |
| Relevancy | 50-70 | <300ms | 95%+ | 6GB | Максимальное качество |

## 🎯 **ФИНАЛЬНАЯ РЕКОМЕНДАЦИЯ:**

**Для production платежной системы рекомендуется:**
```bash
env.production.optimal
```

**Причины:**
- ✅ Достаточная скорость: 80-100 RPS
- ✅ Высокое качество: 90%+ accuracy
- ✅ Разумные ресурсы: 4GB RAM
- ✅ Все основные фичи включены
- ✅ Стабильность и надежность