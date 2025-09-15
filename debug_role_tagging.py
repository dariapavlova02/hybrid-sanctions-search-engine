#!/usr/bin/env python3
"""Debug role tagging for Дар'ї"""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

def debug_role_tagging():
    """Debug role tagging issue"""
    print("=== Role Tagging Debug ===")

    # Check if name is in dictionary
    from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES

    print("Checking UKRAINIAN_NAMES dictionary:")

    # Check for Дарія
    if "Дарія" in UKRAINIAN_NAMES:
        entry = UKRAINIAN_NAMES["Дарія"]
        print(f"Found Дарія: {entry}")
        print(f"Declensions: {entry.get('declensions', [])}")
        dari_key = "Дар'ї"
        print(f"Дар'ї in declensions: {dari_key in entry.get('declensions', [])}")
    else:
        print("Дарія NOT found in dictionary!")

    # Check normalization service dictionary loading
    print("\n--- NormalizationService dictionary check ---")
    from ai_service.layers.normalization.normalization_service import NormalizationService
    service = NormalizationService()

    # Check if it loads Ukrainian names
    try:
        # Try to access the loaded dictionary
        if hasattr(service, '_ukrainian_names'):
            names = service._ukrainian_names
            print(f"Service has _ukrainian_names: {len(names)} entries")
            if "Дарія" in names:
                print(f"Дарія found in service dictionary")
                declensions = names["Дарія"].get('declensions', [])
                print(f"Declensions: {declensions}")
            else:
                print("Дарія NOT found in service dictionary")
        else:
            print("Service doesn't have _ukrainian_names attribute")

    except Exception as e:
        print(f"Error accessing service dictionary: {e}")

    # Test direct role tagging
    print(f"\n--- Direct role check ---")
    tokens = ["Павлової", "Дар'ї", "Юріївни"]
    for token in tokens:
        try:
            tagged = service._tag_roles([token], "uk")
            print(f"{token} -> {tagged}")
        except Exception as e:
            print(f"Error tagging {token}: {e}")

if __name__ == "__main__":
    debug_role_tagging()