#!/usr/bin/env python3
"""
Проверка переменных окружения и конфигурации
"""
import sys
import os
sys.path.insert(0, 'src')

def check_config():
    print("🔍 Проверка конфигурации...")

    # Проверим переменные окружения
    print("=== Переменные окружения ===")
    env_vars = [
        "ENABLE_AHO_CORASICK",
        "AHO_CORASICK_CONFIDENCE_BONUS",
        "ENABLE_SMART_FILTER",
        "ALLOW_SMART_FILTER_SKIP",
        "ENABLE_SEARCH"
    ]

    for var in env_vars:
        value = os.getenv(var, "НЕ УСТАНОВЛЕНА")
        print(f"{var}: {value}")

    # Проверим SERVICE_CONFIG
    print("\n=== SERVICE_CONFIG ===")
    try:
        from ai_service.config import SERVICE_CONFIG
        print(f"enable_aho_corasick: {SERVICE_CONFIG.enable_aho_corasick}")
        print(f"aho_corasick_confidence_bonus: {SERVICE_CONFIG.aho_corasick_confidence_bonus}")
        print(f"enable_smart_filter: {SERVICE_CONFIG.enable_smart_filter}")
        print(f"allow_smart_filter_skip: {SERVICE_CONFIG.allow_smart_filter_skip}")
        print(f"enable_search: {SERVICE_CONFIG.enable_search}")
    except Exception as e:
        print(f"Ошибка загрузки config: {e}")

    # Тест SmartFilter с текущей конфигурацией
    print("\n=== Тест SmartFilter ===")
    try:
        from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService

        smart_filter = SmartFilterService(
            language_service=None,
            signal_service=None,
            enable_terrorism_detection=True,
            enable_aho_corasick=True  # Принудительно включаем
        )

        test_text = "Ковриков Роман Валерійович"
        result = smart_filter.should_process_text(test_text)

        print(f"Текст: {test_text}")
        print(f"Should process: {result.should_process}")
        print(f"Confidence: {result.confidence}")

        ac_details = result.signal_details.get('aho_corasick_matches', {})
        print(f"AC matches: {ac_details.get('total_matches', 0)}")
        print(f"AC enabled: {ac_details.get('enabled', False)}")

    except Exception as e:
        print(f"Ошибка SmartFilter: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_config()