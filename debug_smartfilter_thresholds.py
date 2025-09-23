#!/usr/bin/env python3
"""
Отладка порогов SmartFilter
"""
import sys
sys.path.insert(0, 'src')

def debug_smartfilter_detailed():
    print("🔍 Детальная отладка SmartFilter...")

    try:
        from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
        from ai_service.config import SERVICE_CONFIG

        # Проверим конфигурацию
        print(f"AC enabled: {SERVICE_CONFIG.aho_corasick_enabled}")
        print(f"AC confidence bonus: {SERVICE_CONFIG.aho_corasick_confidence_bonus}")
        print(f"SmartFilter threshold: {getattr(SERVICE_CONFIG, 'smartfilter_threshold', 'N/A')}")

        smart_filter = SmartFilterService(
            language_service=None,
            signal_service=None,
            enable_terrorism_detection=True,
            enable_aho_corasick=True
        )

        test_text = "Ковриков Роман Валерійович"

        # Детальный анализ
        print(f"\n=== Тестирование: '{test_text}' ===")

        # 1. AC поиск напрямую
        ac_result = smart_filter.search_aho_corasick(test_text)
        print(f"AC поиск прямой: {ac_result.get('total_matches', 0)} совпадений")

        # 2. Генерация вариантов
        variants = smart_filter._generate_name_variants(test_text)
        print(f"Сгенерированные варианты: {variants}")

        # Проверим каждый вариант
        for i, variant in enumerate(variants, 1):
            variant_result = smart_filter.search_aho_corasick(variant)
            print(f"  Вариант {i} '{variant}': {variant_result.get('total_matches', 0)} совпадений")

        # 3. Полный анализ
        filter_result = smart_filter.should_process_text(test_text)
        print(f"\n=== Результат SmartFilter ===")
        print(f"Should process: {filter_result.should_process}")
        print(f"Confidence: {filter_result.confidence}")
        print(f"Detected signals: {filter_result.detected_signals}")
        print(f"Processing recommendation: {filter_result.processing_recommendation}")

        # 4. Детали сигналов
        details = filter_result.signal_details
        print(f"\n=== Детали сигналов ===")
        print(f"AC matches: {details.get('aho_corasick_matches', {})}")
        print(f"Companies: {details.get('companies', {})}")
        print(f"Names: {details.get('names', {})}")

        # 5. Анализ порога
        if filter_result.confidence > 0:
            print(f"\n=== Анализ порога ===")
            print(f"Current confidence: {filter_result.confidence}")
            print(f"Требуемый порог для обработки: вероятно > 0.1 или > 0.2")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_smartfilter_detailed()