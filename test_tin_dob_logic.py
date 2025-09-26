#!/usr/bin/env python3
"""Test TIN/DOB requirement logic"""

def test_scenarios():
    """Test different TIN/DOB requirement scenarios"""

    scenarios = [
        {
            "name": "HIGH RISK + No TIN/DOB in request",
            "input": "Сергій Олійник",  # Just name
            "expected_review_required": True,
            "expected_required_fields": ["TIN", "DOB"],
            "reason": "HIGH RISK match but missing identifiers"
        },
        {
            "name": "HIGH RISK + Has TIN in request",
            "input": "Сергій Олійник ІПН 1234567890",
            "expected_review_required": True,
            "expected_required_fields": ["DOB"],
            "reason": "HIGH RISK match, has TIN but missing DOB"
        },
        {
            "name": "HIGH RISK + Has DOB in request",
            "input": "Сергій Олійник дата народження 01.01.1990",
            "expected_review_required": True,
            "expected_required_fields": ["TIN"],
            "reason": "HIGH RISK match, has DOB but missing TIN"
        },
        {
            "name": "HIGH RISK + Has both TIN and DOB",
            "input": "Сергій Олійник ІПН 1234567890 дата народження 01.01.1990",
            "expected_review_required": False,
            "expected_required_fields": [],
            "reason": "HIGH RISK match but has all required identifiers"
        },
        {
            "name": "LOW RISK",
            "input": "Джон Сміт",  # Non-sanctioned name
            "expected_review_required": False,
            "expected_required_fields": [],
            "reason": "LOW RISK - no additional fields needed"
        }
    ]

    print("🧪 TIN/DOB Requirement Logic Test")
    print("=" * 60)

    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print(f"Input: '{scenario['input']}'")
        print(f"Expected review_required: {scenario['expected_review_required']}")
        print(f"Expected required_additional_fields: {scenario['expected_required_fields']}")
        print(f"Reason: {scenario['reason']}")
        print("-" * 60)

if __name__ == "__main__":
    test_scenarios()