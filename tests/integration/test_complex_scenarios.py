#!/usr/bin/env python3
"""
Test runner for complex scenarios test.

This script runs the test_complex_scenarios parameterized test
to verify complex name extraction scenarios.
"""

import sys
import subprocess
from pathlib import Path


def run_complex_scenarios_test():
    """Run the complex scenarios test."""
    print("🧪 Running Complex Scenarios Test")
    print("=" * 50)
    
    test_cases = [
        "Переказ для ТОВ \"Рога и Копыта\" від Іванова Івана Івановича -> Іванов Іван Іванович",
        "Payment for services from John Doe, invoice 456 -> John Doe",
        "За послуги зв'язку, платник СИДОРЕНКО ПЕТРО -> СИДОРЕНКО ПЕТРО",
        "Возврат средств по заказу #789, получатель Jane Smith -> Jane Smith",
        "Аліменти від Петренко О.П. -> Петренко О.П."
    ]
    
    print("Testing scenarios:")
    for i, case in enumerate(test_cases, 1):
        print(f"  {i}. {case}")
    print()
    
    # Get the test file path
    test_file = Path(__file__).parent / "test_name_extraction_pipeline.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    # Run the specific test
    cmd = [
        sys.executable, "-m", "pytest",
        f"{test_file}::TestNameExtractionPipeline::test_complex_scenarios",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-s",  # Don't capture output (show print statements)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n✅ Complex scenarios test passed successfully!")
        print("All complex name extraction scenarios are working correctly.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Test failed with exit code: {e.returncode}")
        print("Some complex scenarios may not be working as expected.")
        return False
    except Exception as e:
        print(f"\n❌ Error running test: {e}")
        return False


def main():
    """Main function to run the complex scenarios test."""
    print("🚀 Complex Scenarios Test Runner")
    print("=" * 50)
    
    success = run_complex_scenarios_test()
    
    if success:
        print("\n🎉 Complex scenarios test completed successfully!")
        print("The AI service correctly handles complex name extraction scenarios.")
        sys.exit(0)
    else:
        print("\n💥 Complex scenarios test failed!")
        print("Please check the test output for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
