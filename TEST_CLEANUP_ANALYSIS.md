# Test Cleanup Analysis

## 🗂️ Current Test Structure Analysis

### ❌ OBSOLETE TESTS (to remove)

#### Integration Tests - Deprecated/Irrelevant
- `test_changelog_automation.py` (632 lines) - Not related to core functionality
- `test_orchestrator_with_fixes.py` (479 lines) - Uses deprecated OrchestratorService
- `test_name_extraction_pipeline.py` (622 lines) - Duplicate of unified pipeline tests
- `test_normalization_pipeline.py` (371 lines) - Superseded by unified tests
- `test_pipeline_debug.py` (117 lines) - Debug test, no longer needed
- `test_pipeline_without_mocks.py` (81 lines) - Redundant with end2end tests
- `test_working_normalization.py` (102 lines) - Temp debugging test
- `test_ukrainian_morphology_debug.py` (48 lines) - Debug test
- `test_language_detection_debug.py` (41 lines) - Debug test
- `run_name_extraction_tests.py` (143 lines) - Not a proper pytest test

#### Unit Tests - Obsolete Services
- `test_build_templates_script.py` (214 lines) - Script test, not core functionality
- `test_run_service_script.py` (362 lines) - Script test, not core functionality
- `test_vector_processing.py` (587 lines) - If not using vector processing
- `test_template_builder.py` (467 lines) - If templates not core to unified architecture
- `test_final_ac_optimizer.py` (275 lines) - AC optimization not in unified arch
- `test_optimized_ac_pattern_generator.py` (248 lines) - AC patterns not in unified arch
- `test_enhanced_template_builder.py` (167 lines) - Template building not core
- `test_multi_tier_screening.py` (462 lines) - If multi-tier not in unified arch

### ✅ KEEP AND UPDATE TESTS

#### Core Architecture Tests (our new ones)
- `test_pipeline_end2end.py` (483 lines) - ✅ Keep (our comprehensive integration tests)
- `test_unified_contracts.py` (413 lines) - ✅ Keep (our contract tests)
- `test_unified_orchestrator.py` (396 lines) - ✅ Keep (our orchestrator tests)

#### Core Functionality Tests (update for new arch)
- `test_normalization_service.py` (695 lines) - ✅ Keep but update for new contracts
- `test_normalization_result_fields.py` (126 lines) - ✅ Keep, verify against new contracts
- `test_flags_behavior.py` (227 lines) - ✅ Keep, essential for CLAUDE.md compliance
- `test_role_tagging_extended.py` (242 lines) - ✅ Keep, core functionality
- `test_org_acronyms_filter.py` (149 lines) - ✅ Keep, CLAUDE.md requirement
- `test_morph_and_diminutives.py` (227 lines) - ✅ Keep, core morphology

#### Language & Morphology Tests
- `test_russian_morphology_service.py` (531 lines) - ✅ Keep but update
- `test_ukrainian_morphology.py` (462 lines) - ✅ Keep but update
- `test_russian_morphology_unit.py` (337 lines) - ✅ Keep
- `test_ukrainian_morphology_unit.py` (336 lines) - ✅ Keep
- `test_integration_morphology.py` (187 lines) - ✅ Keep
- `test_language_detection_service.py` (311 lines) - ✅ Keep but update
- `test_unicode_service.py` (291 lines) - ✅ Keep but update

#### Smart Filter Tests (update for new adapter)
- `test_smart_filter_service.py` (265 lines) - ✅ Keep but update for adapter
- `test_company_detector.py` (297 lines) - ✅ Keep
- `test_document_detector.py` (320 lines) - ✅ Keep
- `test_terrorism_detector.py` (335 lines) - ✅ Keep
- `test_decision_logic.py` (330 lines) - ✅ Keep

#### Utility Tests
- `test_input_validation.py` (297 lines) - ✅ Keep, used in validation layer
- `test_cache_service.py` (314 lines) - ✅ Keep if caching still used
- `test_canary_overfit.py` (152 lines) - ✅ Keep, important anti-overfit test
- `test_edge_cases_comprehensive.py` (360 lines) - ✅ Keep, edge cases important
- `test_name_dictionaries_validation.py` (327 lines) - ✅ Keep, data validation

#### Integration Tests to Keep
- `test_ru_uk_sentences.py` (231 lines) - ✅ Keep, language testing
- `test_mixed_script_names.py` (150 lines) - ✅ Keep, CLAUDE.md requirement
- `test_full_normalization_suite.py` (167 lines) - ✅ Keep but review for duplicates
- `test_ukrainian_normalization.py` (136 lines) - ✅ Keep but merge with others
- `test_diminutive_forms.py` (56 lines) - ✅ Keep, morphology testing
- `test_complex_scenarios.py` (84 lines) - ✅ Keep if unique scenarios

### 🔄 CONDITIONAL TESTS (review first)
- `test_variant_generation_service.py` (421 lines) - Keep if variants used in unified arch
- `test_pattern_service.py` (328 lines) - Keep if patterns still used

## 📊 Cleanup Impact

**Files to Remove:** ~15 test files (~3,500+ lines)
**Files to Keep:** ~25 test files (~7,500+ lines)
**Files to Update:** ~20 test files for new contracts

**Total Reduction:** ~30% of test code while maintaining full coverage of actual functionality.

## 🎯 New Clean Test Structure

```
tests/
├── integration/
│   ├── test_pipeline_end2end.py          # ✅ Main integration tests
│   ├── test_ru_uk_sentences.py           # Language-specific tests
│   ├── test_mixed_script_names.py        # Mixed script handling
│   └── test_complex_scenarios.py         # Edge cases
├── unit/
│   ├── core/
│   │   ├── test_unified_orchestrator.py  # ✅ Main orchestrator
│   │   └── test_unified_contracts.py     # ✅ Contract tests
│   ├── layers/
│   │   ├── test_normalization_service.py # Updated for new contracts
│   │   ├── test_smart_filter_adapter.py  # Updated for adapter
│   │   ├── test_language_detection.py    # Layer 3
│   │   └── test_unicode_service.py       # Layer 4
│   ├── morphology/
│   │   ├── test_russian_morphology.py    # Consolidated
│   │   ├── test_ukrainian_morphology.py  # Consolidated
│   │   └── test_morph_integration.py     # Integration
│   └── utilities/
│       ├── test_input_validation.py      # Keep
│       ├── test_cache_service.py         # Keep
│       └── test_canary_overfit.py        # Keep
└── performance/
    └── test_ab_perf.py                   # Performance tests
```

This structure aligns with the unified architecture and removes obsolete/duplicate tests.