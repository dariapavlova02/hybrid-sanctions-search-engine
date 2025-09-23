# 🚨 URGENT: Decision Engine Fix - AC Search Not Contributing to Risk Score

## ❗ Critical Issue Identified

**Проблема**: AC поиск находит прямые совпадения, но риск остается "low" вместо "high"

**Root Cause**: В decision engine отсутствует параметр `search=inp.search`, из-за чего AC результаты игнорируются при расчете риска.

## 🔍 Proof of Issue

**Test**: `curl -X POST http://95.217.84.234:8002/process -H "Content-Type: application/json" -d '{"text": "Петро Порошенко"}'`

**AC Search Results**: ✅ **WORKING**
```json
{
  "search_results": {
    "results": [
      {
        "score": 200.3004,
        "confidence": 1.0,
        "search_mode": "ac"
      }
    ],
    "total_hits": 2
  }
}
```

**Decision Engine**: ❌ **BROKEN**
```json
{
  "decision": {
    "risk_level": "low",    // ДОЛЖЕН БЫТЬ "high"
    "risk_score": 0.255,
    "score_breakdown": {
      // ОТСУТСТВУЕТ search_contribution !!!
      "smartfilter_contribution": 0.075,
      "person_contribution": 0.18,
      "similarity_contribution": 0.0
    }
  }
}
```

## ✅ Fix Applied (in src/ai_service/core/decision_engine.py:58)

**Before**:
```python
safe_input = DecisionInput(
    text=inp.text,
    language=inp.language,
    smartfilter=smartfilter,
    signals=signals,
    similarity=similarity
    # MISSING: search=inp.search
)
```

**After**:
```python
safe_input = DecisionInput(
    text=inp.text,
    language=inp.language,
    smartfilter=smartfilter,
    signals=signals,
    similarity=similarity,
    search=inp.search  # ← FIX: ADD THIS LINE
)
```

## 🚀 Deployment Instructions

### Option 1: Manual File Update (Fastest)

```bash
# On production server (95.217.84.234)
cd /root/ai-service
cp src/ai_service/core/decision_engine.py src/ai_service/core/decision_engine.py.backup

# Edit line 58 in decision_engine.py to add:
search=inp.search

# Restart service
docker-compose restart ai-service
# OR
systemctl restart ai-service
```

### Option 2: Git Pull + Restart

```bash
# On production server
cd /root/ai-service
git pull origin main  # Contains commit 51e80c4
docker-compose restart ai-service
```

### Option 3: Copy Fixed File via Upload

Upload the fixed file `/Users/dariapavlova/Desktop/ai-service/src/ai_service/core/decision_engine.py` to production server.

## 🧪 Expected Results After Fix

**Test**: Same test with "Петро Порошенко"

**Expected Decision Engine**:
```json
{
  "decision": {
    "risk_level": "high",     // ← FIXED
    "risk_score": 0.85+,      // ← HIGHER DUE TO AC MATCHES
    "score_breakdown": {
      "search_contribution": 0.25+,  // ← NOW PRESENT
      "smartfilter_contribution": 0.075,
      "person_contribution": 0.18
    }
  }
}
```

## 📋 Verification Checklist

After deployment, verify:

1. ✅ AC search still works: `total_hits > 0`
2. ✅ Decision includes search contribution: `search_contribution > 0`
3. ✅ Risk level changes to "high" for direct AC matches
4. ✅ Vector search fallback still works when no AC matches

## 🎯 Impact

- **Before**: AC finds sanctions matches → still shows "low risk" → FALSE NEGATIVE
- **After**: AC finds sanctions matches → shows "high risk" → CORRECT DETECTION

This fix resolves the core issue where direct AC pattern matches were not contributing to risk assessment, causing dangerous false negatives in sanctions screening.

## 📝 Commit Reference

**Fixed in commit**: `51e80c4 - fix(decision): add missing search parameter to DecisionInput`