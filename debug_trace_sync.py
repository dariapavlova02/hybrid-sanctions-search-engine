#!/usr/bin/env python3
"""
Отладка синхронизации между токенами и trace.
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
    'DEBUG_TRACING': 'true'  # Включаем debug tracing!
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def detailed_trace_debug():
    """Детальная отладка trace vs tokens."""
    print("🔍 ДЕТАЛЬНАЯ ОТЛАДКА TRACE СИНХРОНИЗАЦИИ")
    print("="*60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        text = "Порошенка Петенька"
        print(f"📝 Тест: '{text}'")

        result = service.normalize_sync(
            text=text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n✅ Normalized: '{result.normalized}'")
        print(f"✅ Tokens: {result.tokens}")

        print(f"\n🔍 ПОЛНЫЙ TRACE ({len(result.trace)} записей):")
        for i, trace in enumerate(result.trace):
            if hasattr(trace, 'token'):
                print(f"  {i:2d}: '{trace.token}' → {trace.role} → '{trace.output}' ({trace.rule})")
                if trace.notes:
                    print(f"      Notes: {trace.notes}")
            else:
                print(f"  {i:2d}: {trace}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    detailed_trace_debug()