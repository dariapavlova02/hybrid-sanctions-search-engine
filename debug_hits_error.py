#!/usr/bin/env python3
"""
Debug script to reproduce the .hits attribute error
"""

import sys
import traceback
import json

sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from ai_service.data.dicts import get_lexicons

def debug_hits_error():
    """Debug the hits attribute error."""
    print("🔍 DEBUGGING .hits ATTRIBUTE ERROR")
    print("=" * 50)

    try:
        # Create factory instance
        lexicons = get_lexicons()
        name_dictionaries = lexicons.get('name_dictionaries', {})
        diminutive_maps = lexicons.get('diminutive_maps', {})

        factory = NormalizationFactory(
            name_dictionaries,
            diminutive_maps
        )

        # Test configuration
        config = NormalizationConfig(
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            enable_spacy_uk_ner=False,  # Disable NER initially
            enable_spacy_en_ner=False,
            enable_spacy_ru_ner=False
        )

        # Test text that fails in production
        test_text = "Порошенка Петра"

        print(f"Testing text: '{test_text}'")
        print(f"Language: {config.language}")
        print(f"NER disabled for debugging")

        # Try normalization
        result = factory.normalize(test_text, config)
        print(f"✅ Success without NER: {result.normalized}")

        # Now test with NER enabled
        print("\n🔍 Testing with NER enabled...")
        config.enable_spacy_uk_ner = True

        result = factory.normalize(test_text, config)
        print(f"✅ Success with NER: {result.normalized}")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()

        # Try to identify the source
        tb = traceback.extract_tb(e.__traceback__)
        for frame in tb:
            print(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            print(f"Code: {frame.line}")

if __name__ == "__main__":
    debug_hits_error()