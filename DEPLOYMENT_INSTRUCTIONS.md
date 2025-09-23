# Deployment Instructions - Context Filtering Fixes

## Changes Made

### 1. Payment Context Filtering ✅
- Added "сплата" to all payment lexicons
- **Files modified**: `payment_context.txt`, `stopwords.py`, `lexicon.py`

### 2. Insurance Context Filtering ✅
- Added comprehensive insurance terms: страховий, поліс, ОСЦПВ, КАСКО
- **Files modified**: `payment_context.txt`, `stopwords.py`, `lexicon.py`

### 3. Transport Context Filtering ✅
- Added transport terms: поповнення, транспортна, карти, проїзд, etc.
- **Files modified**: `payment_context.txt`, `stopwords.py`, `lexicon.py`

## Current Status

✅ **Code pushed** to remote repository
⚠️ **Server restart required** - changes not yet applied
🔍 **Feature flags working** - factory implementation correctly chosen

## Required Steps

### 1. Restart Production Server

The changes are in the code but require server restart to load new lexicons:

```bash
# SSH to production server
ssh production-server

# Navigate to service directory
cd /path/to/ai-service

# Pull latest changes
git pull origin main

# Restart the service (choose appropriate method)
# Option A: Docker restart
docker-compose restart ai-service

# Option B: Systemd restart
sudo systemctl restart ai-service

# Option C: Manual restart
pkill -f "python.*main.py"
python src/ai_service/main.py &
```

### 2. Verify Deployment

After restart, test with the transport example:

```bash
curl -X POST 'http://95.217.84.234:8000/process' \
-H 'Content-Type: application/json' \
-d '{
  "text": "Поповнення транспортної карти 1000",
  "options": {
    "flags": {
      "use_factory_normalizer": true,
      "normalization_implementation": "factory"
    }
  }
}'
```

**Expected result after restart:**
```json
{
  "normalized_text": "",  // Empty - transport terms filtered
  "tokens": [],
  "signals": {
    "organizations": [],  // No false person entities
    "persons": []
  }
}
```

**Current result (before restart):**
```json
{
  "normalized_text": "Транспортна Поповнення",  // ❌ Wrong
  "tokens": ["Транспортна", "Поповнення"],
  "signals": {
    "persons": [{"core": ["Поповнення", "транспортна"]}]  // ❌ False person
  }
}
```

### 3. Test Cases for Verification

After restart, test all context types:

```bash
# Test 1: Payment context
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Сплата за послуги 100 грн"}'
# Expected: Payment terms filtered, no false names

# Test 2: Insurance context
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Страховий платіж за поліс ОСЦПВ"}'
# Expected: Insurance terms filtered, no false names

# Test 3: Transport context
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Поповнення транспортної карти метро"}'
# Expected: Transport terms filtered, no false names

# Test 4: Real names (should still work)
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Хамін Владислав Ігорович"}'
# Expected: Names correctly extracted and normalized
```

## Rollback Plan

If issues occur, rollback to previous version:

```bash
# Revert to previous commit
git reset --hard HEAD~3

# Restart service
docker-compose restart ai-service
```

## Monitoring

Check server logs for:
- ✅ `"Using factory implementation for language=uk"` (factory used)
- ✅ `"Filtered stop word: 'поповнення'"` (transport terms filtered)
- ✅ `"Filtered stop word: 'сплата'"` (payment terms filtered)
- ❌ Any new errors or performance issues

## Files Changed

```
data/lexicons/payment_context.txt          # Added 50+ new terms
src/ai_service/data/dicts/stopwords.py     # Added to STOP_ALL
src/ai_service/layers/variants/templates/lexicon.py  # Added to all language sets
```

## Commits Applied

1. `fix(normalization): add "сплата" to payment context filters`
2. `fix(normalization): add insurance context filtering`
3. `fix(normalization): add transport context filtering`

---

**Next Action Required**: Server restart to apply lexicon changes.