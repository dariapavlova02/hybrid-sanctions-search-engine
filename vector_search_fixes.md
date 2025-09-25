# Vector Search False Positives Fix

## Problem
System gives HIGH RISK for vector matches with low scores (0.7), causing false positives for unrelated names like "Дарья Павлова Юрьевна" matching "Рашникова Ольга Вікторівна".

## Root Cause
The `high_confidence_matches` calculation in `search_contracts.py` was using lenient thresholds for vector matches, allowing weak semantic similarities to be classified as high confidence.

## Fixed Files

### 1. src/ai_service/contracts/search_contracts.py
**Issue**: Vector matches with score 0.7 were counted as high confidence
**Fix**: Strict thresholds - vector ≥ 0.90, AC/fuzzy ≥ 0.80

### 2. src/ai_service/core/unified_orchestrator.py
**Issue**: Using normalized confidence instead of real ES scores
**Fix**: Use actual ES scores in candidate creation

### 3. src/ai_service/core/decision_engine.py
**Issue**: Same threshold for vector and AC matches
**Fix**: Different thresholds - vector 0.95, AC 0.9

### 4. src/ai_service/config/settings.py
**Issue**: Decision engine disabled by default
**Fix**: Enable decision engine, set vector thresholds

## Deployment Instructions

1. Stop current services:
```bash
cd /root/ai-service
docker-compose -f docker-compose.prod.yml down
```

2. Replace the 4 fixed files with the versions from this fix package

3. Restart services:
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

4. Test the fix:
```bash
curl -X POST "http://95.217.84.234:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья Павлова Юрьевна"}' | jq '.search.high_confidence_matches'
```

**Expected result**: Should show 0 instead of 10

## Debug Logs
The fix includes debug logging that will show:
```
🔍 DEBUG: Processing N candidates for high_confidence_matches
📊 Candidate 0: score=0.71, is_vector=true, threshold=0.90 → NOT HIGH CONFIDENCE
🎯 FINAL: high_confidence_matches = 0
```

If you don't see these logs, the changes haven't been applied properly.