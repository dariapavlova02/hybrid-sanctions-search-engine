#!/usr/bin/env python3
"""
Тест с принудительным включением DEBUG логов.
"""

import os
import sys
import logging
from pathlib import Path

# Set production environment variables
os.environ.update({
    'PRESERVE_FEMININE_SURNAMES': 'true',
    'ENABLE_ENHANCED_GENDER_RULES': 'true',
    'PRESERVE_FEMININE_SUFFIX_UK': 'true',
    'ENABLE_FSM_TUNED_ROLES': 'true',
    'MORPHOLOGY_CUSTOM_RULES_FIRST': 'true',
    'ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_MORPHOLOGY': 'true',
    'DEBUG_TRACING': 'true',
    'LOG_LEVEL': 'DEBUG'
})

# Force DEBUG logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_with_debug():
    """Тест с принудительным debug."""
    print("🔍 ТЕСТ С ПРИНУДИТЕЛЬНЫМ DEBUG ЛОГИРОВАНИЕМ")
    print("="*60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Enable debug logging for the specific modules
        normalization_logger = logging.getLogger("ai_service.layers.normalization")
        normalization_logger.setLevel(logging.DEBUG)

        factory_logger = logging.getLogger("ai_service.layers.normalization.processors.normalization_factory")
        factory_logger.setLevel(logging.DEBUG)

        text = "Порошенка Петенька"
        print(f"📝 Тест: '{text}'")

        result = service.normalize_sync(
            text=text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n✅ Получили: '{result.normalized}'")
        print(f"✅ Токены: {result.tokens}")

        expected = "Порошенко Петро"
        if result.normalized == expected:
            print(f"✅ УСПЕХ!")
        else:
            print(f"❌ ОШИБКА! Ожидали: '{expected}'")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_debug()