#!/usr/bin/env python3
"""
Тест простого случая
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService

def test_simple_case():
    """Тест простого случая"""
    service = NormalizationService()

    result = service.normalize("Иван Петров", language='ru')
    print(f"Результат: '{result.normalized_text}'")
    print(f"Токены: {result.tokens}")

if __name__ == "__main__":
    test_simple_case()