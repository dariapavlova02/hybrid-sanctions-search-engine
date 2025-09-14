
# Project Rules — AI Normalization & Signals

## 0) Цели проекта

* Нормализовать персональные имена и core-части компаний.
* Сигналы: выделить структуру (person/org + legal forms, dob, ids).
* Работать детерминированно, объяснимо (TokenTrace для normalization, evidence для signals).
* Строго разделять обязанности:

  * **Normalization** = канон имён/организаций (без форм и метаданных).
  * **Signals** = обогащение и структурирование (legal form, DOB, INN, EDRPOU и т.п.).
* Не дублировать Smart Filter/NameDetector — у нас только жёсткие правила и детекция сигналов.

---

## 1) Запреты (anti-overshoot)

❌ Никаких хардкодов под тесты/строки.
❌ Не обходить тесты ради «зелёного» — исправляем причину.
❌ Не тянуть Smart Filter в нормализацию — у нас свои слои.
❌ Не морфить английские имена в кириллическом контексте.
❌ Не конвертировать женские фамилии в мужские.
❌ Не держать списки юр. форм в Normalization (только в Signals).

---

## 2) Рабочий цикл

1. Малый инкремент.
2. Показать `git diff`.
3. Запустить релевантные тесты (unit → integration).
4. Коммит: атомарный, осмысленный.
5. Если ошибка — приложить одну трассу (TokenTrace/Signals evidence).

---

## 3) Ветки и коммиты

* Фича-ветка: `feat/<scope>`
* Сообщения:

  * `chore(packaging): editable install & test collection ok`
  * `feat(signals): birthdate parsing and ISO normalization`
  * `fix(tagging): filter legal acronyms as unknown; no fallback`
  * `perf(cache): lru_cache on morphology`
  * `docs: update README and docstrings`

---

## 4) Слои


# Логика работы по слоям

## 0. Вход / Контракты

**Вход:** `text: str`, опц. `hints: {language?, flags?}`
**Выход (верхний уровень Orchestrator):**

```json
{
  "original_text": "...",
  "language": "ru|uk|en",
  "language_confidence": 0.0-1.0,
  "normalized_text": "чистое ФИО + ядра компаний",
  "tokens": ["..."],
  "trace": [...],                  // TokenTrace по выведенным токенам
  "signals": {                     // Сервис сигналов
    "persons": [...],
    "organizations": [...],
    "numbers": {...},             // inn / edrpou / ogrn / etc.
    "dates": {...},               // birth_dates, other_dates
    "confidence": 0.0-1.0
  },
  "variants": [...],              // опционально
  "embeddings": [...],            // опционально
  "processing_time": ...,
  "success": true,
  "errors": []
}
```

---

## 1) Validation & Sanitization (Input)

**Задача:** базовая проверка и безопасная очистка.
**Делает:**

* trim, collapse spaces, ограничение длины, удаление явного бинарного мусора.
* early-block (например, только цифры/символы) → короткий ответ `should_process=false` (опционально).
  **Не делает:** языковых/морфологических преобразований.
  **Выход:** `sanitized_text`, предупреждения.

---

## 2) Smart Filter (предварительная оценка)

**Задача:** быстро решить, «имеет смысл» дорогая обработка.
**Вход:** `sanitized_text` (в оригинальном виде).
**Детекторы:**

* `NameDetector`: заглавные, инициалы, патронимные хвосты, никнеймы/уменьшительные.
* `CompanyDetector`: юр. формы (ООО/ТОВ/LLC/Inc…), банковские/организационные триггеры, кавычные ядра.
* контекст платежа (триггеры: платеж/оплата/в пользу/за услуги и т.п.).
  **Скоринг:** веса сигналов → `confidence` + классификация: `must_process | recommend | maybe | skip`.
  **Не делает:** нормализации/лемматизации.
  **Выход:** `FilterResult {should_process, confidence, detected_signals, details}`.

> Если `skip` — можно остановиться (конфигурируемо). Иначе — дальше.

---

## 3) Language Detection

**Задача:** определить основной язык текста (ru/uk/en) + доверие.
**Принципы:**

* быстрые эвристики (алфавит, частотные токены) → словари → ML (fallback).
* mixed-script допускается (основной язык один, ASCII-токены учитываются отдельно на нормализации).
  **Выход:** `language`, `language_confidence`.

---

## 4) Unicode Normalization

**Задача:** привести символы к каноническим формам.
**Делает:**

* NFKC/NFKD нормализацию (по конфигу), маппинг диакритики, homoglyph-safe замены (ё→е при необходимости), кавычки к стандарту, дефисы/апострофы к норме.
  **Не делает:** токенизацию по смыслу.
  **Выход:** `text_unicode_normalized`.

---

## 5) Name Normalization (Morph NormalizationService)

**Задача:** вывести **канон ФИО** и **ядра названий компаний**, детально трассируя правила.
**Флаги (обязателен реальный эффект):**

* `remove_stop_words`: true/false — чистка STOP\_ALL в токенизаторе.
* `preserve_names`: true/false — сохранять `. - '` (инициалы/двойные фамилии/O’Brien). Если false — агрессивнее сплитим.
* `enable_advanced_features`: true/false — морфология + diminutives + гендер фамилий; если false — минимум (кейсинг, инициалы, фильтр unknown).
  **Пайплайн:**

1. **Tokenize & Noise-strip**

   * унификация кейса; выделение кавычных токенов; мягкая фильтрация мусора; сохранение знаков имён, если `preserve_names`.
2. **Role Tagging**

   * `initial` (в т.ч. автосплит `"П.І."` → `["П.", "І."]`), `patronymic` (регексы c падежами), `given` (словари имен/уменьшительных), `surname` (паттерны -енко, -ов/-ова, -ський/-ська, -ук/-юк/-чук, -ян, -дзе …), `unknown`.
   * **ORG\_ACRONYMS** (ООО/ТОВ/LLC …) → всегда `unknown` (или `legal_form`) и **не участвуют** в позиционных дефолтах.
   * позиционные дефолты (first→given, last→surname) **только** для нейтральных токенов и **никогда** для стоп-словаря/акронимов/явного контекста.
3. **Normalize by Role**

   * `initial` → формат `X.`
   * `given/surname/patronymic`:

     * если `enable_advanced_features`: морфология (pymorphy3 ru/uk), выбор лучшего парса (Name/Surn + `nomn`, иначе lemma), **после** — diminutives DIM2FULL (ru/uk, + en nicknames).
     * гендер фамилии: сохраняем женскую форму; в сомнениях — остаёмся на исходной женской, не «омужичиваем».
     * **ASCII-токены при ru/uk**: морфологию **не** применяем, только капитализация и позиционные роли.
4. **Reconstruct**

   * собираем **только** персональные токены (unknown/context — отбрасываются), нормализуем пробелы, фиксируем `TokenTrace` (token, role, rule, morph\_lang?, normal\_form?, output, fallback, notes?).
   * параллельно собираем `organizations.core` из кавычных/орг-токенов (не попадает в `normalized`).
     **Выход:**
     `NormalizationResult { normalized, tokens, trace, organizations.core?, language, confidence?, token_count, lengths, processing_time, success }`.

> Важно: **юридические формы** (ООО/ТОВ/LLC) из нормализации не уходят в `normalized` — это задача Signals собрать их в полное имя организации.

---

## 6) Signals (обогащение поверх нормализации)

**Задача:** извлечь структуру сигналов из **оригинального текста** + **trace/organizations.core** из нормализации.
**Делает:**

* **Организации**:

  * `legal_form`: из словаря (ООО/ТОВ/LLC/Inc/Bank/…);
  * `core`: из `NormalizationResult.organizations.core` (кавычные и явные ядра);
  * `full`: `legal_form + "core"` (учёт кавычек), варианты написания (регистры/кавычки).
  * confidence по сигналам (legal\_form + quoted core + банковские триггеры).
* **Персоны**:

  * ФИО-строки и токены из `normalized` + позиции в исходном тексте (по сопоставлению);
  * quality метки (есть ли patronymic, инициалы и т.п.).
* **Документы/номера**:

  * `numbers`: `inn/itn`, `edrpou`, `ogrn`, `kpp` и т.п. — по шаблонам/контексту.
* **Даты рождения**:

  * date patterns (дд.мм.гггг, ISO, текстом), контекстные ключи (`дата рождения`, `DOB`, `р.`, `born`, `д/р`).
  * нормализация в `YYYY-MM-DD`, доп. `precision` (day|month|year).
* **Скоринг**: веса сигналов + бонусы за согласованность (например, legal\_form + quoted core).
  **Не делает:** морфологию.
  **Выход:** `signals { organizations[], persons[], numbers{}, dates{}, confidence }`.

---

## 7) Variants (опционально)

**Задача:** на базе нормализованного ФИО/ядра генерировать варианты:

* морфологические (падежи), типографские (инициалы, дефис), транслитерация, фонетические.
  **Вход:** нормализованный результат.
  **Выход:** `variants: [..]`, `token_variants: {token: [...]}`.

---

## 8) Embeddings (опционально)

**Задача:** векторизация для семантического поиска/сопоставления (sentence-transformers).
**Вход:** normalized/variants.
**Выход:** `embeddings`.

---

## 9) Decision & Response

**Задача:** собрать итог, проставить статусы, метрики, ошибки.
**Делает:** измерение времени этапов, агрегация ошибок, финальные флаги `success`.

---

# Границы ответственности (что где НЕ делаем)

* **NormalizationService**:

  * не восстанавливает полное название компании с юр. формой;
  * не извлекает даты/идентификаторы;
  * не делает тяжёлых поисков/сопоставлений;
  * не решает «обрабатывать или нет» — это Smart Filter.

* **Smart Filter**:

  * не нормализует и не меняет текст;
  * не склеивает `legal_form + core`;
  * не генерирует варианты.

* **Signals**:

  * не морфологизирует;
  * не детектит язык;
  * не решает пропуск этапов (только отдаёт confidence по сигналам).

---

# Правила-ключи (суммарно)

* ORG\_ACRONYMS всегда `unknown` для нормализованного ФИО и **не участвуют** в позиционных дефолтах.
* ASCII-токены в ru/uk режиме — не морфить.
* Женские фамилии не «омужичивать».
* `enable_advanced_features=False` — без морфологии/словарей, только кейс/инициалы/фильтр.
* Все `unknown` и контекстные слова (союзы/глаголы) — **вне** `normalized`.
* Полные названия компаний собирает **Signals** (legal\_form + quoted core).

---

# Мини-псевдокод (сквозной)

```python
def process(text):
    inp = validate(text)
    filt = smart_filter.should_process(inp.text)
    if not filt.should_process and config.allow_skip:
        return minimal_response(inp.text, filt)

    lang = language.detect(inp.text)
    uni  = unicode.normalize(inp.text)

    norm = morph_normalize.normalize_async(
        uni,
        language=lang.code,
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True
    )
    sigs = signals.extract(
        original_text=inp.text,
        norm_trace=norm.trace,
        org_core=norm.organizations.get("core")
    )

    vars = variants.generate(norm.normalized) if config.gen_variants else None
    embs = embedder.encode(norm.normalized)   if config.gen_embeddings else None

    return assemble_response(inp, lang, norm, sigs, vars, embs)
```

---

# Мини-набор приёмочных критериев

* **NormalizationResult**

  * `normalized` содержит только персональные токены (инициалы/имя/отчество/фамилия).
  * `organizations.core` заполнен для кавычных ядёр.
  * `TokenTrace` есть на каждый выведенный токен.
  * флаги реально ветвят поведение.

* **Signals**

  * `organizations[*].legal_form` из текста;
  * `organizations[*].core` из нормализации;
  * `organizations[*].full` = склейка;
  * `numbers.inn|edrpou|...` и `dates.birth` извлекаются при наличии.

* **Perf**

  * p95 нормализации ≤ 10 мс (короткие строки), благодаря lru\_cache морфологии и ASCII bypass.

---

## 5) Конфигурационные флаги (Normalization)

* `remove_stop_words`: удалять STOP\_ALL или нет.
* `preserve_names`: True → сохраняем `.-'`; False → агрессивно сплитим.
* `enable_advanced_features`: True → morph + diminutives + gender; False → базовый режим (кейсинг, initials).

---

## 6) Словари/паттерны

* **ORG\_ACRONYMS** (Normalization): ооо, тов, llc, ltd, inc, corp, gmbh, ag… → всегда unknown.
* **LEGAL\_FORMS** (Signals): расширенный список (uk/ru/en/eu).
* **Diminutives DIM2FULL**: ru/uk + en nicknames.
* **Surname patterns**: -енко, -ук, -ов/-ова, -ський/-ська, -ян, -дзе…
* **Patronymic**: -ович, -евич, -івна, -овна и т.п.

---

## 7) Языковая логика

* ru/uk: pymorphy3 analyzers (если advanced).
* ASCII в ru/uk: не морфить, использовать nicknames/role defaults.
* Gender surnames: сохраняем женскую форму.

---

## 8) Контракты

### NormalizationResult

```
{
  normalized: str,
  tokens: [str],
  trace: [TokenTrace],
  errors: [str],
  language: str,
  confidence: float|None,
  original_length: int,
  normalized_length: int,
  token_count: int,
  processing_time: float,
  success: bool,
  persons_core: [[str]],
  organizations_core: [str]
}
```

### SignalsResult

```
{
  persons: [ {core, full_name, dob, ids[], confidence, evidence[]} ],
  organizations: [ {core, legal_form, full, ids[], confidence, evidence[]} ],
  extras: {dates[], amounts[]}
}
```

---

## 9) Тест-политика

Минимальный зелёный набор:

* `test_normalization_result_fields.py`
* `test_flags_behavior.py`
* `test_org_acronyms_filter.py`
* `test_role_tagging_extended.py`
* `test_morph_and_diminutives.py`
* `test_ru_uk_sentences.py`
* `test_mixed_script_names.py`
* `test_canary_overfit.py` (мусорные слова не становятся именами).

- сигнальные тесты: `test_signals_contract`, `test_signals_legal_forms`, `test_signals_ids_parse`, `test_signals_dob_parse`, `test_signals_scoring`, `test_pipeline_end_to_end`.

---

## 10) Производительность

* `_morph_nominal` с @lru\_cache.
* Morph только если enable\_advanced\_features=True.
* Логгер предупреждает, если normalize() > 100ms.
* Signals быстрый: только regex + простая близость.

---

## 11) Качество кода

* Стайл: black, isort, flake8.
* Докстринги для ключевых методов обоих сервисов.
* Константы/паттерны — в отдельные модули.
* Никаких магических чисел.

---

## 12) Локальный запуск

* Packaging: pyproject.toml + pip install -e .
* pytest --collect-only -q (быстрая проверка).
* Запуски: unit → integration → e2e.

---

## 13) Definition of Done

* Все тесты зелёные.
* Флаги реально влияют на поведение.
* TokenTrace объясняет каждый токен.
* SignalsResult структурирует org/person/dob/ids.
* Женские фамилии корректные.
* Нет дублирования SmartFilter.
* Докстринги и README обновлены.

---