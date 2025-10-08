# INN Cache Fix Deployment Instructions

## Problem Summary
The system was showing "low risk" for "Дарья Павлова ИНН 2839403975" even though INN 2839403975 belongs to a sanctioned person (Якубов Руслан). The INN cache (КЖШ) exists and contains the correct data, but FAST PATH logic was not working.

## Root Cause Analysis
Two issues were identified:

1. **Wrong order of operations**: `_check_sanctioned_inn_cache()` was called BEFORE `_enrich_persons_with_ids()`, so `persons` array was empty when FAST PATH tried to enrich with sanctioned data.

2. **Incorrect ID deduplication**: For INN 2839403975, the system found two IDs:
   - `numeric_id` from normalization trace (confidence 0.95)
   - `inn` from identifier extractor (confidence 0.6)
   
   The deduplication logic prioritized trace over extractor, so `numeric_id` was used instead of `inn`.

## Fixes Applied

### Fix 1: Change order of operations in `signals_service.py`
```python
# OLD (lines 477-481):
self._check_sanctioned_inn_cache(unique_person_ids, unique_org_ids, persons, organizations)
self._enrich_organizations_with_ids(organizations, unique_org_ids)
self._enrich_persons_with_ids(persons, unique_person_ids)

# NEW:
self._enrich_organizations_with_ids(organizations, unique_org_ids)
self._enrich_persons_with_ids(persons, unique_person_ids)
self._check_sanctioned_inn_cache(unique_person_ids, unique_org_ids, persons, organizations)
```

### Fix 2: Update ID deduplication logic in `signals_service.py`
```python
# OLD (lines 1592-1599):
group.sort(key=lambda x: (
    x.get('source') != 'normalization_trace',  # trace первые (False < True)
    -x.get('confidence', 0)  # потом по убывающей confidence
))

# NEW:
group.sort(key=lambda x: (
    x.get('type') not in ['inn', 'inn_ua', 'inn_ru'],  # INN типы первые (False < True)
    x.get('source') != 'normalization_trace',  # trace вторые (False < True)  
    -x.get('confidence', 0)  # потом по убывающей confidence
))
```

## Deployment Steps

### 1. Update the service file
Copy the modified `signals_service.py` to the server:
```bash
scp src/ai_service/layers/signals/signals_service.py root@95.217.84.234:/app/src/ai_service/layers/signals/
```

### 2. Restart the service
```bash
ssh root@95.217.84.234 "cd /app && docker-compose restart ai-service"
```

### 3. Wait for service startup
```bash
sleep 10
```

### 4. Test the fix
```bash
curl -X POST "http://95.217.84.234:8000/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "text": "Дарья Павлова ИНН 2839403975",
    "request_id": "test-inn-fixed",
    "options": {
      "enable_signals": true,
      "enable_search": true,
      "enable_decision": true
    }
  }'
```

## Expected Results After Fix

The response should show:
- `risk_level: "high"` (instead of "low")
- `id_match: true` (instead of false)
- `id_bonus: 0.15` (instead of 0.0)
- Person IDs should include an entry with `"sanctioned": true`

## Verification Commands

### Check INN cache is working:
```bash
curl -X GET "http://95.217.84.234:8000/health" | jq '.components.search_service.fallback_services'
```

### Check service is processing correctly:
```bash
curl -X GET "http://95.217.84.234:8000/health/detailed" | jq '.orchestrator.processed_total'
```

## Files Modified

1. `src/ai_service/layers/signals/signals_service.py`:
   - Lines 477-481: Order of operations fix
   - Lines 1592-1599: ID deduplication logic fix

## Cache Status

The INN cache is already generated and contains 19,789 sanctioned INNs including the target INN 2839403975 (Якубов Руслан Рішатович). The cache is automatically loaded at service startup.

## Business Impact

After this fix, any query containing a sanctioned INN will immediately trigger:
- `id_match: true`
- `id_bonus: 0.15` 
- High risk score (typically > 0.7)
- Automatic rejection/review required

This ensures compliance with business rules that require automatic high risk for any sanctioned INN match, regardless of name similarity.