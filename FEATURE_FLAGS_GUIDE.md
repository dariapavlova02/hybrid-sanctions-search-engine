# 🚩 Feature Flags Complete Guide

## 🎯 Overview

Feature flags control the behavior of the AI Service normalization and search pipeline. This guide provides comprehensive documentation for all available flags, their impact on performance, and optimal configurations.

## 📋 Quick Reference

### 🔥 Critical Production Flags (Must Be Enabled)

| Flag | Default | Production | Description |
|------|---------|------------|-------------|
| `ENABLE_SEARCH` | `true` | `true` | **CRITICAL** - Enables search functionality |
| `enable_vector_fallback` | `true` | `true` | **CRITICAL** - AC→Vector escalation |
| `preserve_feminine_suffix_uk` | `true` | `true` | **CRITICAL** - Ukrainian feminine endings |
| `enable_spacy_uk_ner` | `true` | `true` | **CRITICAL** - Ukrainian NER processing |
| `enable_enhanced_diminutives` | `true` | `true` | **IMPORTANT** - Nickname resolution |

### ⚡ Performance Optimization Flags

| Flag | Default | Production | Impact |
|------|---------|------------|---------|
| `enable_ascii_fastpath` | `true` | `true` | 🟢 +50% speed for ASCII text |
| `morphology_custom_rules_first` | `true` | `true` | 🟢 +20% accuracy for names |
| `enable_spacy_en_ner` | `true` | `false` | 🔴 -30% speed, +10% EN accuracy |
| `debug_tracing` | `false` | `false` | 🔴 -40% speed when enabled |

## 📊 Flag Categories

### 1. Core Implementation Flags

#### `normalization_implementation`
- **Values**: `factory`, `legacy`, `auto`
- **Default**: `factory`
- **Production**: `factory`
- **Description**: Primary normalization implementation

#### `factory_rollout_percentage`
- **Values**: `0-100`
- **Default**: `100`
- **Production**: `100`
- **Description**: Gradual rollout percentage for factory implementation

#### `use_factory_normalizer`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Use factory normalizer (recommended)

### 2. Performance & Fallback Flags

#### `enable_performance_fallback`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enable automatic fallback on performance issues
- **Impact**: 🟢 Prevents timeouts, maintains SLA

#### `max_latency_threshold_ms`
- **Values**: `1-10000`
- **Default**: `100.0`
- **Production**: `50.0`
- **Description**: Maximum processing latency before fallback
- **Impact**: 🟢 Enforces response time SLA

#### `enable_ascii_fastpath`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Fast processing for ASCII-only text
- **Impact**: 🟢 **+50% speed** for English names

### 3. Search & Escalation Flags

#### `enable_search`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: **CRITICAL** - Enable search functionality
- **Impact**: 🔥 **Required for sanctions screening**

#### `enable_vector_fallback`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: **CRITICAL** - Enable AC→Vector search escalation
- **Impact**: 🔥 **Required for typo handling**

#### `enable_ac_tier0`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enable Aho-Corasick tier 0 patterns
- **Impact**: 🟢 +40% exact match speed

#### `search_escalation_threshold`
- **Values**: `0.0-1.0`
- **Default**: `0.6`
- **Production**: `0.6`
- **Description**: AC confidence threshold for vector escalation
- **Impact**: Lower = more escalation (better recall)

#### `vector_search_threshold`
- **Values**: `0.0-1.0`
- **Default**: `0.3`
- **Production**: `0.3`
- **Description**: Vector similarity threshold
- **Impact**: Lower = more fuzzy matches

### 4. Language Processing Flags

#### `enable_spacy_ner`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enable spaCy Named Entity Recognition
- **Impact**: 🟢 +15% accuracy, 🔴 -20% speed

#### `enable_spacy_uk_ner`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: **CRITICAL** - Ukrainian NER processing
- **Impact**: 🔥 **+25% accuracy for Ukrainian names**

#### `enable_spacy_en_ner`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `false`
- **Description**: English NER processing
- **Impact**: 🟢 +10% EN accuracy, 🔴 -30% speed
- **Recommendation**: Disable for performance in UK-focused deployments

#### `enable_nameparser_en`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enable nameparser for English names
- **Impact**: 🟢 +20% English name accuracy

### 5. Morphology & Gender Flags

#### `morphology_custom_rules_first`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Apply custom rules before pymorphy3
- **Impact**: 🟢 **+20% accuracy** for names

#### `preserve_feminine_suffix_uk`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: **CRITICAL** - Preserve Ukrainian feminine suffixes
- **Impact**: 🔥 **Essential for Ukrainian female names** (-ська, -енко)

#### `enable_enhanced_gender_rules`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enhanced gender rule processing
- **Impact**: 🟢 +15% gender detection accuracy

#### `preserve_feminine_surnames`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Preserve feminine surname forms
- **Impact**: 🟢 Prevents incorrect masculinization

### 6. Diminutives & Nicknames

#### `enable_enhanced_diminutives`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enhanced diminutive/nickname handling
- **Impact**: 🟢 **+30% nickname resolution** (Вова → Володимир)

#### `enable_en_nicknames`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: English nickname expansion
- **Impact**: 🟢 +25% English nickname accuracy (Bob → Robert)

#### `use_diminutives_dictionary_only`
- **Values**: `true/false`
- **Default**: `false`
- **Production**: `false`
- **Description**: Use only dictionary for diminutives (no fuzzy matching)
- **Impact**: 🟢 +20% speed, 🔴 -10% recall

### 7. Advanced Processing Flags

#### `enable_fsm_tuned_roles`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Use FSM-tuned role detection
- **Impact**: 🟢 +10% role classification accuracy

#### `enforce_nominative`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Enforce nominative case for names
- **Impact**: 🟢 Consistent name normalization

#### `filter_titles_suffixes`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Filter titles/suffixes from English names
- **Impact**: 🟢 Cleaner name extraction

### 8. Debug & Monitoring Flags

#### `debug_tracing`
- **Values**: `true/false`
- **Default**: `false`
- **Production**: `false`
- **Description**: Enable detailed debug tracing
- **Impact**: 🔴 **-40% performance**, 🟢 Full debugging

#### `log_implementation_choice`
- **Values**: `true/false`
- **Default**: `true`
- **Production**: `true`
- **Description**: Log implementation selection decisions
- **Impact**: 🟢 Better monitoring, minimal performance impact

#### `enable_dual_processing`
- **Values**: `true/false`
- **Default**: `false`
- **Production**: `false`
- **Description**: Process with both legacy and factory for comparison
- **Impact**: 🔴 **-50% performance**, 🟢 A/B testing

## 🎯 Predefined Configurations

### Production Optimal (Recommended)
```json
{
  "enable_search": true,
  "enable_vector_fallback": true,
  "enable_ac_tier0": true,
  "preserve_feminine_suffix_uk": true,
  "enable_enhanced_diminutives": true,
  "enable_spacy_uk_ner": true,
  "enable_spacy_en_ner": false,
  "enable_ascii_fastpath": true,
  "morphology_custom_rules_first": true,
  "debug_tracing": false,
  "max_latency_threshold_ms": 50.0,
  "search_escalation_threshold": 0.6,
  "vector_search_threshold": 0.3
}
```

### Fast Mode (Development)
```json
{
  "enable_spacy_ner": false,
  "enable_spacy_uk_ner": true,
  "enable_spacy_en_ner": false,
  "enable_enhanced_gender_rules": false,
  "enable_ascii_fastpath": true,
  "debug_tracing": false
}
```

### Accurate Mode (Testing)
```json
{
  "enable_spacy_ner": true,
  "enable_spacy_uk_ner": true,
  "enable_spacy_en_ner": true,
  "enable_enhanced_gender_rules": true,
  "enable_fsm_tuned_roles": true,
  "debug_tracing": true
}
```

## 📊 Performance Impact Matrix

| Flag | Speed Impact | Accuracy Impact | Memory Impact | Recommendation |
|------|--------------|-----------------|---------------|----------------|
| `enable_spacy_uk_ner` | 🔴 -20% | 🟢 +25% | 🟡 +50MB | ✅ Enable (critical) |
| `enable_spacy_en_ner` | 🔴 -30% | 🟢 +10% | 🟡 +50MB | ⚠️ Disable in UK-focused |
| `enable_ascii_fastpath` | 🟢 +50% | 🟡 ±0% | 🟢 -10MB | ✅ Enable |
| `debug_tracing` | 🔴 -40% | 🟢 +0% | 🔴 +100MB | ❌ Disable in production |
| `enable_enhanced_diminutives` | 🔴 -10% | 🟢 +30% | 🟡 +20MB | ✅ Enable |

## 🚨 Critical Warnings

### ❌ Never Disable in Production:
- `ENABLE_SEARCH` - Breaks sanctions screening
- `enable_vector_fallback` - Breaks typo handling
- `preserve_feminine_suffix_uk` - Breaks Ukrainian female names

### ⚠️ Performance Killers:
- `debug_tracing=true` - 40% performance loss
- `enable_dual_processing=true` - 50% performance loss
- `enable_spacy_en_ner=true` - 30% performance loss (in UK-focused deployments)

### 🔧 Optimization Tips:
- Enable `enable_ascii_fastpath` for +50% speed on English text
- Set `max_latency_threshold_ms=50` for strict SLA enforcement
- Disable `enable_spacy_en_ner` if primarily processing Ukrainian text
- Use `morphology_custom_rules_first=true` for +20% name accuracy

## 🧪 Testing Different Configurations

### Using the API:
```bash
curl -X POST http://localhost:8000/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Порошенк Петро",
       "options": {
         "mode": "balanced",
         "flags": {
           "enable_spacy_uk_ner": true,
           "preserve_feminine_suffix_uk": true,
           "debug_tracing": false
         }
       }
     }'
```

### Performance Testing:
```bash
# Run flag profiling
python flag_performance_profiler.py

# Results in flag_profiling_results.json
```

## 🔍 Troubleshooting

### Issue: Search returns empty results
**Check**: `ENABLE_SEARCH=true`, `enable_vector_fallback=true`

### Issue: Ukrainian female names incorrect
**Check**: `preserve_feminine_suffix_uk=true`, `enable_enhanced_gender_rules=true`

### Issue: Slow performance
**Check**: `enable_ascii_fastpath=true`, `debug_tracing=false`, `enable_spacy_en_ner=false`

### Issue: Poor nickname resolution
**Check**: `enable_enhanced_diminutives=true`, `enable_en_nicknames=true`

### Issue: English names not parsed well
**Check**: `enable_nameparser_en=true`, `filter_titles_suffixes=true`

## 📈 Monitoring Flag Impact

Monitor these metrics for flag performance:
- Average processing time per request
- P95/P99 latency percentiles
- Accuracy scores for test cases
- Memory usage per worker
- Cache hit rates

Use the built-in metrics endpoint:
```bash
curl http://localhost:8000/metrics
```

## 🔄 Flag Migration Guide

When updating flags in production:

1. **Test in staging** with representative data
2. **Gradual rollout** using `factory_rollout_percentage`
3. **Monitor metrics** for performance regression
4. **Rollback plan** ready with previous configuration
5. **A/B testing** using `enable_dual_processing` (temporarily)

---

## 📞 Support

For flag configuration issues:
1. Check this guide for flag descriptions
2. Use flag profiler for performance testing
3. Review production recommendations
4. Test with validation API endpoints