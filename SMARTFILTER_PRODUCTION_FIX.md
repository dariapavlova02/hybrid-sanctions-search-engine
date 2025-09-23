# 🚨 SmartFilter Production Fix - Personal Names Issue

## 🔍 Problem Analysis

**Symptom:** Valid personal names are being skipped by SmartFilter with `"smartfilter_skip"`.

**Evidence:**
- ❌ `"Дарья Павлова"` → SKIPPED
- ❌ `"Кухарук Вікторія"` → SKIPPED
- ❌ `"John Smith"` → SKIPPED
- ✅ `"Іван Петров"` → PROCESSED (Ukrainian chars detected)
- ⚠️ `"Прийом оплат"` → PROCESSED (should be blocked!)

## 🎯 Root Cause

SmartFilter confidence calculation is **too strict for simple personal names**:

1. **Language Detection Issues**: Names without context get poor language scores
2. **Low Name Recognition**: Simple 2-word names get insufficient confidence
3. **Threshold Too High**: `min_processing_threshold` blocks valid names

## 🛠️ Production Fix Strategy

### **Option 1: Environment Variable Override (RECOMMENDED)**

Set environment variable to lower the threshold:

```bash
export AI_SMARTFILTER__MIN_PROCESSING_THRESHOLD=0.001
```

**Current values:**
- `smart_filter_patterns.py`: `0.001` (already low)
- `constants.py`: `0.3` (too high - likely active)

### **Option 2: Service Restart with Updated Code**

Our code changes include:
- Enhanced language patterns with names from dictionaries
- Improved SERVICE_WORDS filtering
- Better name detection logic

## 🚀 Immediate Production Fix

**Step 1: Set Environment Variable**
```bash
# On production server (95.217.84.234:8002)
export AI_SMARTFILTER__MIN_PROCESSING_THRESHOLD=0.001
```

**Step 2: Restart Service**
```bash
# Restart the AI service to load new threshold
sudo systemctl restart ai-service
# OR
pm2 restart ai-service
# OR kill and restart process
```

**Step 3: Verify Fix**
```bash
curl -X POST http://95.217.84.234:8002/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья Павлова"}'
```

**Expected Result:**
```json
{
  "decision": {
    "risk_level": "medium",  // NOT "skip"
    "decision_reasons": [...] // NOT ["smartfilter_skip"]
  }
}
```

## ⚡ Alternative Quick Fix

If environment variables don't work, **temporarily modify constants.py**:

```python
# In src/ai_service/constants.py, line 78:
"min_processing_threshold": 0.001,  # Changed from 0.3
```

## 🧪 Test Cases After Fix

| Input | Current | Expected After Fix |
|-------|---------|-------------------|
| `"Дарья Павлова"` | `skip` | `medium/high` |
| `"Кухарук Вікторія"` | `skip` | `medium/high` |
| `"John Smith"` | `skip` | `low/medium` |
| `"Іван Петров"` | `high` | `high` (unchanged) |
| `"Прийом оплат"` | `low` | `skip` (should block) |

## 📊 Environment Variables Reference

**SmartFilter related:**
```bash
AI_SMARTFILTER__MIN_PROCESSING_THRESHOLD=0.001
AI_SMARTFILTER__HIGH_THRESHOLD=0.7
AI_SMARTFILTER__MEDIUM_THRESHOLD=0.5
```

**Decision Engine (already applied):**
```bash
AI_DECISION__W_SEARCH_EXACT=0.4
AI_DECISION__THR_MEDIUM=0.5
AI_DECISION__BONUS_EXACT_MATCH=0.2
```

## 🔍 Monitoring Commands

**Check if fix is working:**
```bash
# Test simple names
curl -X POST http://95.217.84.234:8002/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья Павлова"}' | jq '.decision.risk_level'

# Should return: "medium" or "high", NOT "skip"
```

**Check current threshold:**
```bash
# Look for threshold in decision_details
curl -X POST http://95.217.84.234:8002/process \
  -H "Content-Type: application/json" \
  -d '{"text": "test", "options": {"flags": {"debug_tracing": true}}}' | jq '.decision.decision_details'
```

## 🎉 Success Criteria

✅ **"Дарья Павлова"** returns `risk_level != "skip"`
✅ **"John Smith"** returns `risk_level != "skip"`
✅ **"Кухарук Вікторія"** returns `risk_level != "skip"`
✅ **Insurance garbage terms** still get filtered appropriately

---

**Priority: 🔥 CRITICAL** - This affects all personal name processing in production.