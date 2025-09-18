#!/usr/bin/env python3
"""
Test script for pymorphy3 analysis
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_pymorphy():
    """Test pymorphy3 analysis"""
    
    try:
        import pymorphy3
        morph = pymorphy3.MorphAnalyzer()
        
        test_tokens = ["Вики", "Дашеньки", "Вика", "Дарья"]
        
        print("Testing pymorphy3 analysis:")
        for token in test_tokens:
            parses = morph.parse(token)
            print(f"\nToken: '{token}'")
            print(f"  Parses: {len(parses)}")
            for i, parse in enumerate(parses):
                print(f"    Parse {i}: {parse.normal_form} | {parse.tag} | {parse.score}")
                if hasattr(parse, 'methods'):
                    print(f"      Methods: {parse.methods}")
    except ImportError:
        print("pymorphy3 not available")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pymorphy()
