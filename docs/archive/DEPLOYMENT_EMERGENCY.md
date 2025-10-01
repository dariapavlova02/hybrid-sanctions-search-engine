# 🚨 EMERGENCY DEPLOYMENT REQUIRED

## Server Status: 95.217.84.234:8000
**CRITICAL SECURITY VULNERABILITIES ACTIVE**

---

## ✅ Working Fixes:
- Surname suffix "енк" pattern recognition ✅
- `"Порошенк"` correctly classified as `surname` ✅

## ❌ Missing Critical Fixes:

### 1. **HOMOGLYPH DETECTION DISABLED**
```json
// Current (VULNERABLE):
"risk_level": "low"
// NO homoglyph_detected field

// Expected (SECURE):
"risk_level": "HIGH",
"homoglyph_detected": true,
"homoglyph_analysis": {...}
```

### 2. **SEARCH COMPLETELY DISABLED**
```json
// Current (VULNERABLE):
"search_contribution": 0.0,
"total_hits": 0

// Expected (SECURE):
"search_contribution": > 0,
"total_hits": > 0 (for known persons)
```

### 3. **RISK SCORING NOT UPDATED**
- No +0.85 homoglyph bonus
- Known persons get "low" risk instead of "high"

---

## 🚀 IMMEDIATE DEPLOYMENT NEEDED

### Files to Update on Server:

1. **`src/ai_service/layers/normalization/normalization_service.py`**
   - Add homoglyph analysis integration (lines 519-527)

2. **`src/ai_service/core/decision_engine.py`**
   - Add +0.85 homoglyph score bonus (lines 164-168)

3. **`src/ai_service/core/unified_orchestrator.py`**
   - Add search service auto-initialization (lines 123-134)

4. **`src/ai_service/config/settings.py`** ✅ Already updated
   - ENABLE_SEARCH default = "true" ✅

### Infrastructure Requirements:
- Start Elasticsearch on server
- Load sanctions data into indices
- Restart ai-service process

---

## 🧪 POST-DEPLOYMENT VERIFICATION

### Test 1: Homoglyph Detection
```bash
curl -X POST 'http://95.217.84.234:8000/process' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Liudмуlа Uliаnоvа"}'
```
**Expected**: `"risk_level": "HIGH"`, `"homoglyph_detected": true`

### Test 2: Search Functionality
```bash
curl -X POST 'http://95.217.84.234:8000/process' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Порошенк Петро"}'
```
**Expected**: `"search_contribution": > 0`, `"total_hits": > 0`

### Test 3: Risk Assessment
Both tests should show appropriate HIGH risk for:
- Known sanctioned persons
- Homoglyph attacks

---

## 🎯 SUCCESS CRITERIA

✅ All security vulnerabilities closed
✅ Homoglyph attacks detected and blocked
✅ Search finds known sanctioned persons
✅ Risk assessment accurate for threats

---

## ⏰ URGENCY: IMMEDIATE

**Current Status**: Production server vulnerable to sanctions evasion
**Risk Level**: CRITICAL
**Action Required**: Deploy security fixes within hours