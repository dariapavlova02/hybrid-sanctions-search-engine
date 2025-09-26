# TIN/DOB Fields Fix

## Problem
Поля `review_required` и `required_additional_fields` были false/пустые даже для HIGH RISK случаев.

**Причина**: Логика требовала `person_confidence >= 0.8`, но реальные значения ~0.6

## Solution
Исправил логику в `src/ai_service/core/decision_engine.py`:

1. **Понизил порог** с 0.8 до 0.6 для person/org confidence
2. **Добавил логику для санкционных совпадений** - если HIGH RISK из-за санкций, всегда требовать TIN/DOB

## Changes Made

```python
# OLD: Слишком высокий порог
has_strong_name_match = (
    inp.signals.person_confidence >= 0.8 or
    inp.signals.org_confidence >= 0.8 or
    (inp.similarity.cos_top and inp.similarity.cos_top >= 0.8)
)

# NEW: Реалистичный порог + санкционная логика
has_sanctions_match = (
    inp.search and inp.search.total_matches > 0 and
    (inp.search.has_exact_matches or inp.search.high_confidence_matches > 0)
)

has_strong_name_match = (
    inp.signals.person_confidence >= 0.6 or  # Lowered from 0.8
    inp.signals.org_confidence >= 0.6 or    # Lowered from 0.8
    (inp.similarity.cos_top and inp.similarity.cos_top >= 0.8) or
    has_sanctions_match  # HIGH RISK from sanctions = always strong match
)
```

## Expected Result

После развертывания:

```bash
curl -X POST "http://95.217.84.234:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Сергій Олійник"}'
```

**Ожидаемый результат**:
```json
{
  "decision": {
    "risk_level": "high",
    "review_required": true,
    "required_additional_fields": ["TIN", "DOB"]
  }
}
```

## Deployment

1. Заменить файл `src/ai_service/core/decision_engine.py`
2. Перезапустить сервис
3. Тестировать на HIGH RISK случаях

Файл: `tin_dob_fix_final.tar.gz`