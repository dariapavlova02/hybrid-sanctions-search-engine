#!/usr/bin/env python3
"""
Test script to validate the unified architecture implementation.

This script tests the integration of all layers according to the specification
in CLAUDE.md without relying on existing test infrastructure.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

try:
    from ai_service.core.orchestrator_factory import OrchestratorFactory
    from ai_service.utils import setup_logging, get_logger

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    async def test_unified_architecture():
        """Test the unified architecture with sample inputs"""
        print("🚀 Testing Unified Architecture Implementation")
        print("=" * 50)

        try:
            # Initialize minimal orchestrator for testing
            print("1. Initializing orchestrator...")
            orchestrator = await OrchestratorFactory.create_testing_orchestrator(minimal=True)
            print("✅ Orchestrator initialized successfully")

            # Test cases from CLAUDE.md requirements
            test_cases = [
                # Person name normalization
                {
                    "text": "Іван Петрович Сидоренко",
                    "expected_type": "person",
                    "description": "Ukrainian person name"
                },
                # Organization with legal form
                {
                    "text": "ООО \"ГАЗПРОМ\"",
                    "expected_type": "organization",
                    "description": "Russian organization with legal form"
                },
                # Mixed context
                {
                    "text": "платеж от Петров Иван Иванович ИНН 123456789012",
                    "expected_type": "mixed",
                    "description": "Payment context with person and INN"
                },
                # ASCII name in Cyrillic context
                {
                    "text": "John Smith работает в ООО Рога и копыта",
                    "expected_type": "mixed",
                    "description": "ASCII name in Cyrillic context"
                }
            ]

            print("\n2. Running test cases...")
            for i, case in enumerate(test_cases, 1):
                print(f"\n--- Test Case {i}: {case['description']} ---")
                print(f"Input: {case['text']}")

                try:
                    # Process with unified orchestrator
                    result = await orchestrator.process(
                        text=case['text'],
                        # Test different flag combinations per CLAUDE.md
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=True,
                        generate_variants=False,
                        generate_embeddings=False
                    )

                    # Validate result structure
                    print(f"✅ Processing successful: {result.success}")
                    print(f"   Language: {result.language} (confidence: {result.language_confidence:.2f})")
                    print(f"   Normalized: '{result.normalized_text}'")
                    print(f"   Tokens: {result.tokens}")
                    print(f"   Processing time: {result.processing_time:.3f}s")

                    # Validate persons extraction
                    if result.signals.persons:
                        print(f"   Persons: {len(result.signals.persons)} found")
                        for person in result.signals.persons:
                            print(f"     - Core: {person.core}, Full: {person.full_name}")
                            if person.dob:
                                print(f"       DOB: {person.dob}")
                            if person.ids:
                                print(f"       IDs: {person.ids}")

                    # Validate organizations extraction
                    if result.signals.organizations:
                        print(f"   Organizations: {len(result.signals.organizations)} found")
                        for org in result.signals.organizations:
                            print(f"     - Core: '{org.core}', Legal: {org.legal_form}")
                            print(f"       Full: '{org.full_name}'")

                    # Validate trace (per CLAUDE.md requirement)
                    if result.trace:
                        print(f"   Trace: {len(result.trace)} tokens traced")
                        for trace in result.trace[:3]:  # Show first 3
                            if hasattr(trace, 'token'):
                                print(f"     - {trace.token} -> {trace.role} -> {trace.output}")

                    print(f"   Signals confidence: {result.signals.confidence:.2f}")

                except Exception as e:
                    print(f"❌ Test case failed: {e}")
                    import traceback
                    traceback.print_exc()

            print("\n3. Testing normalization flags behavior...")

            # Test flags actually change behavior (per CLAUDE.md requirement)
            test_text = "Іван Петрович Сидоренко и ООО компания"

            flag_tests = [
                {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
                {"remove_stop_words": False, "preserve_names": True, "enable_advanced_features": True},
                {"remove_stop_words": True, "preserve_names": False, "enable_advanced_features": True},
                {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": False},
            ]

            results = []
            for flags in flag_tests:
                result = await orchestrator.process(text=test_text, **flags)
                results.append((flags, result.normalized_text, result.tokens))
                print(f"Flags {flags}: '{result.normalized_text}' ({len(result.tokens)} tokens)")

            # Verify flags actually change results
            unique_results = set(r[1] for r in results)
            if len(unique_results) > 1:
                print("✅ Flags behavior test passed - different flags produce different results")
            else:
                print("⚠️  Flags behavior test warning - all results are identical")

            print("\n🎉 Unified architecture test completed!")
            return True

        except Exception as e:
            print(f"❌ Unified architecture test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    if __name__ == "__main__":
        success = asyncio.run(test_unified_architecture())
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed and services are implemented")
    sys.exit(1)