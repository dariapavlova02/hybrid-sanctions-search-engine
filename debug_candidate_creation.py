#!/usr/bin/env python3
"""
Find exact location of Candidate 'name' parameter error
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_candidate_creation():
    """Find where Candidate is created with 'name' parameter."""
    print("🔍 TRACING CANDIDATE CREATION ERROR")
    print("="*50)

    # Let's monkey-patch Candidate.__init__ to catch the error
    try:
        from ai_service.layers.search.contracts import Candidate, SearchMode

        # Store original __init__
        original_init = Candidate.__init__

        def debug_init(self, *args, **kwargs):
            print(f"🐛 Candidate.__init__ called with:")
            print(f"   args: {args}")
            print(f"   kwargs: {kwargs}")

            if 'name' in kwargs:
                print(f"❌ FOUND 'name' parameter: {kwargs['name']}")
                import traceback
                print("📍 STACK TRACE:")
                traceback.print_stack()
                # Remove the problematic 'name' parameter
                kwargs.pop('name')
                print(f"🔧 Removed 'name', continuing with: {kwargs}")

            return original_init(self, *args, **kwargs)

        # Apply monkey patch
        Candidate.__init__ = debug_init
        print("✅ Monkey patch applied to Candidate.__init__")

        # Now run the orchestrator to trigger the error
        print("\n🚀 Testing with orchestrator to trigger error...")

        import asyncio
        async def test_orchestrator():
            try:
                from ai_service.core.orchestrator_factory import OrchestratorFactory
                orchestrator = await OrchestratorFactory.create_production_orchestrator()

                result = await orchestrator.process(
                    "Test Name",
                    language_hint="uk"
                )

                print(f"✅ Orchestrator completed without Candidate errors")

            except Exception as e:
                print(f"❌ Orchestrator error: {e}")
                if "Candidate.__init__()" in str(e) and "name" in str(e):
                    print("🎯 This is our target error!")
                import traceback
                traceback.print_exc()

        asyncio.run(test_orchestrator())

    except Exception as e:
        print(f"❌ Error in debug setup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_candidate_creation()