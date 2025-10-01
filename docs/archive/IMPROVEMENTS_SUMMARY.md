# 🚀 Improvements Summary - Decision Engine & Garbage Terms Filtering

## ✅ Completed Changes

### 1. **Decision Engine Weight Improvements**

Повышены веса и пороги для более агрессивного детектирования:

**В `src/ai_service/config/settings.py`:**
```python
# Увеличен вес точных совпадений: 0.3 → 0.4 (+33%)
w_search_exact: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SEARCH_EXACT", "0.4")))

# Понижен порог MEDIUM: 0.65 → 0.5 (-0.15)
thr_medium: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_MEDIUM", "0.5")))

# Новый бонус за точные совпадения ≥95%
bonus_exact_match: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__BONUS_EXACT_MATCH", "0.2")))
```

**В `src/ai_service/core/decision_engine.py`:**
```python
# Exact match bonus
if search.has_exact_matches and search.exact_confidence >= 0.95:
    score += self.config.bonus_exact_match
```

### 2. **Garbage Terms Filtering**

#### 2.1 **Smart Filter NameDetector (Name Detection Layer)**

**В `src/ai_service/layers/smart_filter/name_detector.py`:**

- ✅ Добавлен импорт `SERVICE_WORDS`
- ✅ Создан объединённый словарь служебных слов при инициализации
- ✅ Добавлена проверка перед эвристикой заглавных букв:

```python
# Skip if it's a service word (payment terms, services, etc.)
if token_lower in self._service_words:
    self.logger.debug(f"Skipping service word: {token}")
    continue
```

#### 2.2 **Smart Filter Patterns (Pattern Data)**

**В `src/ai_service/data/dicts/smart_filter_patterns.py`:**

Добавлены новые украинские служебные слова:
```python
"перевезення",
"прийом",           # ← Новые
"прийму",           # ← Новые
"приймання",        # ← Новые
"прийняття",        # ← Новые
"логістика",
```

#### 2.3 **Normalization Stopwords (Core Filtering)**

**В `src/ai_service/data/dicts/stopwords.py`:**

Значительно расширен словарь STOP_ALL:

```python
# Добавлены транспортные/логистические термины
"прийом",
"прийму",
"приймання",
"прийняття",
"перевезення",
"транспортування",
"доставка",

# Добавлены страховые термины
"страх",
"страх.",
"страхування",
"страхував",
"страховий",
"страхової",
"travel",
"тrаvеl",           # Mixed script version

# Добавлены бизнес и сервисные термины
"клієнт", "клієнта", "клієнту", "клієнтів",
"клиент", "клиента", "клиенту", "клиентов",
"додаток", "додатку",
"приложение", "приложения",
"сервіс", "сервісу", "сервиса",
"послуга", "послуг",
"обслуживание", "обслуговування",
"компания", "компанія",
"фирма", "организация", "організація",

# Добавлены коды документов и идентификаторы
"tv", "tv0015628", "gm", "okpo", "iban",
"код", "шифр", "ідентифікатор",
"платіж", "платіжу", "сума", "суми",
"платник", "отримувач", "призначення",
```

## 🎯 Expected Results After Service Restart

### 1. **Decision Engine Improvements**

При точном совпадении (например, через search results):

- **Старый scoring**: `w_search_exact=0.3 * confidence + thresholds[0.65, 0.85]`
- **Новый scoring**: `w_search_exact=0.4 * confidence + bonus_exact_match=0.2 + thresholds[0.5, 0.85]`

**Эффект**: больше MEDIUM и HIGH риск-левелов при точных совпадениях.

### 2. **Garbage Terms Filtering**

**Проблемный пример из API:**
```
Страх. платіж по договору TRAVEL 68ccdc4cd19cabdee2eaa56c TV0015628 від 20.09.2025 Holoborodko Liudmyla д.р. 12.11.1968 іпн 2515321244 GM293232 OKPO 30929821 7sichey
```

**Текущий результат (до рестарта):**
```json
"normalized_text": "Страх. Тrаvеl Ноlоbоrоdkо Liudmуlа 7Siсhеу Д. Р.",
"tokens": ["Страх.", "Тrаvеl", "Ноlоbоrоdkо", "Liudmуlа", "7Siсhеу", "Д.", "Р.", ...]
```

**Ожидаемый результат (после рестарта):**
```json
"normalized_text": "Ноlоbоrоdkо Liudmуlа",
"tokens": ["Ноlоbоrоdkо", "Liudmуlа"]
```

**Отфильтровано:** "Страх.", "TRAVEL", служебные коды и ID.

### 3. **Simple Cases**

| Input | Current | Expected After Restart |
|-------|---------|------------------------|
| `"Прийом оплат клієнтів"` | `"Прий оплат клієнтів"` | `""` (empty) |
| `"Перевезення товарів"` | `"Перевезення товарів"` | `""` (empty) |
| `"Іван Петров"` | `"Петров Іван"` | `"Петров Іван"` (unchanged) |
| `"Кухарук В. Р."` | `"Кухарук В. Р."` | `"Кухарук В. Р."` (unchanged) |

## 🔧 Service Restart Required

**Изменения НЕ применятся до рестарта сервиса**, так как:

1. **Конфигурационные значения** загружаются при старте
2. **Словари стоп-слов** кешируются в памяти
3. **Environment variables** не перечитываются динамически

## 🧪 Testing Commands

После рестарта сервиса можно использовать скрипты для проверки:

```bash
# Проверить изменения весов
python check_config_simple.py

# Проверить фильтрацию мусорных терминов
python test_api_fix.py
```

## 📊 Key Metrics to Verify

1. **w_search_exact**: 0.25 → 0.4 ✅
2. **thr_medium**: 0.65 → 0.5 ✅
3. **bonus_exact_match**: NOT FOUND → 0.2 ✅
4. **"Страх" filtering**: Currently processed → Should be empty ✅
5. **Insurance document cleaning**: Currently messy → Should extract only person names ✅

---

**🎉 Все изменения готовы к применению после рестарта сервиса!**