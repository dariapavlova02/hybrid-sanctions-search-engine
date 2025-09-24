#!/usr/bin/env python3
"""
Test duplicates issue in full pipeline
"""

import sys
import json
import asyncio
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_full_pipeline():
    """Test full processing pipeline."""
    print("🔍 TESTING FULL PIPELINE WITH DUPLICATES CHECK")
    print("="*50)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.layers.validation.validation_service import ValidationService
        from ai_service.layers.language.language_detection_service import LanguageDetectionService
        from ai_service.layers.unicode.unicode_service import UnicodeService
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.signals.signals_service import SignalsExtractionService

        orchestrator = UnifiedOrchestrator(
            validation_service=ValidationService(),
            language_service=LanguageDetectionService(),
            unicode_service=UnicodeService(),
            normalization_service=NormalizationService(),
            signals_service=SignalsExtractionService()
        )

        # Test case
        test_input = "ШЕВЧЕНКО АНДРІЙ АНАТОЛІЙОВИЧ"
        print(f"Input: '{test_input}'")

        result = await orchestrator.process_async(test_input)

        # Convert to dict for analysis
        result_dict = result.to_dict()

        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"  normalized_text: '{result_dict['normalized_text']}'")
        print(f"  tokens: {result_dict['tokens']}")

        # Check trace for duplicates
        print(f"\n📝 TRACE ANALYSIS:")
        trace_tokens = []
        unique_trace_tokens = set()
        duplicate_trace_entries = []

        for i, trace_entry in enumerate(result_dict['trace']):
            token = trace_entry.get('token', '')
            trace_tokens.append(token)

            # Check if we've seen this exact token before
            token_key = f"{token}:{trace_entry.get('role', '')}:{trace_entry.get('output', '')}"
            if token_key in unique_trace_tokens:
                duplicate_trace_entries.append({
                    'index': i,
                    'token': token,
                    'role': trace_entry.get('role', ''),
                    'output': trace_entry.get('output', '')
                })
            unique_trace_tokens.add(token_key)

        print(f"  Total trace entries: {len(result_dict['trace'])}")
        print(f"  Unique tokens in trace: {len(set(trace_tokens))}")

        if duplicate_trace_entries:
            print(f"\n⚠️ DUPLICATE TRACE ENTRIES FOUND:")
            for dup in duplicate_trace_entries:
                print(f"    Index {dup['index']}: '{dup['token']}' (role: {dup['role']}, output: {dup['output']})")
        else:
            print("  ✅ No exact duplicate trace entries")

        # Check signals for duplicates
        if 'signals' in result_dict and result_dict['signals'].get('persons'):
            print(f"\n📊 SIGNALS ANALYSIS:")
            for i, person in enumerate(result_dict['signals']['persons']):
                core_tokens = person.get('core', [])
                print(f"  Person {i+1} core: {core_tokens}")

                # Check for duplicates in core
                seen = set()
                dups = []
                for token in core_tokens:
                    if token.lower() in seen:
                        dups.append(token)
                    seen.add(token.lower())

                if dups:
                    print(f"    ⚠️ Duplicates found: {dups}")
                else:
                    print(f"    ✅ No duplicates in person core")

        # Show expected vs actual
        print(f"\n🎯 EXPECTED vs ACTUAL:")
        print(f"  Expected normalized: 'Шевченко Андрій Анатолійович'")
        print(f"  Actual normalized:   '{result_dict['normalized_text']}'")
        print(f"  Match: {result_dict['normalized_text'] == 'Шевченко Андрій Анатолійович'}")

        print(f"\n  Expected tokens: ['Шевченко', 'Андрій', 'Анатолійович']")
        print(f"  Actual tokens:   {result_dict['tokens']}")
        print(f"  Match: {result_dict['tokens'] == ['Шевченко', 'Андрій', 'Анатолійович']}")

        # Output full JSON for analysis
        print(f"\n📄 FULL JSON OUTPUT:")
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())