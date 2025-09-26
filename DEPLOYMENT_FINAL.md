# FINAL DEPLOYMENT - All Fixes

## Summary of ALL Changes

### 1. ✅ Homoglyph Normalization Fixed
**Problem**: "Liudмуla Ulianova" wasn't normalized to "Liudmula Ulianova"
**Solution**: Fixed mapping to convert Cyrillic→Latin (was Latin→Cyrillic)
**Result**: Mixed scripts properly normalized to single script (Latin)

### 2. ✅ Vector Search False Positives Fixed
**Problem**: "Дарья Павлова Юрьевна" getting HIGH RISK from weak vector matches
**Solution**: Strict thresholds for vector matches (≥0.90)
**Already working on production!**

### 3. ✅ TIN/DOB Fields Added
**Problem**: Missing `review_required` and `required_additional_fields` in API
**Solution**: Added fields to decision output
**Already working on production!**

### 4. ✅ Stopwords Updated
**Added**: Russian "сумма" and all its cases to filter out payment amounts

## Files to Deploy (4 files)

Archive: `homoglyph_fixes_final.tar.gz`

1. **src/ai_service/layers/normalization/homoglyph_detector.py**
   - Fixed Cyrillic→Latin mapping (was backwards)
   - Now properly normalizes "мула" → "mula"

2. **src/ai_service/core/unified_orchestrator.py**
   - Always checks for homoglyphs in search query
   - Normalizes before searching

3. **src/ai_service/core/decision_engine.py**
   - Removed automatic HIGH RISK for homoglyphs
   - Let normalized text search normally

4. **src/ai_service/data/dicts/stopwords.py**
   - Added "сумма", "суммы", "сумме", "суммой", "сумму"
   - Will filter out payment amounts

## Deployment Instructions

```bash
# On server 95.217.84.234
cd /root/ai-service

# Stop services
docker-compose -f docker-compose.prod.yml down

# Extract files
tar -xzf homoglyph_fixes_final.tar.gz

# Restart services
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for startup
sleep 30

# Test homoglyph normalization
curl -X POST "http://95.217.84.234:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Liudмуla Ulianova"}' | jq '.normalized_text'

# Expected: "Liudmula Ulianova" (all Latin)
```

## Expected Results After Deployment

### Test 1: Homoglyph Normalization
**Input**: "Liudмуla Ulianova"
**Expected normalized_text**: "Liudmula Ulianova"
**Expected search query**: "Liudmula Ulianova"

### Test 2: Stopwords
**Input**: "Сумма платежа 1000"
**Expected normalized_text**: "платежа 1000" (сумма removed)

### What's Already Working
- ✅ `high_confidence_matches: 0` for weak vector matches
- ✅ `review_required` and `required_additional_fields` in API response

## Critical Note
Only 2 files REALLY need updating on production:
1. `homoglyph_detector.py` - for proper normalization
2. `unified_orchestrator.py` - to use the normalization

The other changes are already partially working!