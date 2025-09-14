# 🚀 AI Service Migration Guide

## Overview

The AI service has been consolidated from multiple orchestrator implementations into a unified architecture that exactly implements the 9-layer specification from CLAUDE.md.

## 🎯 Migration Path

### Before (Deprecated)
```python
# Multiple orchestrator options (all deprecated)
from ai_service.core.orchestrator_service import OrchestratorService
from ai_service.core.orchestrator_v2 import OrchestratorV2
from ai_service.orchestration.clean_orchestrator import CleanOrchestrator

# Old initialization
orchestrator = OrchestratorService(cache_size=10000, default_ttl=3600)

# Old processing
result = await orchestrator.process_text(
    text="Іван Петров",
    generate_variants=True,
    generate_embeddings=True
)
```

### After (New Unified Architecture)
```python
# Single orchestrator via factory
from ai_service.core.orchestrator_factory import OrchestratorFactory

# New initialization
orchestrator = await OrchestratorFactory.create_production_orchestrator()

# New processing with explicit flags
result = await orchestrator.process(
    text="Іван Петров",
    # Normalization flags (real behavior impact)
    remove_stop_words=True,
    preserve_names=True,
    enable_advanced_features=True,
    # Optional stages
    generate_variants=True,
    generate_embeddings=True
)
```

## 🔄 Step-by-Step Migration

### 1. Update Imports
Replace all deprecated imports:

```python
# ❌ OLD (deprecated)
from ai_service.core.orchestrator_service import OrchestratorService
from ai_service.core.orchestrator_v2 import OrchestratorV2
from ai_service.services.core.orchestrator_v2 import OrchestratorV2 as OrchestratorService

# ✅ NEW (unified)
from ai_service.core.orchestrator_factory import OrchestratorFactory
```

### 2. Update Initialization

```python
# ❌ OLD
orchestrator = OrchestratorService(cache_size=10000, default_ttl=3600)
orchestrator = OrchestratorV2(cache_size=10000)

# ✅ NEW
# For production
orchestrator = await OrchestratorFactory.create_production_orchestrator()

# For testing
orchestrator = await OrchestratorFactory.create_testing_orchestrator(minimal=True)

# For custom configuration
orchestrator = await OrchestratorFactory.create_orchestrator(
    enable_smart_filter=True,
    enable_variants=True,
    enable_embeddings=True
)
```

### 3. Update Method Calls

```python
# ❌ OLD methods
result = await orchestrator.process_text(text, generate_variants=True)
result = await orchestrator.normalize_text(text, language="uk")
batch_results = await orchestrator.process_batch(texts)

# ✅ NEW methods
result = await orchestrator.process(
    text=text,
    generate_variants=True,
    remove_stop_words=True,     # Real flag behavior
    preserve_names=True,        # Real flag behavior
    enable_advanced_features=True  # Real flag behavior
)

# Backward compatibility (with deprecation warning)
norm_result = await orchestrator.normalize_async(text, language="uk")
signals_result = await orchestrator.extract_signals(text, norm_result)
```

### 4. Update Result Handling

The new `UnifiedProcessingResult` has enhanced structure:

```python
# ❌ OLD result structure
{
    "original_text": "...",
    "normalized_text": "...",
    "language": "uk",
    "variants": [...],
    "success": true
}

# ✅ NEW result structure (enhanced)
{
    "original_text": "...",
    "language": "uk",
    "language_confidence": 0.9,
    "normalized_text": "...",
    "tokens": [...],
    "trace": [...],                 # NEW: Token-level tracing
    "signals": {                    # NEW: Structured extraction
        "persons": [...],
        "organizations": [...],
        "confidence": 0.85
    },
    "variants": [...],
    "embeddings": [...],
    "processing_time": 0.05,
    "success": true,
    "errors": []
}
```

### 5. Access New Features

```python
result = await orchestrator.process(text="ТОВ Іван Петров")

# Access structured signals
for person in result.signals.persons:
    print(f"Person: {person.core} -> {person.full_name}")
    if person.dob:
        print(f"  DOB: {person.dob}")
    if person.ids:
        print(f"  IDs: {person.ids}")

for org in result.signals.organizations:
    print(f"Org: {org.legal_form} {org.core} -> {org.full_name}")

# Access detailed tracing
for trace in result.trace:
    print(f"Token: {trace.token} -> {trace.role} -> {trace.output}")
    if trace.morph_lang:
        print(f"  Morphology: {trace.morph_lang}")
```

## 📋 Migration Checklist

- [ ] **Update imports** from deprecated orchestrators to `OrchestratorFactory`
- [ ] **Change initialization** to use factory methods
- [ ] **Update method calls** from `process_text()` to `process()`
- [ ] **Add normalization flags** with real behavioral impact
- [ ] **Update result handling** to use new structured format
- [ ] **Access new signals data** (persons, organizations, trace)
- [ ] **Run tests** to ensure functionality works
- [ ] **Remove old orchestrator references**

## 🧪 Testing Migration

Use the migration helper script:

```bash
# Scan for deprecated patterns
python migration_helper.py --scan

# Get interactive migration help
python migration_helper.py --migrate

# Test new architecture
python migration_helper.py --test
```

Run integration tests:

```bash
# Test complete pipeline
python -m pytest tests/integration/test_pipeline_end2end.py -v

# Test unified contracts
python -m pytest tests/unit/test_unified_contracts.py -v

# Test unified orchestrator
python -m pytest tests/unit/test_unified_orchestrator.py -v
```

## 🚨 Deprecation Timeline

| Phase | Status | Timeline |
|-------|--------|----------|
| **Phase 1: Deprecation Warnings** | ✅ Complete | Now |
| **Phase 2: Unified Architecture Ready** | ✅ Complete | Now |
| **Phase 3: Migration Period** | 🟡 Current | 2-4 weeks |
| **Phase 4: Remove Deprecated Code** | 🔴 Future | After migration |

## ⚠️ Breaking Changes

1. **Method Names Changed**
   - `process_text()` → `process()`
   - Parameters changed for normalization flags

2. **Result Structure Enhanced**
   - Added `signals` with structured data
   - Added `trace` for token-level debugging
   - Added `language_confidence`

3. **Initialization Requires Async**
   - Factory methods are async: `await OrchestratorFactory.create_*()`

4. **Flag Behavior Now Real**
   - `remove_stop_words`, `preserve_names`, `enable_advanced_features` have real effects
   - Per CLAUDE.md requirement: flags must actually change behavior

## 🎯 Benefits After Migration

✅ **Single unified orchestrator** (no more choice confusion)
✅ **Exact CLAUDE.md compliance** (9-layer specification)
✅ **Enhanced structured data** (persons, organizations, trace)
✅ **Better performance** (optimized pipeline, caching)
✅ **Comprehensive testing** (integration tests included)
✅ **Clear architecture** (clean layer separation)
✅ **Future-proof** (extensible design)

## 🆘 Need Help?

1. **Read** `CONSOLIDATION_SUMMARY.md` for technical details
2. **Run** `python migration_helper.py --migrate` for interactive help
3. **Check** example usage in `test_unified_architecture.py`
4. **Run** integration tests to see expected behavior
5. **Review** the new contracts in `src/ai_service/contracts/`

## 📚 Additional Resources

- `CONSOLIDATION_SUMMARY.md` - Technical implementation details
- `src/ai_service/contracts/base_contracts.py` - New data structures
- `tests/integration/test_pipeline_end2end.py` - Real usage examples
- `test_unified_architecture.py` - Quick validation test

**The migration is designed to be straightforward with backward compatibility during the transition period. The new architecture provides all the same functionality with better structure and additional features.**