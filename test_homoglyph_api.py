#!/usr/bin/env python3

"""
Test homoglyph detection through the full API pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_homoglyph_api():
    """Test homoglyph detection through full API pipeline."""
    print("🔍 HOMOGLYPH API PIPELINE TEST")
    print("=" * 60)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.core.orchestrator_factory import OrchestratorFactory
        from ai_service.contracts.base_contracts import ProcessResponse

        # Create orchestrator directly
        orchestrator = UnifiedOrchestrator()

        test_cases = [
            {
                "name": "Clean Latin",
                "text": "Liudmila Ulianova",
                "expected_homoglyph": False
            },
            {
                "name": "Mixed Script Attack",
                "text": "Liudмуlа Uliаnоvа",  # Mixed Latin/Cyrillic
                "expected_homoglyph": True
            },
            {
                "name": "Cross-word Mixed",
                "text": "Петро Poroshenko",  # Cyrillic + Latin
                "expected_homoglyph": True
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")
            print(f"   Expected homoglyph: {test_case['expected_homoglyph']}")

            try:
                # Process through orchestrator (async wrapper)
                import asyncio
                result = asyncio.run(orchestrator.process_async(
                    test_case['text'],
                    hints={"language": None},
                    generate_variants=False,
                    generate_embeddings=False,
                    enable_search=True
                ))

                # Check homoglyph fields
                homoglyph_detected = getattr(result, 'homoglyph_detected', None)
                homoglyph_analysis = getattr(result, 'homoglyph_analysis', None)

                print(f"   🔍 homoglyph_detected: {homoglyph_detected}")
                if homoglyph_analysis:
                    print(f"   📊 has_homoglyphs: {homoglyph_analysis.get('has_homoglyphs', 'N/A')}")
                    print(f"   📈 confidence: {homoglyph_analysis.get('confidence', 'N/A')}")
                    print(f"   🚨 suspicious_words: {len(homoglyph_analysis.get('suspicious_words', []))}")
                else:
                    print(f"   📊 homoglyph_analysis: None")

                # Check if it matches expectation
                detected = homoglyph_detected if homoglyph_detected is not None else False
                if detected == test_case['expected_homoglyph']:
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL - Expected {test_case['expected_homoglyph']}, got {detected}")

                # Now test ProcessResponse creation like in main.py
                print(f"   📝 Creating ProcessResponse...")
                process_response = ProcessResponse(
                    normalized_text=result.normalized_text,
                    tokens=result.tokens or [],
                    trace=result.trace or [],
                    language=result.language,
                    success=result.success,
                    errors=result.errors or [],
                    processing_time=result.processing_time,
                    homoglyph_detected=getattr(result, 'homoglyph_detected', False),
                    homoglyph_analysis=getattr(result, 'homoglyph_analysis', None),
                    signals={"persons": [], "organizations": []},
                    decision=None,
                    search_results=None,
                    embedding=None,
                )

                print(f"   🎯 ProcessResponse.homoglyph_detected: {process_response.homoglyph_detected}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("HOMOGLYPH API TEST COMPLETE")


if __name__ == "__main__":
    test_homoglyph_api()