#!/usr/bin/env python3
"""Debug E2E test issues."""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_e2e_issues():
    """Debug E2E test issues"""
    print("=== E2E Issues Debug ===")

    service = NormalizationService()

    test_cases = [
        ("Оплата від Павлової Дар'ї Юріївни", "Павлова Дар'я Юріївна"),
        ("Перерахунок для Іванова Івана Івановича, дата народження 12.05.1980", "Іванов Іван Іванович"),
    ]

    for text, expected in test_cases:
        print(f"\n--- Testing: {text} ---")
        print(f"Expected: {expected}")
        result = service.normalize(text, language="uk")
        print(f"Actual: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")
        print("Trace:")
        for trace in result.trace:
            print(f"  {trace.token} -> {trace.output} (role: {trace.role}, rule: {trace.rule})")

if __name__ == "__main__":
    debug_e2e_issues()