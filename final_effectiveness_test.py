#!/usr/bin/env python3
"""
Финальный тест эффективности наших 1,892 стоп-слов
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.data.dicts.stopwords import STOP_ALL

def final_effectiveness_test():
    """Финальный тест всей системы"""

    print("🏆 ФИНАЛЬНЫЙ ТЕСТ ЭФФЕКТИВНОСТИ СТОП-СЛОВ")
    print("=" * 70)
    print(f"📚 Общее количество стоп-слов: {len(STOP_ALL)}")

    # Сложные реальные случаи для финального теста
    test_cases = [
        {
            "name": "Сложный платеж с адресом и датой рождения",
            "text": "оплата коммунальных услуг 2024 київ вулиця пушкіна 62 кв 88 коваленко анна сергіївна 15.03.1985 року народження ІНН 1234567890 сума 5000 грн поповнення рахунку 533481",
            "expected_names": ["коваленко", "анна", "сергіївна"],
        },
        {
            "name": "ФОП с юридической формой",
            "text": "фоп сидоренко микола васильович єдрпоу 12345678 стандартний курс молодіжна кп 76 село городня оплата послуг 2023 интернет",
            "expected_names": ["сидоренко", "микола", "васильович"],
        },
        {
            "name": "Английское имя с техническими деталями",
            "text": "payment smith john michael invoice 2024-456 company services 64 80 92 rules procedures norms dob 1995-04-15",
            "expected_names": ["smith", "john", "michael"],
        },
        {
            "name": "Смешанный текст с мусором",
            "text": "петренко ольга іванівна 67 58 кп ек єп курс стандартний правила норми коли якщо село центральний сучасний 55 96",
            "expected_names": ["петренко", "ольга", "іванівна"],
        },
        {
            "name": "Деловой контекст с организацией",
            "text": "тов приватбанк компании стандарт процедури молодіжне село центральний 2024 іванов сергій олександрович директор курс",
            "expected_names": ["іванов", "сергій", "олександрович"],
        }
    ]

    total_tokens_original = 0
    total_tokens_filtered = 0
    total_names_found = 0
    total_names_expected = 0

    print(f"\n🧪 ТЕСТИРОВАНИЕ {len(test_cases)} СЛОЖНЫХ СЛУЧАЕВ:")

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'-' * 60}")
        print(f"ТЕСТ {i}: {case['name']}")
        print(f"Текст: {case['text']}")

        # Токенизация
        tokens = case['text'].lower().split()
        original_count = len(tokens)

        # Фильтрация стоп-словами
        filtered_tokens = []
        removed_tokens = []

        for token in tokens:
            # Очистка от пунктуации для лучшего сопоставления
            clean_token = ''.join(c for c in token if c.isalnum())

            if clean_token and len(clean_token) >= 2:
                if clean_token in STOP_ALL:
                    removed_tokens.append(clean_token)
                else:
                    filtered_tokens.append(clean_token)

        filtered_count = len(filtered_tokens)
        removed_count = len(removed_tokens)

        # Анализ эффективности
        filter_percentage = (removed_count / original_count) * 100 if original_count > 0 else 0

        print(f"📊 Исходных токенов: {original_count}")
        print(f"🚫 Отфильтровано: {removed_count} ({filter_percentage:.1f}%)")
        print(f"✅ Осталось: {filtered_count}")

        # Проверка найденных имен
        expected_names = case.get('expected_names', [])
        found_names = [token for token in expected_names if token in filtered_tokens]
        names_success = len(found_names) == len(expected_names)

        print(f"🎯 Ожидаемые имена: {expected_names}")
        print(f"{'✅' if names_success else '❌'} Найденные имена: {found_names}")

        # Показываем что отфильтровалось
        print(f"🗑️  Отфильтрованный мусор: {removed_tokens[:15]}{'...' if len(removed_tokens) > 15 else ''}")
        print(f"📝 Оставшиеся токены: {filtered_tokens}")

        # Статистика
        total_tokens_original += original_count
        total_tokens_filtered += removed_count
        total_names_found += len(found_names)
        total_names_expected += len(expected_names)

        print(f"🏆 Результат: {'✅ УСПЕХ' if names_success and filter_percentage > 70 else '⚠️ ТРЕБУЕТ ВНИМАНИЯ'}")

    # Итоговая статистика
    overall_filter_rate = (total_tokens_filtered / total_tokens_original) * 100
    names_success_rate = (total_names_found / total_names_expected) * 100 if total_names_expected > 0 else 0

    print(f"\n" + "=" * 70)
    print("🎉 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 70)
    print(f"📊 Общая эффективность фильтрации: {overall_filter_rate:.1f}%")
    print(f"🎯 Сохранность имен: {names_success_rate:.1f}%")
    print(f"📚 Количество стоп-слов: {len(STOP_ALL)}")
    print(f"🔥 Токенов отфильтровано: {total_tokens_filtered} из {total_tokens_original}")

    print(f"\n🏆 ФИНАЛЬНАЯ ОЦЕНКА:")
    if overall_filter_rate >= 85 and names_success_rate >= 95:
        print("✅ ОТЛИЧНО! Система работает на максимальном уровне")
        print("   • Фильтрует 85%+ мусора")
        print("   • Сохраняет 95%+ имен")
        print("   • Готова к продакшену!")
    elif overall_filter_rate >= 80 and names_success_rate >= 90:
        print("✅ ХОРОШО! Система работает эффективно")
    else:
        print("⚠️ ТРЕБУЕТ ДОРАБОТКИ")

    return overall_filter_rate, names_success_rate

def compare_with_previous():
    """Сравнение с предыдущими версиями"""

    print(f"\n📈 СРАВНЕНИЕ С ПРЕДЫДУЩИМИ ВЕРСИЯМИ:")
    print("=" * 70)

    versions = [
        {"name": "Исходная версия", "stopwords": 393, "filter_rate": 60, "precision": 85},
        {"name": "После географии", "stopwords": 800, "filter_rate": 80, "precision": 92},
        {"name": "После глубокого анализа", "stopwords": 1833, "filter_rate": 97, "precision": 98},
        {"name": "ФИНАЛЬНАЯ версия", "stopwords": len(STOP_ALL), "filter_rate": 0, "precision": 0}  # Будет заполнено
    ]

    # Получаем текущие метрики
    filter_rate, precision = final_effectiveness_test()
    versions[-1]["filter_rate"] = filter_rate
    versions[-1]["precision"] = precision

    print(f"\n📊 ЭВОЛЮЦИЯ СИСТЕМЫ:")
    for version in versions:
        print(f"{version['name']:<25}: {version['stopwords']:>4} стоп-слов, фильтрация {version['filter_rate']:>5.1f}%, точность {version['precision']:>5.1f}%")

    improvement_stopwords = len(STOP_ALL) - 393
    improvement_filter = filter_rate - 60
    improvement_precision = precision - 85

    print(f"\n🚀 ОБЩИЕ УЛУЧШЕНИЯ:")
    print(f"   • Стоп-слов добавлено: +{improvement_stopwords} (+{(improvement_stopwords/393)*100:.0f}%)")
    print(f"   • Фильтрация улучшена: +{improvement_filter:.1f} процентных пунктов")
    print(f"   • Точность повышена: +{improvement_precision:.1f} процентных пунктов")

if __name__ == "__main__":
    compare_with_previous()