#!/usr/bin/env python3
"""
Максимально простой тест нормализации
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.services.normalization_service import NormalizationService


def test_simple_normalization():
    """Простой тест нормализации без async"""
    print("Инициализация сервиса нормализации...")
    
    try:
        service = NormalizationService()
        print("Сервис инициализирован успешно!")
        
        test_texts = [
            "Платіж ТОВ УПР по договору №5",
            "Володенька Путин",
            "Павлова Дарʼя Юріївна"
        ]
        
        print("\nТестирование нормализации:")
        print("=" * 50)
        
        for i, text in enumerate(test_texts, 1):
            print(f"\n{i}. Исходный текст: {text}")
            
            try:
                # Простой вызов без async
                result = service.normalize_sync(
                    text=text,
                    language="auto",
                    clean_unicode=True,
                    preserve_names=True
                )
                
                print(f"   Нормализованный: {result.normalized_text}")
                print(f"   Язык: {result.language}")
                print(f"   Успешно: {result.success}")
                
                if result.errors:
                    print(f"   Ошибки: {result.errors}")
                    
            except Exception as e:
                print(f"   ОШИБКА: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 50)
        print("Тест завершен!")
        
    except Exception as e:
        print(f"Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_simple_normalization()
