#!/usr/bin/env python3
"""Debug initials splitting issue"""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_initials():
    """Debug initials splitting"""
    print("=== Initials Splitting Debug ===")

    service = NormalizationService()

    test_cases = [
        ["П.І.", "Коваленко"],
        ["А.Б.В.", "Петров"],
    ]

    for tokens in test_cases:
        print(f"\nTesting tokens: {tokens}")

        # Test splitting function directly
        for token in tokens:
            if service._is_initial(token):
                split = service._split_multi_initial(token)
                print(f"  {token} -> {split}")

        # Test role tagging
        tagged = service._tag_roles(tokens, "uk")
        print(f"Role tagging result: {tagged}")

if __name__ == "__main__":
    debug_initials()