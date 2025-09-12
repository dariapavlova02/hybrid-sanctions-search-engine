#!/usr/bin/env python3
"""
Test runner for name extraction pipeline integration tests.

This script demonstrates how to run the integration tests for the
name extraction pipeline and provides detailed output.
"""

import sys
import subprocess
from pathlib import Path


def run_integration_tests():
    """Run the name extraction pipeline integration tests."""
    print("🧪 Running Name Extraction Pipeline Integration Tests")
    print("=" * 60)
    
    # Get the test file path
    test_file = Path(__file__).parent / "test_name_extraction_pipeline.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "--color=yes",  # Colored output
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n✅ All tests passed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return False


def run_specific_test_class():
    """Run a specific test class for focused testing."""
    print("🎯 Running Specific Test Class")
    print("=" * 40)
    
    test_file = Path(__file__).parent / "test_name_extraction_pipeline.py"
    
    cmd = [
        sys.executable, "-m", "pytest",
        f"{test_file}::TestNameExtractionPipeline::test_full_pipeline_ukrainian_name_extraction",
        "-v",
        "--tb=short",
        "--color=yes",
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n✅ Specific test passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Test failed with exit code: {e.returncode}")
        return False


def run_performance_tests():
    """Run only performance-related tests."""
    print("⚡ Running Performance Tests")
    print("=" * 35)
    
    test_file = Path(__file__).parent / "test_name_extraction_pipeline.py"
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-k", "performance",  # Run only tests with "performance" in the name
        "-v",
        "--tb=short",
        "--durations=5",
        "--color=yes",
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n✅ Performance tests completed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Performance tests failed with exit code: {e.returncode}")
        return False


def main():
    """Main function to run different test scenarios."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run name extraction pipeline integration tests")
    parser.add_argument(
        "--type", 
        choices=["all", "specific", "performance"],
        default="all",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    print("🚀 Name Extraction Pipeline Integration Test Runner")
    print("=" * 60)
    
    if args.type == "all":
        success = run_integration_tests()
    elif args.type == "specific":
        success = run_specific_test_class()
    elif args.type == "performance":
        success = run_performance_tests()
    else:
        print(f"❌ Unknown test type: {args.type}")
        success = False
    
    if success:
        print("\n🎉 Test execution completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Test execution failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
