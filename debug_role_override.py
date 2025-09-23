#!/usr/bin/env python3
"""
Debug role override logic in normalization factory.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_role_override():
    """Debug role override logic."""
    print("Debugging role override logic...")

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Initialize service
        service = NormalizationService()

        # Test case from user's complaint
        test_text = "Павловой Даши Юрьевной"
        print(f"\nTesting: '{test_text}'")

        # Add monkey patch to track role changes
        original_classify_token_roles = service.factory._classify_token_roles

        def debug_classify_token_roles(*args, **kwargs):
            result = original_classify_token_roles(*args, **kwargs)
            classified_tokens, roles, role_traces, org_entities = result
            print(f"_classify_token_roles result: {list(zip(classified_tokens, roles))}")
            return result

        service.factory._classify_token_roles = debug_classify_token_roles

        # Monkey patch debug for FSM override
        original_logger_debug = service.factory.logger.debug

        def debug_logger(msg):
            if "FSM overrode roles" in msg or "Classified roles" in msg:
                print(f"LOGGER: {msg}")
            return original_logger_debug(msg)

        service.factory.logger.debug = debug_logger

        # Normalize
        result = service.normalize_sync(test_text, language="ru")

        print(f"\nFinal result:")
        print(f"Normalized: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")

        print("\nToken trace:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. {trace.token} -> {trace.role} ({trace.rule})")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_role_override()