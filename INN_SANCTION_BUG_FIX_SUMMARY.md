# Sanctioned INN Detection Bug - Fix Summary

## Problem Statement
**Input**: "Дарья ПАвлова ИНН 2839403975"
**Current Behavior**: Returns `risk_level: "low"` (incorrect)
**Expected Behavior**: Should return `risk_level: "high"` because INN 2839403975 belongs to sanctioned person "Якубов Руслан Рішатович"

## Root Causes Identified

### 1. **Code Bug: Duplicate Code Blocks** (FIXED)
- **Location**: `src/ai_service/layers/signals/signals_service.py` lines 1588-1737
- **Issue**: The INN extraction code was copy-pasted 3 times, causing the INN to be added multiple times with incorrect types
- **Fix Applied**: Removed duplicate blocks, kept single implementation with `inn_found` flag to prevent re-adding

### 2. **Production Deployment Issue** (NEEDS DEPLOYMENT)
- **Issue**: The `sanctioned_inns_cache.json` file is likely not deployed to production
- **Evidence**:
  - Test passes locally showing sanctioned detection works
  - Production output shows INN extracted but NOT marked as sanctioned
  - This indicates the cache lookup is failing in production

## The Fix

### Code Changes Made
```python
# src/ai_service/layers/signals/signals_service.py (lines 1588-1626)
# SINGLE CLEAN IMPLEMENTATION - removed 2 duplicate blocks

# ИЩЕМ ИНН В NOTES - это фикс для проблемы когда ИНН отсекается нормализацией
notes = entry.get('notes', '')
if 'marker_инн_nearby' in notes or 'marker_inn_nearby' in notes:
    token_text = entry.get('token', '')
    if token_text and token_text.isdigit() and len(token_text) >= 10:
        import re
        inn_pattern = r'(?:(?:ИНН|инн|INN)\s*[\:\:]?\s*)?(\d{10,12})'
        inn_matches = list(re.finditer(inn_pattern, text))

        inn_found = False  # FLAG TO PREVENT DUPLICATES
        for match in inn_matches:
            inn_value = match.group(1)
            if inn_value == token_text or len(token_text) == 10:
                position = match.span(1)

                # Создаем ID для ИНН с правильной валидацией
                is_valid = validate_inn(inn_value)
                inn_id_info = {
                    "type": "inn",  # ✅ CORRECT TYPE
                    "value": inn_value,
                    "raw": match.group(0),
                    "name": "Taxpayer ID (INN)",
                    "confidence": 0.9 if is_valid else 0.6,
                    "position": position,
                    "valid": is_valid,
                    "source": "normalization_trace_inn"
                }

                person_ids.append(inn_id_info.copy())
                self.logger.warning(f"🔍 ID TRACE: Found INN '{inn_value}' from marker_инн_nearby in trace (valid={is_valid})")
                inn_found = True  # SET FLAG
                break

        # Если не нашли ИНН pattern, НЕ добавляем как numeric_id
        if not inn_found:
            self.logger.debug(f"🔍 ID TRACE: Token '{token_text}' with marker_инн_nearby but no INN pattern match")
```

### Fast Path Cache Check Enhancement
The `_check_sanctioned_inn_cache` method was updated to:
1. Check ALL INNs regardless of validation status (even invalid INNs can be sanctioned)
2. Add detailed logging for debugging
3. Mark matched INNs with `sanctioned: true` flag

## Verification

### Local Test Results ✅
```bash
python tests/integration/test_sanctioned_inn_fix.py

✅ INN 2839403975 found with correct type='inn'
✅ INN 2839403975 marked as sanctioned
✅ Sanctioned name: Якубов Руслан Рішатович
```

### Cache Verification ✅
```bash
python test_inn_cache_direct.py

✅ FOUND: Якубов Руслан Рішатович
✅ INN '2839403975' exists as key in cache
```

## Deployment Steps

### 1. Run Diagnostic on Production (FIRST)
```bash
# Copy and run diagnostic script
scp diagnose_production_inn_cache.py root@95.217.84.234:/opt/ai-service/
ssh root@95.217.84.234 "cd /opt/ai-service && python diagnose_production_inn_cache.py"
```

### 2. Deploy the Fix
```bash
# Use the deployment script
./deploy_inn_cache_fix.sh

# Or manually:
# 1. Copy cache file
scp src/ai_service/data/sanctioned_inns_cache.json root@95.217.84.234:/opt/ai-service/src/ai_service/data/

# 2. Copy fixed code
scp src/ai_service/layers/signals/signals_service.py root@95.217.84.234:/opt/ai-service/src/ai_service/layers/signals/

# 3. Copy cache module
scp src/ai_service/layers/search/sanctioned_inn_cache.py root@95.217.84.234:/opt/ai-service/src/ai_service/layers/search/

# 4. Restart service
ssh root@95.217.84.234 "systemctl restart ai-service"
```

### 3. Verify Fix in Production
```bash
# Test the endpoint
curl -X POST http://95.217.84.234/model \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья ПАвлова ИНН 2839403975"}'

# Expected: risk_level: "high" with sanctioned INN detected
```

## Key Files

1. **Code Fix**: `src/ai_service/layers/signals/signals_service.py`
2. **Cache Data**: `src/ai_service/data/sanctioned_inns_cache.json` (19,789 sanctioned INNs)
3. **Cache Module**: `src/ai_service/layers/search/sanctioned_inn_cache.py`
4. **Integration Test**: `tests/integration/test_sanctioned_inn_fix.py`
5. **Diagnostic Script**: `diagnose_production_inn_cache.py`
6. **Deployment Script**: `deploy_inn_cache_fix.sh`

## Impact

Once deployed, this fix will:
1. Correctly identify sanctioned INNs in the FAST PATH (O(1) lookup)
2. Return `risk_level: "high"` for sanctioned entities
3. Prevent duplicate INN extraction with wrong types
4. Improve overall sanctions detection accuracy

## Additional Notes

- The INN 2839403975 is formally valid according to Russian/Ukrainian INN validation
- The person "Якубов Руслан Рішатович" is in Ukrainian sanctions list
- The fast path cache provides immediate detection without Elasticsearch queries
- Even invalid INNs are now checked against sanctions (important for data quality issues)