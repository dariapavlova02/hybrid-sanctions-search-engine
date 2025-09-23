#!/bin/bash

curl -X 'POST' \
  'http://95.217.84.234:8000/process' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "Порошенка Петра",
  "generate_variants": true,
  "generate_embeddings": true,
  "cache_result": true,
  "options": {
    "flags": {
      "normalization_implementation": "factory",
      "factory_rollout_percentage": 100,
      "enable_performance_fallback": true,
      "max_latency_threshold_ms": 100,
      "enable_accuracy_monitoring": true,
      "min_confidence_threshold": 0.8,
      "enable_dual_processing": false,
      "log_implementation_choice": true,
      "debug_tracing": true,
      "use_factory_normalizer": true,
      "fix_initials_double_dot": true,
      "preserve_hyphenated_case": true,
      "strict_stopwords": true,
      "enable_ac_tier0": true,
      "enable_vector_fallback": true,
      "morphology_custom_rules_first": true,
      "enable_nameparser_en": true,
      "enable_en_nicknames": true,
      "enable_spacy_ner": true,
      "enable_spacy_uk_ner": true,
      "enable_spacy_en_ner": true,
      "enable_fsm_tuned_roles": true,
      "enable_enhanced_diminutives": true,
      "enable_enhanced_gender_rules": true,
      "preserve_feminine_suffix_uk": true,
      "en_use_nameparser": true,
      "enable_en_nickname_expansion": true,
      "filter_titles_suffixes": true,
      "require_tin_dob_gate": true,
      "enforce_nominative": true,
      "preserve_feminine_surnames": true,
      "enable_ascii_fastpath": true,
      "use_diminutives_dictionary_only": true,
      "diminutives_allow_cross_lang": true,
      "language_overrides": {
        "additionalProp1": "legacy",
        "additionalProp2": "legacy",
        "additionalProp3": "legacy"
      }
    }
  }
}' | jq .