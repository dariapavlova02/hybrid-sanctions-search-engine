# INN Cache Fix Deployment Guide

## Problem Summary
The sanctions detection system was showing "low risk" for "Дарья Павлова ИНН 2839403975" even though INN 2839403975 belongs to sanctioned person Якубов Руслан.

## Fixes Applied (Commit: 9f791e4)

### Fix 1: Order of Operations (signals_service.py:477-484)
**Problem**: `_check_sanctioned_inn_cache()` was called BEFORE `_enrich_persons_with_ids()`, so the `persons` array was empty when FAST PATH tried to enrich with sanctioned data.

**Solution**: Reordered operations to enrich IDs first, then check INN cache:
```python
# OLD:
self._check_sanctioned_inn_cache(unique_person_ids, unique_org_ids, persons, organizations)
self._enrich_organizations_with_ids(organizations, unique_org_ids)
self._enrich_persons_with_ids(persons, unique_person_ids)

# NEW:
self._enrich_organizations_with_ids(organizations, unique_org_ids)
self._enrich_persons_with_ids(persons, unique_person_ids)
self._check_sanctioned_inn_cache(unique_person_ids, unique_org_ids, persons, organizations)
```

### Fix 2: ID Deduplication Priority (signals_service.py:1599-1602)
**Problem**: For INN 2839403975, the system found two IDs but prioritized `numeric_id` from trace over `inn` from extractor.

**Solution**: Modified sorting to prioritize INN types first:
```python
group.sort(key=lambda x: (
    x.get('type') not in ['inn', 'inn_ua', 'inn_ru'],  # INN типы первые
    x.get('source') != 'normalization_trace',  # trace вторые  
    -x.get('confidence', 0)  # потом по confidence
))
```

### Fix 3: Invalid INN Handling (signals_service.py:1650-1653)
**Problem**: INN 2839403975 fails checksum validation but is a real sanctioned INN that should be checked regardless.

**Solution**: Modified FAST PATH to check INN types regardless of validation:
```python
# INN независимо от валидности
if id_value and id_value.isdigit() and len(id_value) >= 10 and id_type in ['inn', 'inn_ua', 'inn_ru']:
    all_ids_to_check.append((id_value, 'person', id_info))
elif id_value and id_value.isdigit() and len(id_value) >= 10 and id_info.get('valid', True):  # Остальные только если валидные
    all_ids_to_check.append((id_value, 'person', id_info))
```

## Deployment Steps

### Step 1: Pull Latest Changes
```bash
cd /app
git pull origin main
```

### Step 2: Verify Changes
```bash
# Check that commit 9f791e4 is present
git log --oneline -3

# Verify fixes are in the code
grep -A 5 "_enrich_persons_with_ids(persons, unique_person_ids)" src/ai_service/layers/signals/signals_service.py
grep -A 3 "x.get('type') not in \['inn'" src/ai_service/layers/signals/signals_service.py
grep -A 2 "id_type in \['inn'" src/ai_service/layers/signals/signals_service.py
```

### Step 3: Rebuild Docker Container
```bash
# Force rebuild to pick up code changes
docker-compose down
docker-compose build --no-cache ai-service
docker-compose up -d ai-service
```

### Step 4: Verify INN Cache
```bash
# Check that target INN is in cache
grep -c "2839403975" src/ai_service/data/sanctioned_inns_cache.json
# Should return: 1

# Verify cache data
python -c "
import json
with open('src/ai_service/data/sanctioned_inns_cache.json', 'r') as f:
    cache = json.load(f)
data = cache.get('2839403975')
if data:
    print(f'INN 2839403975: {data[\"name\"]} ({data[\"type\"]})')
else:
    print('INN 2839403975 not found in cache')
"
```

### Step 5: Test the Fix
```bash
# Test with curl command
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "text": "Дарья Павлова ИНН 2839403975",
    "request_id": "test-inn-production",
    "options": {
      "enable_signals": true,
      "enable_search": true,
      "enable_decision": true
    }
  }' | python -c "
import json
import sys
data = json.load(sys.stdin)
print('Risk level:', data['decision']['risk_level'])
print('ID match:', data['decision']['decision_details']['normalized_features']['id_match'])
print('ID bonus:', data['decision']['decision_details']['score_breakdown']['id_bonus'])
if data['signals']['persons']:
    person = data['signals']['persons'][0]
    print('Person IDs:')
    for pid in person.get('ids', []):
        if pid.get('sanctioned'):
            print(f'  🚨 SANCTIONED: {pid}')
        else:
            print(f'  {pid}')
"
```

### Expected Results
After successful deployment, the test should show:
- `Risk level: high` (or `reject`)
- `ID match: true`
- `ID bonus: > 0.0` (typically 0.5)
- At least one person ID with `sanctioned: true`

### Troubleshooting

#### If still showing low risk:
1. **Check container logs**: `docker-compose logs ai-service`
2. **Verify code inside container**: 
   ```bash
   docker-compose exec ai-service grep -A 3 "id_type in \['inn'" src/ai_service/layers/signals/signals_service.py
   ```
3. **Check if cache is loaded**: Look for cache loading messages in logs
4. **Force complete rebuild**:
   ```bash
   docker-compose down
   docker system prune -f
   docker-compose build --no-cache
   docker-compose up -d
   ```

#### If service won't start:
1. **Check for syntax errors**: `docker-compose logs ai-service`
2. **Verify Python imports**: Make sure all dependencies are installed
3. **Check configuration**: Verify environment variables and config files

## Verification Commands

### Quick Health Check
```bash
# Check service status
docker-compose ps

# Check service health
curl -f http://localhost:8000/health || echo "Service not healthy"
```

### Detailed Test
```bash
# Test multiple INN cases
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "text": "Дарья Павлова ИНН 2839403975",
    "request_id": "test-inn-1",
    "options": {"enable_signals": true, "enable_search": true, "enable_decision": true}
  }' | jq '.decision.risk_level'

curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "text": "Иванов Иван ИНН 123456789012",
    "request_id": "test-inn-2", 
    "options": {"enable_signals": true, "enable_search": true, "enable_decision": true}
  }' | jq '.decision.risk_level'
```

## Contact
If deployment fails or issues persist, check:
1. Docker logs: `docker-compose logs ai-service`
2. Git status: Ensure commit 9f791e4 is present
3. Cache file: Verify `sanctioned_inns_cache.json` contains target INN
4. Network: Ensure service can access external dependencies