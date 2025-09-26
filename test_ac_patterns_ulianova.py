#!/usr/bin/env python3
"""
Проверяем генерируются ли AC паттерны для Ulianova
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def test_ac_patterns_for_ulianova():
    """Проверим генерируются ли паттерны для нашего случая"""

    print("🔍 ТЕСТ AC ПАТТЕРНОВ ДЛЯ ULIANOVA")
    print("=" * 60)

    # Целевое имя из санкций
    target_name = "Ulianova Liudmyla Oleksandrivna"

    # То что ищем (после гомоглиф-нормализации)
    search_query = "Liudmyla Ulianova"

    print(f"🎯 Целевое имя: '{target_name}'")
    print(f"🔍 Поисковый запрос: '{search_query}'")

    try:
        # Пытаемся импортировать AC generator
        from ai_service.layers.variants.templates.high_recall_ac_generator_refactored import HighRecallACGenerator

        generator = HighRecallACGenerator()

        # Генерируем паттерны для целевого имени
        patterns = generator.generate_patterns(target_name)

        print(f"\n📊 Сгенерировано паттернов: {len(patterns)}")

        # Проверяем есть ли паттерн который покроет наш поиск
        matching_patterns = []

        for pattern in patterns:
            # Проверяем разные способы совпадения
            pattern_str = pattern if isinstance(pattern, str) else pattern.get('pattern', str(pattern))

            if search_query.lower() in pattern_str.lower():
                matching_patterns.append(pattern_str)
            elif "liudmyla" in pattern_str.lower() and "ulianova" in pattern_str.lower():
                matching_patterns.append(pattern_str)

        print(f"\n🎯 НАЙДЕНО СОВПАДАЮЩИХ ПАТТЕРНОВ: {len(matching_patterns)}")

        if matching_patterns:
            print("✅ Найденные паттерны:")
            for i, pattern in enumerate(matching_patterns[:10], 1):
                print(f"   {i}. {pattern}")
            if len(matching_patterns) > 10:
                print(f"   ... и еще {len(matching_patterns) - 10}")
        else:
            print("❌ НЕ НАЙДЕНО подходящих паттернов!")
            print("\n📋 Примеры сгенерированных паттернов:")
            for i, pattern in enumerate(patterns[:10], 1):
                pattern_str = pattern if isinstance(pattern, str) else str(pattern)
                print(f"   {i}. {pattern_str}")
            if len(patterns) > 10:
                print(f"   ... и еще {len(patterns) - 10}")

        # Дополнительная проверка - ищем перестановки
        print(f"\n🔄 ПРОВЕРКА ПЕРЕСТАНОВОК:")
        permutation_checks = [
            "Liudmyla Ulianova",
            "Ulianova Liudmyla",
            "LIUDMYLA ULIANOVA",
            "ULIANOVA LIUDMYLA",
            "liudmyla ulianova",
            "ulianova liudmyla"
        ]

        for perm in permutation_checks:
            found = False
            for pattern in patterns:
                pattern_str = pattern if isinstance(pattern, str) else str(pattern)
                if perm.lower() == pattern_str.lower().strip():
                    found = True
                    print(f"   ✅ '{perm}' найдена в паттернах")
                    break
            if not found:
                print(f"   ❌ '{perm}' НЕ найдена в паттернах")

    except ImportError as e:
        print(f"❌ Не удалось импортировать AC generator: {e}")

        # Альтернативная проверка - читаем готовые паттерны из файла
        try:
            import json
            with open('/Users/dariapavlova/Desktop/ai-service/src/high_recall_ac_patterns_sample.json', 'r') as f:
                patterns_data = json.load(f)
                patterns = patterns_data.get('patterns', [])

                print(f"📁 Загружено паттернов из файла: {len(patterns)}")

                # Ищем подходящие
                matching = []
                for pattern in patterns:
                    if "liudmyla" in pattern.lower() and "ulianova" in pattern.lower():
                        matching.append(pattern)

                if matching:
                    print(f"✅ Найдено в файле: {len(matching)} паттернов")
                    for pattern in matching[:5]:
                        print(f"   {pattern}")
                else:
                    print("❌ В файле паттернов не найдено подходящих")

        except Exception as file_e:
            print(f"❌ Не удалось прочитать файл паттернов: {file_e}")

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

def main():
    test_ac_patterns_for_ulianova()

    print(f"\n🎯 ЗАКЛЮЧЕНИЕ:")
    print("   Если AC паттерны не содержат 'Liudmyla Ulianova',")
    print("   то проблема в генерации паттернов, а не в поиске!")

if __name__ == "__main__":
    main()