#!/usr/bin/env python3
"""Debug diminutive maps for Дар'ї"""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_diminutive_maps():
    """Debug diminutive maps issue"""
    print("=== Diminutive Maps Debug ===")

    service = NormalizationService()

    token = "Дар'ї"
    token_lower = token.lower()

    print(f"Testing token: {token}")
    print(f"Token lower: {token_lower}")

    # Check dim2full_maps
    print(f"\n--- dim2full_maps ---")
    if hasattr(service, 'dim2full_maps'):
        uk_dim2full = service.dim2full_maps.get('uk', {})
        print(f"UK dim2full_maps has {len(uk_dim2full)} entries")
        print(f"'{token_lower}' in dim2full_maps: {token_lower in uk_dim2full}")
        if token_lower in uk_dim2full:
            print(f"  -> maps to: {uk_dim2full[token_lower]}")

        # Check some examples
        print("Sample entries:")
        for key in list(uk_dim2full.keys())[:5]:
            print(f"  {key} -> {uk_dim2full[key]}")
    else:
        print("No dim2full_maps attribute")

    # Check diminutive_maps
    print(f"\n--- diminutive_maps ---")
    if hasattr(service, 'diminutive_maps'):
        uk_dim = service.diminutive_maps.get('uk', {})
        print(f"UK diminutive_maps has {len(uk_dim)} entries")
        print(f"'{token_lower}' in diminutive_maps: {token_lower in uk_dim}")
        if token_lower in uk_dim:
            print(f"  -> maps to: {uk_dim[token_lower]}")

        # Check some examples
        print("Sample entries:")
        for key in list(uk_dim.keys())[:5]:
            print(f"  {key} -> {uk_dim[key]}")
    else:
        print("No diminutive_maps attribute")

    # Test morphology directly
    print(f"\n--- Morphology check ---")
    morphed = service._morph_nominal(token, "uk", True)
    print(f"Morphed result: '{morphed}'")
    if morphed:
        morphed_lower = morphed.lower()
        print(f"Morphed lower: '{morphed_lower}'")

        if hasattr(service, 'dim2full_maps'):
            uk_dim2full = service.dim2full_maps.get('uk', {})
            print(f"'{morphed_lower}' in dim2full_maps: {morphed_lower in uk_dim2full}")

        if hasattr(service, 'diminutive_maps'):
            uk_dim = service.diminutive_maps.get('uk', {})
            print(f"'{morphed_lower}' in diminutive_maps: {morphed_lower in uk_dim}")

if __name__ == "__main__":
    debug_diminutive_maps()