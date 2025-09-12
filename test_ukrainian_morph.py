#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath('src'))

from ai_service.services.ukrainian_morphology import UkrainianMorphologyAnalyzer

def test_ukrainian_morph():
    analyzer = UkrainianMorphologyAnalyzer()
    
    test_words = ['Іванова', 'Зеленського', 'Положинського', 'Петренка']
    
    for word in test_words:
        print(f"\n=== Testing: {word} ===")
        lemma = analyzer.get_lemma(word)
        print(f"Lemma: {lemma}")
        
        # Test morph analyzer directly if available
        if hasattr(analyzer, 'morph_analyzer') and analyzer.morph_analyzer:
            parses = analyzer.morph_analyzer.parse(word)
            if parses:
                print(f"Best parse: {parses[0].normal_form}")
                print(f"Tag: {parses[0].tag}")

if __name__ == "__main__":
    test_ukrainian_morph()