#!/usr/bin/env python3
"""
Отладка назначения ролей токенам.
"""

import os
import sys
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
    'ENFORCE_NOMINATIVE': 'false',  # Отключаем двойную морфологию
    'DEBUG_TRACING': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_role_assignment():
    """Детальная отладка назначения ролей."""
    print("🔍 ОТЛАДКА НАЗНАЧЕНИЯ РОЛЕЙ")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        text = "Павлової Дарʼї Юріївни"
        print(f"📝 Тест: '{text}'")

        result = service.normalize_sync(
            text=text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n✅ Результат: '{result.normalized}'")
        print(f"✅ Токены: {result.tokens}")

        print(f"\n🔍 ДЕТАЛЬНЫЙ TRACE АНАЛИЗ:")
        for i, trace in enumerate(result.trace):
            if hasattr(trace, 'token'):
                print(f"  {i:2d}: '{trace.token}' → role='{trace.role}' → output='{trace.output}'")
                if trace.notes:
                    print(f"      notes: {trace.notes[:100]}...")
            else:
                print(f"  {i:2d}: {trace}")

        print(f"\n🔍 ОЖИДАЕМЫЙ ПОРЯДОК:")
        print(f"   Павлова (surname) → Дарʼя (given) → Юріївна (patronymic)")
        print(f"   Должно быть: 'Павлова Дарʼя Юріївна'")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_role_assignment()