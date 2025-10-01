# Feature Flag Performance Report

Generated: 2025-09-24 02:23:53

## Performance Summary

| Mode | Avg Time (ms) | P95 Time (ms) | Accuracy | Success Rate | Recommendation |
|------|---------------|---------------|----------|--------------|----------------|
| minimal | 0.7 | 0.8 | 0.78 | 100.0% | 🏆 Most Efficient |
| balanced | 0.7 | 1.1 | 0.78 | 100.0% | |
| accurate | 0.7 | 1.3 | 0.78 | 100.0% | |
| production_optimal | 0.7 | 1.1 | 0.78 | 100.0% | |
| fast | 0.9 | 2.7 | 0.78 | 100.0% | |

## Recommendations

- **Production**: `production_optimal`
- **Development**: `balanced`
- **Testing**: `accurate`
- **Ci_Cd**: `fast`

## Optimal Production Configuration

```json
{
  "enable_spacy_ner": true,
  "enable_spacy_uk_ner": true,
  "enable_spacy_en_ner": false,
  "enable_enhanced_gender_rules": true,
  "enable_enhanced_diminutives": true,
  "enable_fsm_tuned_roles": true,
  "preserve_feminine_suffix_uk": true,
  "morphology_custom_rules_first": true,
  "enable_ascii_fastpath": true,
  "debug_tracing": false,
  "enable_performance_fallback": true,
  "max_latency_threshold_ms": 50.0,
  "enable_vector_fallback": true,
  "enable_ac_tier0": true
}
```
