#!/usr/bin/env python3
"""
Test Decision Engine integration with sanctions search
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_decision_engine_integration():
    """Test full pipeline: normalization → signals → decision engine"""

    print("🔍 Testing Decision Engine integration with sanctions search")
    print("=" * 70)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator

        # Initialize orchestrator
        orchestrator = UnifiedOrchestrator()

        # Test cases with business signals
        test_cases = [
            {
                "text": "ІПН 782611846337",
                "description": "IPN only (potential sanctions match)",
                "expected_risk": "high"  # Should be high if IPN is in sanctions
            },
            {
                "text": "Holoborodko Liudmyla ІПН 782611846337",
                "description": "Personal name + IPN",
                "expected_risk": "varies"  # Depends on sanctions match
            },
            {
                "text": "Дарья Павлова",
                "description": "Personal name only (no business signals)",
                "expected_risk": "low"  # No sanctions indicators
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['description']}")
            print(f"📝 Input: '{test_case['text']}'")

            # Run full orchestrator pipeline
            import asyncio
            async def run_pipeline():
                return await orchestrator.process_async(
                    text=test_case['text'],
                    language="uk",
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True,
                    generate_variants=False,  # Skip variants for faster testing
                    generate_embeddings=False  # Skip embeddings for faster testing
                )

            result = asyncio.run(run_pipeline())

            print(f"\n📊 Orchestrator Result:")
            print(f"  Success: {result.success}")
            print(f"  Errors: {result.errors}")

            # Check normalization results
            if hasattr(result, 'normalization') and result.normalization:
                norm = result.normalization
                print(f"\n🔧 Normalization:")
                print(f"  Normalized: '{norm.normalized}'")
                print(f"  Tokens: {norm.tokens}")

                # Check for business signals in tokens
                business_signals = [token for token in norm.tokens
                                  if any(marker in token.lower()
                                        for marker in ['іпн', 'ipn', 'edrpou', 'едрпоу'])
                                     or token.isdigit() and len(token) >= 8]
                print(f"  Business signals found: {business_signals}")

            # Check signals results
            if hasattr(result, 'signals') and result.signals:
                signals = result.signals
                print(f"\n💼 Signals Service:")
                print(f"  Confidence: {signals.confidence}")
                print(f"  Persons: {len(signals.persons) if signals.persons else 0}")
                print(f"  Organizations: {len(signals.organizations) if signals.organizations else 0}")

                # Check for extracted business identifiers
                if hasattr(signals, 'numbers') and signals.numbers:
                    print(f"  Numbers extracted: {signals.numbers}")
                if hasattr(signals, 'dates') and signals.dates:
                    print(f"  Dates extracted: {signals.dates}")

            # Check search results (if available)
            if hasattr(result, 'search') and result.search:
                search = result.search
                print(f"\n🔍 Search Results:")
                print(f"  Has exact matches: {search.has_exact_matches}")
                print(f"  Exact confidence: {search.exact_confidence}")
                print(f"  Total matches: {search.total_matches}")
                print(f"  Search contribution: {search.search_contribution}")

            # Check decision engine results
            if hasattr(result, 'decision') and result.decision:
                decision = result.decision
                print(f"\n⚖️  Decision Engine:")
                print(f"  Risk level: {decision.risk_level}")
                print(f"  Final score: {decision.final_score}")
                print(f"  Should process: {decision.should_process}")

                # Check individual contributions
                if hasattr(decision, 'contributions'):
                    contributions = decision.contributions
                    print(f"  Contributions:")
                    for key, value in contributions.items():
                        print(f"    {key}: {value}")

                # Check if sanctions contributed to risk
                sanctions_impact = any(key in str(contributions).lower()
                                     for key in ['sanction', 'ipn', 'exact_match', 'search'])
                print(f"  Sanctions impact detected: {'✅ YES' if sanctions_impact else '❌ NO'}")

            else:
                print(f"\n⚖️  Decision Engine: ❌ NO DECISION RESULT")

            print(f"\n{'='*50}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_decision_engine_integration()