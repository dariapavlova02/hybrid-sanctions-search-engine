# Smoke Test Failures Analysis

## Summary
- **Total Tests**: 220
- **Failed**: 20
- **Pass Rate**: 90.9%

## Top 5 Critical Failures

| Test | Symptom | Root Cause | Impact |
|------|---------|------------|--------|
| `test_apostrophes_preservation` | Apostrophe not preserved | Token splitting on `'` breaks name structure | EN names like "O'Connor" become "O Connor" |
| `test_hyphenated_names_preservation` | Hyphenated parts not capitalized | Missing hyphen handling in normalization | Names like "Петров-Сидоров" become empty |
| `test_initials_double_dot_collapse` | Missing collapse_double_dots rule | Double dot collapsing not implemented | "И.. И. Петров" not collapsed to "И. И. Петров" |
| `test_titlecase_person_tokens` | Empty result for hyphenated names | Hyphenated names filtered out completely | "петров-сидоров" → "" instead of "Петров-Сидоров" |
| `test_multi_person_extraction` | Second person not extracted | Multi-person detection not working | "иван петров ковальська" missing "олена ковальська" |

## Detailed Failure Analysis

### 1. Apostrophe Preservation (3 failures)
- **Files**: `test_apostrophes_preservation[ru/uk/en]`
- **Symptom**: `'` not preserved in names
- **Root Cause**: Token splitting on apostrophes in `_classify_english_names()`
- **Fix**: Don't split apostrophes, preserve for nameparser

### 2. Hyphenated Names (6 failures)
- **Files**: `test_hyphenated_names_preservation[ru/uk/en]`, `test_hyphenated_names_titlecase`, `test_hyphenated_name_normalization[ru/uk/en]`
- **Symptom**: Empty results for hyphenated surnames
- **Root Cause**: Hyphenated names filtered out in token processing
- **Fix**: Preserve hyphenated names in token processing

### 3. Double Dot Collapse (3 failures)
- **Files**: `test_initials_double_dot_collapse[ru/uk/en]`, `test_collapse_double_dots_trace`, `test_initials_collapse`
- **Symptom**: Missing `collapse_double_dots` rule in trace
- **Root Cause**: Double dot collapsing not implemented in factory
- **Fix**: Implement double dot collapsing with proper trace

### 4. Multi-person Extraction (2 failures)
- **Files**: `test_multi_person_extraction[ru/uk]`
- **Symptom**: Second person not extracted
- **Root Cause**: Multi-person detection logic not working
- **Fix**: Implement proper multi-person extraction

### 5. Stop Words Filtering (1 failure)
- **Files**: `test_stop_words_filtering`
- **Symptom**: Service word 'sender' not filtered
- **Root Cause**: Stop word filtering not working properly
- **Fix**: Implement proper stop word filtering

## Trace Analysis

### Missing Rules in Trace
- `collapse_double_dots` - Not implemented
- `dedup_consecutive_person_tokens` - Not implemented
- `apostrophe_preserved` - Not implemented
- `hyphenated_name_normalized` - Not implemented

### Expected vs Actual Trace
```
Expected: ['collapse_double_dots', 'role_classification:initial', 'role_classification:surname']
Actual: ['role_classification:initial', 'role_classification:surname', 'assemble_done']
```

## Performance Impact
- **Factory vs Legacy**: 3x faster (5.1ms vs 15.2ms average)
- **Accuracy Trade-off**: 64.5% parity vs 100% legacy accuracy
- **Critical Issues**: 20/220 smoke tests failing

## Priority Fixes

### P0 (Critical)
1. Fix apostrophe splitting in English name processing
2. Implement hyphenated name preservation
3. Fix double dot collapsing
4. Implement proper trace building

### P1 (High)
1. Fix multi-person extraction
2. Implement stop word filtering
3. Fix property test failures

### P2 (Medium)
1. Improve trace completeness
2. Add missing normalization rules
3. Optimize performance while maintaining accuracy

## Test Commands for Verification

```bash
# Run specific failing tests
pytest -q tests/smoke/test_normalization_smoke.py::TestNormalizationSmoke::test_apostrophes_preservation -v
pytest -q tests/smoke/test_normalization_smoke.py::TestNormalizationSmoke::test_hyphenated_names_preservation -v
pytest -q tests/smoke/test_normalization_smoke.py::TestNormalizationSmoke::test_initials_double_dot_collapse -v

# Run all smoke tests
pytest -q tests/smoke -k normalization --tb=short
```

## Expected Results After Fix

- **Apostrophe Preservation**: "O'Connor" → "O'Connor" (not "O Connor")
- **Hyphenated Names**: "Петров-Сидоров" → "Петров-Сидоров" (not empty)
- **Double Dot Collapse**: "И.. И. Петров" → "И. И. Петров"
- **Multi-person**: "иван петров ковальська" → "иван петров олена ковальська"
- **Trace Completeness**: All expected rules present in trace
