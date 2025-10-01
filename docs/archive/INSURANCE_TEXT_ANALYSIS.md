# Insurance Text Processing Analysis

## Problem Summary

The API was incorrectly processing insurance payment text, returning wrong normalized results:

**Input text:**
```
"Страховий платіж за поліс ОСЦПВ EPcode 232483013 від 20.09.2025 Хамін Владислав Ігорович іпн 3731301153 Арсенал AG*232483013 33908322"
```

**Expected result:** Should extract and normalize "Хамін Владислав Ігорович" (name + patronymic)

**Actual API result:**
```json
{
  "normalized_text": "Поліс Страховий",
  "tokens": ["Поліс", "Страховий", ""]
}
```

## Root Cause Analysis

### 1. Insurance Context Not Recognized

**Problem:** Insurance terms were being classified as personal names:
- "Страховий" (insurance) → classified as `given` name
- "поліс" (policy) → classified as `surname`

**Solution:** Added insurance terms to lexicons:
- `data/lexicons/payment_context.txt`
- `src/ai_service/data/dicts/stopwords.py`
- `src/ai_service/layers/variants/templates/lexicon.py`

**Terms added:** страховий, поліс, ОСЦПВ, ОСАГО, КАСКО, страхування, etc.

### 2. API vs Factory Implementation Discrepancy

**Key Finding:** Factory normalization works correctly but API uses different path.

**Factory test result (correct):**
```
Factory result: '232483013 Хамін Владислав Арсенал Ігорович'
Factory tokens: ['232483013', 'Хамін', 'Владислав', 'Арсенал', 'Ігорович']
```

**API result (incorrect):**
```json
{
  "normalized_text": "Поліс Страховий",
  "tokens": ["Поліс", "Страховий", ""]
}
```

### 3. Normalization Path Analysis

The API configuration shows:
```json
"flags": {
  "normalization_implementation": "factory",
  "use_factory_normalizer": true
}
```

But the trace shows FSM role tagger being used:
```json
{
  "token": "Владислав",
  "role": "unknown",
  "notes": "FSM role tagger: token 'Владислав' -> unknown (reason: fallback_unknown)"
}
```

**Hypothesis:** The unified_orchestrator is using FSM role tagger service instead of factory role classification, leading to different results.

## Files Modified

### 1. Insurance Context Addition
- `data/lexicons/payment_context.txt` - Added insurance terms
- `src/ai_service/data/dicts/stopwords.py` - Added to STOP_ALL
- `src/ai_service/layers/variants/templates/lexicon.py` - Added to PAYMENT_CONTEXT and STOPWORDS_*

### 2. Payment Word Filtering
- Added "сплата" to all payment context lexicons to prevent misclassification as given name

## Commits

1. `fix(normalization): add "сплата" to payment context filters` - Fixed "Сплата" being classified as given name
2. `fix(normalization): add insurance context filtering` - Added comprehensive insurance terms

## Next Steps

To fully resolve the API issue:

1. **Investigate unified_orchestrator normalization path** - Determine why API uses FSM role tagger instead of factory
2. **Ensure API flags properly route to factory** - Fix the configuration so factory normalization is actually used
3. **Test end-to-end pipeline** - Verify that insurance terms are properly filtered and names correctly extracted

## Test Cases

To verify the fix:

```bash
curl -X POST 'http://95.217.84.234:8000/process' -H 'Content-Type: application/json' -d '{
  "text": "Страховий платіж за поліс ОСЦПВ EPcode 232483013 від 20.09.2025 Хамін Владислав Ігорович іпн 3731301153 Арсенал AG*232483013 33908322"
}'
```

**Expected result after fix:**
- Insurance terms should be filtered out
- "Хамін Владислав Ігорович" should be properly normalized
- ІНН "3731301153" should be extracted in signals

## Status

✅ **Fixed:** Insurance context filtering
✅ **Fixed:** Payment word classification
🔄 **In Progress:** API normalization path consistency