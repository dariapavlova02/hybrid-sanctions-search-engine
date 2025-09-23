#!/usr/bin/env python3
"""
Direct test for the Pavlova role classification fix.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_pavlova_case():
    """Test the specific case that was failing."""
    print("Testing the Pavlova case...")

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Initialize service
        service = NormalizationService()

        # Test case from user's complaint
        test_text = "Павловой Даши Юрьевной"
        print(f"\nTesting: '{test_text}'")

        # Normalize
        result = service.normalize_sync(test_text, language="ru")

        print(f"Normalized: '{result.normalized}'")
        print(f"Success: {result.success}")
        print(f"Tokens: {result.tokens}")

        print("\nToken trace:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. {trace.token} -> {trace.role} ({trace.rule}) {getattr(trace, 'notes', '')}")

        # Check if "Павловой" is correctly identified as surname
        pavlova_traces = [t for t in result.trace if "павлов" in t.token.lower()]
        if pavlova_traces:
            trace = pavlova_traces[0]
            if trace.role == "surname":
                print("\n✅ SUCCESS: 'Павловой' correctly identified as surname")
                success = True
            else:
                print(f"\n❌ FAIL: 'Павловой' identified as '{trace.role}', expected 'surname'")
                success = False
        else:
            print("\n❌ FAIL: 'Павловой' not found in traces")
            success = False

        return success

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pavlova_case()
    if success:
        print("\n🎉 Test passed!")
    else:
        print("\n❌ Test failed!")