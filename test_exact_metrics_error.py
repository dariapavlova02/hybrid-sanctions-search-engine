#!/usr/bin/env python3

"""
Test to identify the exact location of the metrics error.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_with_detailed_traceback():
    """Run a test that captures the exact location of metrics error."""
    print("🔍 DETAILED METRICS ERROR INVESTIGATION")
    print("=" * 60)

    try:
        # Import the main components
        from ai_service.layers.normalization.normalization_service import NormalizationService

        print("✅ NormalizationService imported")

        # Create the service
        service = NormalizationService()

        print("✅ NormalizationService created")

        # Try a simple normalization that might trigger the error
        test_text = "Іванов Іван Іванович"

        print(f"🧪 Testing normalization with: '{test_text}'")

        # This should trigger the metrics error if it exists
        result = service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=False  # Disable heavy features
        )

        print("📋 Normalization completed successfully")
        print(f"   Success: {result.success}")
        print(f"   Errors: {result.errors}")
        print(f"   Normalized: '{result.normalized}'")

        # Check if we have the metrics error
        if result.errors and any("metrics" in str(error).lower() for error in result.errors):
            print("❌ Found metrics error in result!")
            return False

        print("✅ No metrics errors detected!")
        return True

    except Exception as e:
        error_msg = str(e).lower()

        print(f"❌ Exception occurred: {e}")

        # Print detailed traceback to find exact location
        print("\n📍 DETAILED TRACEBACK:")
        print("-" * 40)
        traceback.print_exc()
        print("-" * 40)

        if "metrics" in error_msg and "not defined" in error_msg:
            print("\n🎯 CONFIRMED: This is the metrics undefined error!")

            # Extract the specific line information
            tb = traceback.extract_tb(sys.exc_info()[2])
            for frame in tb:
                if "metrics" in frame.line and "not defined" not in frame.line:
                    print(f"\n📍 ERROR LOCATION:")
                    print(f"   File: {frame.filename}")
                    print(f"   Line: {frame.lineno}")
                    print(f"   Function: {frame.name}")
                    print(f"   Code: {frame.line}")

            return False
        else:
            print(f"\nℹ️ Different error (not metrics related): {e}")
            return True

def main():
    print("🎯 EXACT METRICS ERROR LOCATION TEST")
    print("=" * 50)

    success = test_with_detailed_traceback()

    print("\n" + "=" * 50)
    if success:
        print("🎉 NO METRICS ERROR DETECTED")
        print("The error might be fixed or occur in a different scenario")
    else:
        print("❌ METRICS ERROR CONFIRMED")
        print("Check the traceback above for the exact location")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)