#!/usr/bin/env python3
"""Debug Чайковскому morphology issue."""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

import pymorphy3
from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_chaikovsky():
    """Debug Чайковскому morphology"""
    print("=== Чайковскому Debug ===")

    # Test direct pymorphy3
    analyzer = pymorphy3.MorphAnalyzer(lang='ru')
    parses = analyzer.parse('Чайковскому')
    print(f"Direct pymorphy3 parses for 'Чайковскому':")
    for i, p in enumerate(parses):
        print(f"  {i}: {p.normal_form} | {p.tag} | score: {p.score}")

    print(f"\nSurn parses:")
    surn_parses = [p for p in parses if 'Surn' in str(p.tag)]
    for i, p in enumerate(surn_parses):
        print(f"  {i}: {p.normal_form} | {p.tag} | score: {p.score}")

    # Test through normalization service
    service = NormalizationService()
    ru_morph = service._get_morph('ru')
    if ru_morph:
        lemma = ru_morph.get_lemma('Чайковскому')
        print(f"\nru_morph.get_lemma('Чайковскому') = '{lemma}'")

    morph_result = service._morph_nominal('Чайковскому', 'ru')
    print(f"service._morph_nominal('Чайковскому', 'ru') = '{morph_result}'")

    # Test full normalization
    full_result = service.normalize('Благодарность Петру Чайковскому', language='ru')
    print(f"Full result: '{full_result.normalized}'")

if __name__ == "__main__":
    debug_chaikovsky()