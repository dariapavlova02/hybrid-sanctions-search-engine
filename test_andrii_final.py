#!/usr/bin/env python3
"""
Test ANDРІЙ in final normalized text after FSM fix
"""

import sys
import json
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_andrii_final():
    """Test ANDРІЙ in final result."""
    print("🔍 TESTING АНДРІЙ IN FINAL RESULT")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test case
        test_input = "ШЕВЧЕНКО АНДРІЙ АНАТОЛІЙОВИЧ"
        print(f"Input: '{test_input}'")

        result = service.normalize_sync(
            test_input,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"  normalized_text: '{result.normalized}'")
        print(f"  tokens: {result.tokens}")
        print(f"  persons_core: {result.persons_core}")
        print(f"  success: {result.success}")

        # Check АНДРІЙ presence
        print(f"\n✅ ПРОВЕРКИ:")
        if "Андрій" in result.normalized or "андрій" in result.normalized.lower():
            print("  ✅ АНДРІЙ найден в normalized_text!")
        else:
            print("  ❌ АНДРІЙ НЕ найден в normalized_text!")

        # Check for duplicates in persons_core
        if result.persons_core:
            all_tokens = []
            for person_tokens in result.persons_core:
                all_tokens.extend(person_tokens)

            duplicates = []
            seen = set()
            for token in all_tokens:
                token_lower = token.lower()
                if token_lower in seen:
                    duplicates.append(token)
                seen.add(token_lower)

            if duplicates:
                print(f"  ⚠️ Найдены дубликаты в persons_core: {duplicates}")
            else:
                print(f"  ✅ Дубликатов в persons_core нет")

        # Detailed trace for АНДРІЙ
        print(f"\n📝 TRACE для АНДРІЙ:")
        andrii_traces = [t for t in result.trace if 'андрій' in t.token.lower()]
        for i, trace in enumerate(andrii_traces):
            print(f"  {i+1}. Token: '{trace.token}' -> Role: '{trace.role}' -> Output: '{trace.output}'")

        # Show unique tokens in trace
        print(f"\n📊 Уникальные токены в trace:")
        unique_tokens = set()
        for trace in result.trace:
            if hasattr(trace, 'token'):
                unique_tokens.add(trace.token)
        print(f"  Уникальные токены: {unique_tokens}")

        # Count duplicates in trace
        token_counts = {}
        for trace in result.trace:
            if hasattr(trace, 'token'):
                token = trace.token
                token_counts[token] = token_counts.get(token, 0) + 1

        duplicated_tokens = {k: v for k, v in token_counts.items() if v > 1}
        if duplicated_tokens:
            print(f"\n⚠️ Дублированные токены в trace:")
            for token, count in duplicated_tokens.items():
                print(f"  '{token}': {count} раз")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_andrii_final()