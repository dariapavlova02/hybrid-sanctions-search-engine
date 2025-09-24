#!/usr/bin/env python3
"""
Тест реальных производственных кейсов.
"""

import asyncio
import json
import time
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_real_cases():
    """Тест с реальными именами и ожидаемыми результатами."""
    print("🎯 PRODUCTION REAL CASES TEST")
    print("="*50)

    # Initialize orchestrator
    try:
        from ai_service.core.orchestrator_factory import OrchestratorFactory
        orchestrator = await OrchestratorFactory.create_production_orchestrator()
        print("✅ Orchestrator initialized")
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        return

    # Test cases with expected risk levels
    test_cases = [
        {
            "name": "Коваленко Олександра Сергіївна",
            "expected_risk": "low",
            "notes": "Full Ukrainian female name with patronymic"
        },
        {
            "name": "Сергій Олійник",
            "expected_risk": "medium",
            "notes": "Ukrainian male name without patronymic"
        },
        {
            "name": "Liudмуlа Uliаnоvа",
            "expected_risk": "low",
            "notes": "Mixed script (Latin + Cyrillic) homoglyph attack"
        }
    ]

    print(f"\n🧪 Testing {len(test_cases)} real production cases...")

    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        expected_risk = test_case["expected_risk"]
        notes = test_case["notes"]

        print(f"\n{i}. Testing: '{name}'")
        print(f"   Expected: {expected_risk} risk")
        print(f"   Notes: {notes}")

        try:
            start_time = time.time()
            result = await orchestrator.process(name)
            processing_time = (time.time() - start_time) * 1000

            # Extract key results
            normalized = result.normalized_text
            language = result.language
            lang_conf = result.language_confidence
            success = result.success

            print(f"   ⏱️  Processing time: {processing_time:.1f}ms")
            print(f"   📝 Normalized: '{normalized}'")
            print(f"   🌍 Language: {language} ({lang_conf:.3f})")
            print(f"   ✅ Success: {success}")

            # Check signals
            if result.signals:
                # Handle both dict and object access
                if hasattr(result.signals, 'persons'):
                    persons = result.signals.persons or []
                elif isinstance(result.signals, dict):
                    persons = result.signals.get('persons', [])
                else:
                    persons = []

                print(f"   👥 Persons found: {len(persons)}")

                for j, person in enumerate(persons[:2], 1):
                    if isinstance(person, dict):
                        core = person.get('core', 'N/A')
                        conf = person.get('confidence', 0)
                        evidence = person.get('evidence', [])
                    else:
                        core = getattr(person, 'core', 'N/A')
                        conf = getattr(person, 'confidence', 0)
                        evidence = getattr(person, 'evidence', [])

                    print(f"     {j}. Core: {core}")
                    print(f"        Confidence: {conf:.3f}")
                    if evidence:
                        print(f"        Evidence: {evidence[:3]}")  # Show first 3

            # Check trace for debugging
            if result.trace:
                print(f"   🔍 Token traces: {len(result.trace)}")
                for trace in result.trace[:3]:  # Show first 3 traces
                    token = trace.token if hasattr(trace, 'token') else 'N/A'
                    role = trace.role if hasattr(trace, 'role') else 'N/A'
                    rule = trace.rule if hasattr(trace, 'rule') else 'N/A'
                    print(f"     '{token}' -> {role} ({rule})")

            # Risk assessment
            print(f"   🎯 Expected risk: {expected_risk}")

            # Check if we can detect homoglyph attacks
            if "mixed script" in notes.lower():
                has_mixed_chars = any(ord(c) > 127 for c in name) and any(ord(c) <= 127 for c in name)
                if has_mixed_chars:
                    print(f"   ⚠️  Mixed script detected - potential homoglyph attack")

        except Exception as e:
            print(f"   ❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*50}")
    print("🎉 REAL PRODUCTION CASES TEST COMPLETED")
    print("="*50)

    print("📊 Key observations:")
    print("• Full Ukrainian names with patronymics should normalize correctly")
    print("• Mixed script names (homoglyph attacks) should be detected")
    print("• Processing time should be reasonable (< 1000ms)")
    print("• Language detection should work for mixed scripts")
    print("• Token role classification should handle complex cases")

if __name__ == "__main__":
    asyncio.run(test_real_cases())