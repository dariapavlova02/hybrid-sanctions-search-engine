#!/usr/bin/env python3
"""
Simple test runner for the specific name extraction test.

This script runs only the test_simple_name_extraction test to verify
that "Петра Порошенка" is normalized to "Петро Порошенко".
"""

import sys
import subprocess
from pathlib import Path


def run_simple_name_extraction_test():
    """Run the specific simple name extraction test."""
    print("🧪 Running Simple Name Extraction Test")
    print("=" * 50)
    print("Testing: 'Оплата от Петра Порошенка по Договору 123'")
    print("Expected: 'Петро Порошенко'")
    print()
    
    # Get the test file path
    test_file = Path(__file__).parent / "test_name_extraction_pipeline.py"
    
    if not test_file.exists():
        print(f"[ERROR] Test file not found: {test_file}")
        return False
    
    # Run the specific test
    cmd = [
        sys.executable, "-m", "pytest",
        f"{test_file}::TestNameExtractionPipeline::test_simple_name_extraction",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-s",  # Don't capture output (show print statements)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n[OK] Test passed successfully!")
        print("The name 'Петра Порошенка' was correctly normalized to 'Петро Порошенко'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Test failed with exit code: {e.returncode}")
        print("The normalization may not be working as expected")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error running test: {e}")
        return False


def main():
    """Main function to run the simple name extraction test."""
    print("[INIT] Simple Name Extraction Test Runner")
    print("=" * 50)
    
    success = run_simple_name_extraction_test()
    
    if success:
        print("\n🎉 Name extraction test completed successfully!")
        print("The AI service correctly normalizes Ukrainian names from genitive to nominative case.")
        sys.exit(0)
    else:
        print("\n💥 Name extraction test failed!")
        print("Please check the test output for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
