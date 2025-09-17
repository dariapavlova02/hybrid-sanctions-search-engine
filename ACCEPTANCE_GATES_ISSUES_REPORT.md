# 🚨 Acceptance Gates Issues Report

## 📋 Summary

**Status:** ❌ **REJECTED** - PR should NOT be merged

**Issue:** Missing dependencies causing parity tests to fail

**Impact:** 8.3% parity success rate (2/24 tests) - below 90% threshold

## 🔍 Detailed Analysis

### 1. Parity Tests Failed

**Russian (RU):** 1/8 (12.5%) ❌
**Ukrainian (UK):** 1/8 (12.5%) ❌  
**English (EN):** 0/8 (0.0%) ❌

**Root Cause:** Missing dependencies causing factory normalization to fail

### 2. Missing Dependencies

#### 2.1 spaCy Module
```
ERROR: No module named 'spacy'
WARNING: spaCy not available. Install with: pip install spacy
```

**Impact:**
- Russian NER processing fails
- Ukrainian NER processing fails
- English NER processing fails

**Solution:**
```bash
pip install spacy
python -m spacy download en_core_web_sm
python -m spacy download uk_core_news_sm
```

#### 2.2 nameparser Module
```
WARNING: English name parsing failed: No module named 'nameparser'
```

**Impact:**
- English name parsing fails
- English normalization completely broken

**Solution:**
```bash
pip install nameparser
```

#### 2.3 Import Path Issues
```
ERROR: No module named 'src.ai_service.layers.utils'
```

**Impact:**
- Factory normalization fails
- All language processing affected

**Solution:**
- Fix import paths in normalization factory
- Ensure proper module structure

### 3. Morphological Normalization Issues

```
WARNING: Morphological normalization failed: 'tuple' object has no attribute 'normalized'
```

**Impact:**
- Token processing fails
- Normalization results empty

**Solution:**
- Fix morphological adapter return type handling
- Ensure proper result object structure

## ✅ Tests Passing

### Performance Tests
- **P95:** 0.008s (threshold: 0.010s) ✅
- **P99:** 0.012s (threshold: 0.020s) ✅
- **All performance gates:** ✅ PASSED

### Search Integration
- **AC Tier 0/1:** ✅ All tests passing
- **KNN + Hybrid:** ✅ All tests passing
- **Vector Fallback:** ✅ All tests passing

### Property Tests
- **All 10 properties:** ✅ PASSED
- **Hypothesis-based testing:** ✅ PASSED

### Smoke Tests
- **All 8 smoke tests:** ✅ PASSED
- **Basic functionality:** ✅ PASSED

### E2E Tests
- **All 7 E2E tests:** ✅ PASSED
- **Sanctions processing:** ✅ PASSED

## 🔧 Required Fixes

### 1. Install Dependencies
```bash
# Install required packages
pip install spacy nameparser

# Download spaCy models
python -m spacy download en_core_web_sm
python -m spacy download uk_core_news_sm
```

### 2. Fix Import Issues
```python
# Fix in normalization_factory.py
# Change:
from src.ai_service.layers.utils import flag_propagation
# To:
from ...utils import flag_propagation
```

### 3. Fix Morphological Adapter
```python
# Fix return type handling
# Ensure proper NormalizationResult object structure
```

### 4. Update Test Configuration
```python
# Add dependency checks in test setup
# Skip tests if dependencies missing
# Provide clear error messages
```

## 📊 Expected Results After Fixes

### Parity Tests
- **Russian (RU):** 8/8 (100%) ✅
- **Ukrainian (UK):** 8/8 (100%) ✅
- **English (EN):** 8/8 (100%) ✅
- **Overall:** 24/24 (100%) ✅

### Performance Tests
- **P95:** <0.010s ✅
- **P99:** <0.020s ✅
- **All gates:** ✅ PASSED

### All Other Tests
- **Search Integration:** ✅ PASSED
- **Property Tests:** ✅ PASSED
- **Smoke Tests:** ✅ PASSED
- **E2E Tests:** ✅ PASSED

## 🚀 Next Steps

### 1. Immediate Actions
1. **Install Dependencies**
   ```bash
   pip install spacy nameparser
   python -m spacy download en_core_web_sm
   python -m spacy download uk_core_news_sm
   ```

2. **Fix Import Issues**
   - Update import paths in normalization factory
   - Fix morphological adapter return types

3. **Re-run Validation**
   ```bash
   ./scripts/simple_validation.sh
   ```

### 2. Verification
1. **Check Parity Results**
   - Ensure 90%+ success rate for all languages
   - Verify factory normalization works correctly

2. **Verify Performance**
   - Ensure P95 ≤ 10ms, P99 ≤ 20ms
   - Check performance impact of dependencies

3. **Test All Features**
   - Verify all feature flags work correctly
   - Test shadow mode validation

### 3. Final Validation
1. **Run Complete Test Suite**
   ```bash
   pytest tests/ -v
   ```

2. **Generate Final Report**
   ```bash
   python scripts/acceptance_summary.py
   ```

3. **Verify Acceptance Criteria**
   - Parity ≥ 90% for all languages
   - Performance thresholds met
   - All integration tests passing

## 📝 Files to Update

### 1. Dependencies
- `pyproject.toml` - Add spacy and nameparser
- `requirements.txt` - Add spaCy models

### 2. Code Fixes
- `src/ai_service/layers/normalization/processors/normalization_factory.py`
- `src/ai_service/layers/normalization/processors/morphology_adapter.py`

### 3. Test Updates
- `tests/parity/test_golden_parity.py`
- `tests/performance/test_performance_gates.py`

## 🎯 Success Criteria

After fixes, all gates must pass:

- ✅ **Parity (Golden) ≥ 90%** по RU/UK/EN (каждый сабсет)
- ✅ **P95 ≤ 10ms, P99 ≤ 20ms** (короткие строки, perf_micro)
- ✅ **Search: AC Tier-0/1 + kNN fallback** — зелёные интеграционные
- ✅ **Property-tests + Smoke** — зелёные (без xfail)
- ✅ **Все фичи были ВКЛЮЧЕНЫ в shadow-mode**

## 📋 Current Status

| Gate | Status | Details |
|------|--------|---------|
| Parity (RU) | ❌ | 12.5% - Missing spacy |
| Parity (UK) | ❌ | 12.5% - Missing spacy |
| Parity (EN) | ❌ | 0.0% - Missing nameparser |
| Performance | ✅ | All thresholds met |
| Search Integration | ✅ | All tests passing |
| Property Tests | ✅ | All tests passing |
| Smoke Tests | ✅ | All tests passing |
| E2E Tests | ✅ | All tests passing |

**Overall:** ❌ **REJECTED** - Dependencies missing, parity tests failing

**Action Required:** Install dependencies and fix import issues before merge
