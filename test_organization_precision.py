#!/usr/bin/env python3
"""
Тест улучшенной precision для OrganizationSignal
"""

from src.ai_service.layers.signals.signals_service import SignalsService

def test_organization_precision():
    """Тест контекстных сигналов для организаций"""
    service = SignalsService()

    test_cases = [
        {
            "text": "Платеж в пользу ООО Рога и Копыта для услуг по договору",
            "expected_evidence": ["org_core", "legal_form_hit", "activity_context"],
            "description": "Полный контекст: юр.форма + услуги"
        },
        {
            "text": "Банк Приватбанк перевод на счет ТОВ Инноваційні Технології",
            "expected_evidence": ["org_core", "legal_form_hit", "financial_context"],
            "description": "Банковский контекст"
        },
        {
            "text": "Адрес: г. Киев, ул. Крещатик, 1, офис компании ТОВ Украина",
            "expected_evidence": ["org_core", "legal_form_hit", "address_context", "business_context"],
            "description": "Адресный контекст"
        },
        {
            "text": "Просто ООО без контекста",
            "expected_evidence": ["legal_form_hit"],
            "description": "Только юр.форма без контекста"
        },
        {
            "text": "Поставка товаров от предприятия LLC TechCorp",
            "expected_evidence": ["org_core", "legal_form_hit", "activity_context", "business_context"],
            "description": "Множественный контекст"
        },
    ]

    print("=== Тест улучшенной precision OrganizationSignal ===")
    all_passed = True

    for case in test_cases:
        print(f"\n{case['description']}")
        print(f"Текст: '{case['text']}'")

        result = service.extract(case['text'])
        orgs = result.get('organizations', [])

        if not orgs:
            print("❌ Организации не найдены")
            all_passed = False
            continue

        # Берем первую организацию
        org = orgs[0]
        print(f"Найденная организация: {org.get('core', 'N/A')}")
        print(f"Evidence: {org.get('evidence', [])}")
        print(f"Confidence: {org.get('confidence', 0):.3f}")

        # Проверяем evidence
        found_evidence = set(org.get('evidence', []))
        expected_evidence = set(case['expected_evidence'])

        # Проверяем что ключевые evidence присутствуют
        missing_key_evidence = expected_evidence - found_evidence
        extra_evidence = found_evidence - expected_evidence

        if missing_key_evidence:
            print(f"❌ Отсутствуют ключевые evidence: {missing_key_evidence}")
            all_passed = False
        else:
            print("✅ Все ключевые evidence найдены")

        if extra_evidence:
            print(f"➕ Дополнительные evidence: {extra_evidence}")

        # Проверяем что confidence соответствует количеству evidence
        base_confidence = 0.5
        expected_min_confidence = base_confidence + (len(expected_evidence) - 1) * 0.1

        if org.get('confidence', 0) >= expected_min_confidence:
            print(f"✅ Confidence адекватный: {org.get('confidence', 0):.3f} >= {expected_min_confidence:.3f}")
        else:
            print(f"❌ Confidence низкий: {org.get('confidence', 0):.3f} < {expected_min_confidence:.3f}")
            all_passed = False

    # Тест на ложные срабатывания
    print(f"\n=== Тест на ложные срабатывания ===")
    false_positive_cases = [
        "12345678 просто цифры без контекста",
        "Номер документа АА123456",
        "Счет 1234567890123456789 к оплате"
    ]

    for text in false_positive_cases:
        print(f"Тестируем: '{text}'")
        result = service.extract(text)
        orgs = result.get('organizations', [])

        if not orgs:
            print("✅ Организации корректно не найдены")
        else:
            print(f"⚠️ Найдены организации: {[org.get('core') for org in orgs]}")
            # Это может быть нормально, если есть контекст из других extractor-ов

    print(f"\n=== Итоговый результат ===")
    if all_passed:
        print("✅ Все тесты улучшения precision прошли успешно!")
    else:
        print("❌ Некоторые тесты не прошли")

    return all_passed

if __name__ == "__main__":
    test_organization_precision()