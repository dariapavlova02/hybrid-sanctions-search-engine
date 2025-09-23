#!/usr/bin/env python3
"""
Test the role classification fix for Russian names.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
from ai_service.layers.normalization.processors.config import ProcessingConfig

def test_role_classification():
    """Test role classification with the new morphology-aware FSM."""
    print("Testing role classification fix...")

    # Initialize factory
    factory = NormalizationFactory()

    # Test case from user's complaint
    test_text = "Павловой Даши Юрьевной"
    print(f"\nTesting: '{test_text}'")

    # Create config
    config = ProcessingConfig(
        language="ru",
        enable_advanced_features=True,
        remove_stop_words=True,
        preserve_names=True
    )

    # Normalize
    result = factory.normalize_async(test_text, config)

    print(f"Normalized: '{result.normalized}'")
    print("\nToken trace:")
    for trace in result.trace:
        print(f"  {trace.token} -> {trace.role} ({trace.rule}) {trace.notes}")

    # Check if "Павловой" is correctly identified as surname
    pavlova_traces = [t for t in result.trace if "павлов" in t.token.lower()]
    if pavlova_traces:
        trace = pavlova_traces[0]
        if trace.role == "surname":
            print("\n✅ SUCCESS: 'Павловой' correctly identified as surname")
        else:
            print(f"\n❌ FAIL: 'Павловой' identified as '{trace.role}', expected 'surname'")
    else:
        print("\n❌ FAIL: 'Павловой' not found in traces")

    # Test more cases
    test_cases = [
        "Иванов Петр Сергеевич",
        "Сидорова Анна Михайловна",
        "Кузнецовой Елены Владимировны",
        "Петров",
        "Анна"
    ]

    print("\n" + "="*50)
    print("Additional test cases:")

    for test_case in test_cases:
        print(f"\nTesting: '{test_case}'")
        result = factory.normalize_async(test_case, config)
        print(f"Normalized: '{result.normalized}'")

        # Show roles
        roles = []
        for trace in result.trace:
            roles.append(f"{trace.token}({trace.role})")
        print(f"Roles: {' '.join(roles)}")

if __name__ == "__main__":
    test_role_classification()