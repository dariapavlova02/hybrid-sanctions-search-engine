#!/usr/bin/env python3
"""
Расширенный тест генерации паттернов по тирам с документными паттернами
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator


def test_advanced_tier_generation():
    """Расширенный тест генерации паттернов по тирам"""
    generator = HighRecallACGenerator()
    
    # Тестовые данные с документными паттернами
    test_cases = [
        {
            "text": "Петр Олександрович Порошенко, паспорт АА123456",
            "language": "uk",
            "description": "Украинское имя с паспортом"
        },
        {
            "text": "John Smith, passport AA123456",
            "language": "en", 
            "description": "Английское имя с паспортом"
        },
        {
            "text": "ИНН 1234567890, ООО Компания",
            "language": "ru",
            "description": "ИНН и компания"
        },
        {
            "text": "IBAN UA123456789012345678901234567",
            "language": "uk",
            "description": "IBAN номер"
        },
        {
            "text": "Петр Smith, passport AA123456, ИНН 1234567890",
            "language": "mixed",
            "description": "Смешанный режим с документами"
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n=== Тест {i+1}: {case['description']} ===")
        print(f"Текст: {case['text']}")
        print(f"Язык: {case['language']}")
        
        # Генерируем паттерны
        patterns = generator.generate_high_recall_patterns(
            text=case['text'],
            language=case['language']
        )
        
        print(f"Всего паттернов: {len(patterns)}")
        
        # Группируем по тирам
        tiers = {}
        for pattern in patterns:
            tier = pattern.recall_tier
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(pattern)
        
        # Выводим статистику по тирам
        for tier in sorted(tiers.keys()):
            tier_patterns = tiers[tier]
            print(f"\nTier {tier}: {len(tier_patterns)} паттернов")
            
            # Показываем все паттерны для анализа
            for j, pattern in enumerate(tier_patterns):
                print(f"  {j+1}. {pattern.pattern} ({pattern.pattern_type})")
        
        # Проверяем экспорт
        export_data = generator.export_for_high_recall_ac(patterns)
        print(f"\nЭкспорт по тирам:")
        for tier_name, tier_data in export_data.items():
            print(f"  {tier_name}: {len(tier_data)} элементов")
            if tier_data:
                print(f"    Пример: {tier_data[0]}")


if __name__ == "__main__":
    test_advanced_tier_generation()
