#!/usr/bin/env python3
"""
Debug test for pipeline stages.

This script helps debug why normalization returns empty results
in the full pipeline by testing each stage individually.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import asyncio
from ai_service.orchestration.clean_orchestrator import CleanOrchestratorService
from ai_service.config.settings import ServiceConfig
from ai_service.orchestration.interfaces import ProcessingContext, ProcessingStage


async def debug_pipeline_stages():
    """Debug each pipeline stage individually."""
    print("🔍 Pipeline Stage Debug Test")
    print("=" * 50)
    
    # Initialize orchestrator
    config = ServiceConfig(
        enable_advanced_features=True,
        preserve_names=True,
        clean_unicode=True,
        enable_morphology=True,
        enable_transliterations=True,
    )
    
    orchestrator = CleanOrchestratorService(config)
    
    # Test text
    test_text = "Оплата от Петра Порошенка по Договору 123"
    print(f"Test text: '{test_text}'")
    print()
    
    # Create initial context
    context = ProcessingContext(
        original_text=test_text,
        current_text=test_text,
        metadata={}
    )
    
    print("Initial context:")
    print(f"  original_text: '{context.original_text}'")
    print(f"  current_text: '{context.current_text}'")
    print(f"  language: {context.language}")
    print(f"  metadata: {context.metadata}")
    print()
    
    # Test each stage individually
    stages = orchestrator.pipeline.stages
    
    for i, stage in enumerate(stages, 1):
        stage_name = stage.get_stage_name().value
        print(f"Stage {i}: {stage_name}")
        print("-" * 30)
        
        if not stage.is_enabled():
            print(f"  ❌ Stage disabled")
            continue
            
        try:
            # Process stage
            context = await stage.process(context)
            
            print(f"  ✅ Stage completed")
            print(f"  current_text: '{context.current_text}'")
            print(f"  language: {context.language}")
            
            # Check stage results
            if ProcessingStage.TEXT_NORMALIZATION in context.stage_results:
                norm_result = context.stage_results[ProcessingStage.TEXT_NORMALIZATION]
                print(f"  normalization result: {norm_result}")
            elif stage_name == "smart_filtering":
                print(f"  smart_filter_skip: {context.metadata.get('smart_filter_skip', False)}")
                print(f"  skip_reason: {context.metadata.get('skip_reason', 'N/A')}")
            
            print()
            
        except Exception as e:
            print(f"  ❌ Stage failed: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Final result
    print("Final context:")
    print(f"  original_text: '{context.original_text}'")
    print(f"  current_text: '{context.current_text}'")
    print(f"  language: {context.language}")
    print(f"  metadata: {context.metadata}")
    print(f"  stage_results keys: {list(context.stage_results.keys())}")


def main():
    """Main function to run pipeline debug."""
    print("🚀 Pipeline Debug Runner")
    print("=" * 50)
    
    try:
        asyncio.run(debug_pipeline_stages())
        print("\n✅ Pipeline debug completed!")
    except Exception as e:
        print(f"\n❌ Pipeline debug failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
