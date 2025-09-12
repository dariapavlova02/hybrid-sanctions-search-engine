#!/usr/bin/env python3
"""
Строгий тест для извлечения имен без моков.
Проверяет реальную морфологическую нормализацию.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ai_service.orchestration.clean_orchestrator import CleanOrchestratorService
from ai_service.config.settings import ServiceConfig


def test_strict_name_extraction():
    """Строгий тест извлечения имен без моков."""
    print("🔍 Strict Name Extraction Test (No Mocks)")
    print("=" * 60)
    
    # Создаем реальный сервис без моков
    config = ServiceConfig(
        enable_morphology=True,
        enable_transliterations=True,
        preserve_names=True,
        enable_advanced_features=True
    )
    
    orchestrator = CleanOrchestratorService(config)
    
    # Тестовый случай: "Оплата от Петра Порошенка по Договору 123"
    # Ожидаемый результат: "Петро Порошенко" (именительный падеж)
    input_text = "Оплата от Петра Порошенка по Договору 123"
    
    print(f"Input: '{input_text}'")
    print(f"Expected: Names should be normalized to nominative case")
    print(f"Expected: 'Петра' -> 'Петро', 'Порошенка' -> 'Порошенко'")
    print()
    
    # Обрабатываем текст
    result = orchestrator.process_text(input_text)
    
    print(f"Success: {result.success}")
    print(f"Language: {result.context.language}")
    print(f"Normalized text: '{result.context.current_text}'")
    print(f"Processing time: {result.processing_time_ms}ms")
    
    if result.errors:
        print(f"Errors: {result.errors}")
    
    # СТРОГИЕ ПРОВЕРКИ
    assert result.success, f"Pipeline failed: {result.errors}"
    
    normalized_text = result.context.current_text.lower()
    
    # Проверяем, что имена были нормализованы к именительному падежу
    # "Петра" должно стать "Петро", "Порошенка" должно стать "Порошенко"
    
    # Проверка 1: Имя "Петро" должно присутствовать в нормализованном тексте
    assert "петро" in normalized_text, f"Expected 'петро' in normalized text, got: '{normalized_text}'"
    
    # Проверка 2: Имя "Порошенко" должно присутствовать в нормализованном тексте  
    assert "порошенко" in normalized_text, f"Expected 'порошенко' in normalized text, got: '{normalized_text}'"
    
    # Проверка 3: Исходные формы в родительном падеже НЕ должны присутствовать
    assert "петра" not in normalized_text, f"Original genitive form 'петра' should not be in normalized text: '{normalized_text}'"
    assert "порошенка" not in normalized_text, f"Original genitive form 'порошенка' should not be in normalized text: '{normalized_text}'"
    
    # Проверка 4: Имена должны быть рядом друг с другом
    # Ищем позиции имен в тексте
    petro_pos = normalized_text.find("петро")
    pорошенко_pos = normalized_text.find("порошенко")
    
    assert petro_pos != -1, "Name 'петро' not found in normalized text"
    assert pорошенко_pos != -1, "Name 'порошенко' not found in normalized text"
    
    # Проверяем, что имена находятся рядом (в пределах 20 символов)
    distance = abs(petro_pos - pорошенко_pos)
    assert distance <= 20, f"Names 'петро' and 'порошенко' are too far apart (distance: {distance})"
    
    print("✅ All strict checks passed!")
    print(f"✅ 'петро' found at position {petro_pos}")
    print(f"✅ 'порошенко' found at position {pорошенко_pos}")
    print(f"✅ Distance between names: {distance} characters")
    print(f"✅ Original genitive forms 'петра' and 'порошенка' were correctly normalized")
    
    return result


if __name__ == "__main__":
    test_strict_name_extraction()
