# Homoglyph Normalization Fix

## Problem
System was giving HIGH RISK for all homoglyph attacks (mixed scripts like "Liudмуla Ulianova"), instead of normalizing them and searching in sanctions lists.

## Solution
Changed logic to:
1. **Detect homoglyphs** in search query
2. **Normalize them** to a single script (e.g., "Liudмуla" → "Liudmula")
3. **Search with normalized query** in sanctions lists
4. **Remove automatic HIGH RISK** for homoglyphs

## Changes Made

### 1. src/ai_service/core/unified_orchestrator.py (lines 630-645)
**Before**: Only normalized homoglyphs if `norm_result.homoglyph_detected`
**After**: ALWAYS check for homoglyphs in search query and normalize them

```python
# ALWAYS check for homoglyphs in search query and normalize them
if self.homoglyph_detector and query.strip():
    original_query = query
    # Detect homoglyphs first
    homoglyph_result = self.homoglyph_detector.detect_homoglyphs(query)
    if homoglyph_result and homoglyph_result.get('has_homoglyphs', False):
        # Normalize homoglyphs for search
        normalized_query, transformations = self.homoglyph_detector.normalize_homoglyphs(query)
        if normalized_query != original_query:
            query = normalized_query
            logger.warning(f"🔧 HOMOGLYPH NORMALIZATION FOR SEARCH: '{original_query}' → '{query}'")
```

### 2. src/ai_service/core/decision_engine.py (lines 241-242)
**Before**: Automatic HIGH RISK for homoglyph + sanctions match
**After**: Removed automatic blocking - let normalized homoglyphs go through normal search

## Expected Behavior
- **Input**: "Liudмуla Ulianova" (mixed Latin/Cyrillic)
- **Normalization**: "Liudmula Ulianova" (all Latin)
- **Search**: Look for "Liudmula Ulianova" in sanctions lists
- **Result**: Normal risk assessment based on search results

## Deployment Instructions

1. Stop services:
```bash
cd /root/ai-service
docker-compose -f docker-compose.prod.yml down
```

2. Replace these 2 files with the fixed versions:
   - `src/ai_service/core/unified_orchestrator.py`
   - `src/ai_service/core/decision_engine.py`

3. Restart services:
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

4. Test:
```bash
curl -X POST "http://95.217.84.234:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Liudмуla Ulianova"}' | jq '.homoglyph_detected, .normalized_text, .risk_assessment.level'
```

**Expected result**:
- Still detects homoglyphs for analysis
- But searches with normalized text
- Risk level based on actual search results, not automatic HIGH