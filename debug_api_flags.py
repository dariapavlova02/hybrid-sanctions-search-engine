#!/usr/bin/env python3

import requests
import json

# Test the same request that was failing
test_request = {
    "text": "Поповнення транспортної карти 1000 1244 0215 1 поїздку",
    "generate_variants": True,
    "generate_embeddings": False,
    "cache_result": True,
    "options": {
        "flags": {
            "normalization_implementation": "factory",
            "factory_rollout_percentage": 100,
            "enable_performance_fallback": True,
            "max_latency_threshold_ms": 100,
            "enable_accuracy_monitoring": True,
            "min_confidence_threshold": 0.8,
            "enable_dual_processing": True,
            "log_implementation_choice": True,
            "debug_tracing": True,
            "use_factory_normalizer": True,
            "fix_initials_double_dot": True,
            "preserve_hyphenated_case": True,
            "strict_stopwords": True,
            "enable_ac_tier0": True,
            "enable_vector_fallback": True,
            "morphology_custom_rules_first": True,
            "enable_nameparser_en": True,
            "enable_en_nicknames": True,
            "enable_spacy_ner": True,
            "enable_spacy_uk_ner": True,
            "enable_spacy_en_ner": True,
            "enable_fsm_tuned_roles": True,
            "enable_enhanced_diminutives": True,
            "enable_enhanced_gender_rules": True,
            "preserve_feminine_suffix_uk": True,
            "en_use_nameparser": True,
            "enable_en_nickname_expansion": True,
            "filter_titles_suffixes": True,
            "require_tin_dob_gate": True,
            "enforce_nominative": True,
            "preserve_feminine_surnames": True,
            "enable_ascii_fastpath": True,
            "use_diminutives_dictionary_only": False,
            "diminutives_allow_cross_lang": True,
            "language_overrides": {
                "additionalProp1": "legacy",
                "additionalProp2": "legacy",
                "additionalProp3": "legacy"
            }
        }
    }
}

print("Making API request...")
print(f"Request flags: use_factory_normalizer={test_request['options']['flags']['use_factory_normalizer']}")
print(f"Request flags: normalization_implementation={test_request['options']['flags']['normalization_implementation']}")

try:
    response = requests.post(
        'http://95.217.84.234:8000/process',
        headers={'Content-Type': 'application/json'},
        json=test_request,
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ API call successful")
        print(f"Normalized result: '{result.get('normalized_text', 'N/A')}'")
        print(f"Tokens: {result.get('tokens', 'N/A')}")

        # Look for implementation choice in trace/logs
        trace = result.get('trace', [])
        for i, token_trace in enumerate(trace[:5]):  # First 5 traces
            notes = token_trace.get('notes', '')
            if 'factory' in notes.lower() or 'legacy' in notes.lower():
                print(f"Trace {i}: {notes}")
            print(f"Trace {i}: token='{token_trace.get('token')}' role={token_trace.get('role')} output='{token_trace.get('output')}'")

    else:
        print(f"❌ API call failed: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ Request failed: {e}")