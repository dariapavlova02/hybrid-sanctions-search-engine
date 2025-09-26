#!/usr/bin/env python3
"""
Простой тест AC генерации паттернов для Ulianova
"""

def test_manual_patterns():
    """Проверим какие паттерны должны генерироваться"""

    print("🔍 РУЧНАЯ ПРОВЕРКА AC ПАТТЕРНОВ")
    print("=" * 60)

    name = "Ulianova Liudmyla Oleksandrivna"
    search_query = "Liudmyla Ulianova"

    print(f"Исходное имя: {name}")
    print(f"Поиск: {search_query}")

    # Ожидаемые паттерны которые должны генерироваться
    expected_patterns = [
        # Полное имя
        "Ulianova Liudmyla Oleksandrivna",
        "ULIANOVA LIUDMYLA OLEKSANDRIVNA",
        "ulianova liudmyla oleksandrivna",

        # Без отчества
        "Ulianova Liudmyla",
        "ULIANOVA LIUDMYLA",
        "ulianova liudmyla",

        # Перестановки
        "Liudmyla Ulianova Oleksandrivna",
        "LIUDMYLA ULIANOVA OLEKSANDRIVNA",
        "liudmyla ulianova oleksandrivna",

        "Liudmyla Ulianova",
        "LIUDMYLA ULIANOVA",
        "liudmyla ulianova",

        # Инициалы
        "Ulianova L. O.",
        "Ulianova L.",
        "L. Ulianova",
    ]

    print(f"\n📊 ОЖИДАЕМЫЕ ПАТТЕРНЫ ({len(expected_patterns)}):")
    for i, pattern in enumerate(expected_patterns, 1):
        print(f"   {i:2d}. {pattern}")

    # Проверяем какие из них покрывают наш запрос
    matching = []
    for pattern in expected_patterns:
        if search_query.lower() == pattern.lower():
            matching.append(pattern)

    print(f"\n🎯 ДОЛЖНЫ НАХОДИТЬ НАШ ЗАПРОС ({len(matching)}):")
    for pattern in matching:
        print(f"   ✅ {pattern}")

    if not matching:
        print("   ❌ Ни один ожидаемый паттерн не найдет наш запрос!")
        print("   🔧 Значит нужно улучшить генерацию паттернов")

    return matching

def test_load_actual_patterns():
    """Попробуем загрузить реальные паттерны"""

    print(f"\n🔍 ЗАГРУЗКА РЕАЛЬНЫХ ПАТТЕРНОВ:")
    print("=" * 60)

    # Попробуем найти файлы с паттернами
    import glob
    import json

    pattern_files = glob.glob('/Users/dariapavlova/Desktop/ai-service/**/*pattern*.json', recursive=True)

    print(f"📁 Найдено файлов паттернов: {len(pattern_files)}")

    for file_path in pattern_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

                if isinstance(data, list):
                    patterns = data
                elif isinstance(data, dict):
                    patterns = data.get('patterns', [])
                else:
                    continue

                print(f"\n📄 {file_path.split('/')[-1]}: {len(patterns)} паттернов")

                # Ищем упоминания Ulianova или Liudmyla
                ulianova_patterns = []
                for pattern in patterns[:1000]:  # Первые 1000 для скорости
                    pattern_str = str(pattern).lower()
                    if ('ulianova' in pattern_str and 'liudmyla' in pattern_str) or \
                       ('liudmyla' in pattern_str and 'ulianova' in pattern_str):
                        ulianova_patterns.append(str(pattern))

                if ulianova_patterns:
                    print(f"   ✅ Найдено Ulianova паттернов: {len(ulianova_patterns)}")
                    for pattern in ulianova_patterns[:5]:
                        print(f"      {pattern}")
                    if len(ulianova_patterns) > 5:
                        print(f"      ... и еще {len(ulianova_patterns) - 5}")
                else:
                    print(f"   ❌ Ulianova паттернов не найдено")

        except Exception as e:
            print(f"   ❌ Ошибка чтения {file_path}: {e}")

def main():
    matching = test_manual_patterns()
    test_load_actual_patterns()

    print(f"\n🎯 ВЫВОД:")
    if matching:
        print("✅ Теоретически паттерны должны найти наш запрос")
        print("❓ Проблема может быть в:")
        print("   • AC индекс не содержит нужные паттерны")
        print("   • Проблемы с нормализацией при поиске")
        print("   • Elasticsearch/AC connection issues")
    else:
        print("❌ Генерация паттернов не создает нужные перестановки")
        print("🔧 Нужно улучшить AC generator для генерации всех перестановок имен")

if __name__ == "__main__":
    main()