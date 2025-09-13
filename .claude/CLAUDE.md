
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

### NormalizationService

* **Tokenizer**: чистим мусор (цифры, стоп-слова при remove\_stop\_words=True).
* **Role tagger**: initial | patronymic | given | surname | unknown.

  * ORG\_ACRONYMS всегда unknown.
  * Дефолты только если ≥2 CapStart токенов.
* **Normalize by role**:

  * initial → форматирование (A.).
  * given/surname/patronymic → morph (если enable\_advanced\_features=True) → diminutives → gender adjust.
  * ASCII в ru/uk режиме не морфить.
* **Reconstruct**: собрать токены, фильтровать `unknown`, вернуть NormalizationResult (+ TokenTrace).
* **Output**: `persons_core`, `organizations_core` (без legal\_form/ids/dob).

### SignalsService

* **Legal forms**: словари/регексы, восстанавливает `full_name` (ТОВ + core).
* **IDs**: ИНН, ЕДРПОУ, ОГРН, VAT и т.п. → нормализовать, привязать к org/person.
* **DOB**: искать форматы дат + маркеры (р.н., DOB, born). → нормализовать ISO.
* **Scoring**: confidence 0–1, evidence = список правил/паттернов.
* **Output**: JSON {persons\[], organizations\[], extras{dates, amounts}}.

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