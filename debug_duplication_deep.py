#!/usr/bin/env python3
"""
Deep debug of token duplication issue
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def debug_duplication_deep():
    """Debug the duplication issue step by step."""
    print("🔍 DEEP DEBUGGING TOKEN DUPLICATION")
    print("="*50)

    test_case = "Петр Порошенко"  # Ukrainian name that should be "Петро Порошенко"

    try:
        # Test direct normalization service
        print("1️⃣ Testing NormalizationService directly")
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        result_direct = await service.normalize_async(
            test_case,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"   Input: '{test_case}'")
        print(f"   Normalized: '{result_direct.normalized}'")
        print(f"   Tokens: {result_direct.tokens}")
        print(f"   Trace count: {len(result_direct.trace)}")

        # Show trace details
        print(f"   Trace details:")
        for i, trace_item in enumerate(result_direct.trace):
            if hasattr(trace_item, 'token'):
                print(f"     {i+1}. '{trace_item.token}' -> '{trace_item.role}' -> '{trace_item.output}'")
            else:
                print(f"     {i+1}. Non-TokenTrace: {str(trace_item)[:100]}")

        print("\n" + "="*30)

        # Test orchestrator
        print("2️⃣ Testing UnifiedOrchestrator")
        from ai_service.core.orchestrator_factory import OrchestratorFactory
        orchestrator = await OrchestratorFactory.create_production_orchestrator()

        result_orchestrator = await orchestrator.process(
            test_case,
            language_hint="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"   Input: '{test_case}'")
        print(f"   Normalized: '{result_orchestrator.normalized_text}'")
        if hasattr(result_orchestrator, 'tokens'):
            print(f"   Tokens: {result_orchestrator.tokens}")

        # Check if normalization_data exists
        if hasattr(result_orchestrator, 'normalization_data') and result_orchestrator.normalization_data:
            norm_data = result_orchestrator.normalization_data
            print(f"   Norm data tokens: {norm_data.tokens}")
            print(f"   Norm data trace count: {len(norm_data.trace)}")

            # Show trace details
            print(f"   Orchestrator trace details:")
            for i, trace_item in enumerate(norm_data.trace):
                if hasattr(trace_item, 'token'):
                    print(f"     {i+1}. '{trace_item.token}' -> '{trace_item.role}' -> '{trace_item.output}'")
                else:
                    print(f"     {i+1}. Non-TokenTrace: {str(trace_item)[:100]}")

        print("\n" + "="*30)

        # Compare results
        print("3️⃣ COMPARISON ANALYSIS")
        print(f"Direct normalized: '{result_direct.normalized}'")
        if hasattr(result_orchestrator, 'normalized_text'):
            print(f"Orchestrator normalized: '{result_orchestrator.normalized_text}'")
            if result_direct.normalized != result_orchestrator.normalized_text:
                print(f"❌ MISMATCH in normalized text!")

        print(f"Direct tokens: {result_direct.tokens}")
        if hasattr(result_orchestrator, 'normalization_data') and result_orchestrator.normalization_data:
            orch_tokens = result_orchestrator.normalization_data.tokens
            print(f"Orchestrator tokens: {orch_tokens}")
            if result_direct.tokens != orch_tokens:
                print(f"❌ MISMATCH in tokens!")

        # Check for Ukrainian vs Russian processing
        print("\n4️⃣ LANGUAGE PROCESSING ANALYSIS")
        if "Петр" in result_direct.normalized:
            print(f"❌ Russian name 'Петр' found - should be Ukrainian 'Петро'!")
        elif "Петро" in result_direct.normalized:
            print(f"✅ Ukrainian name 'Петро' correctly preserved!")

        if hasattr(result_orchestrator, 'normalized_text'):
            if "Петр" in result_orchestrator.normalized_text:
                print(f"❌ Orchestrator: Russian name 'Петр' found - should be Ukrainian 'Петро'!")
            elif "Петро" in result_orchestrator.normalized_text:
                print(f"✅ Orchestrator: Ukrainian name 'Петро' correctly preserved!")

        # Check language detection
        print(f"Direct service detected language: {result_direct.language}")
        if hasattr(result_orchestrator, 'language'):
            print(f"Orchestrator detected language: {result_orchestrator.language}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_duplication_deep())