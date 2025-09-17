#!/usr/bin/env python3
"""
Простой канареечный тест для проверки работы инфраструктуры.
"""

import pytest
from pathlib import Path
import yaml

# Add src to path for module imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


def test_canary_data_files_exist():
    """Проверяет, что все YAML файлы с данными существуют."""
    data_dir = Path(__file__).parent / "data"
    
    required_files = [
        "dangerous_surnames.yml",
        "transliteration.yml", 
        "homoglyphs.yml",
        "apostrophes.yml",
        "hyphenated.yml",
        "org_context.yml"
    ]
    
    for filename in required_files:
        file_path = data_dir / filename
        assert file_path.exists(), f"Missing data file: {filename}"
        
        # Проверяем, что файл валидный YAML
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            assert 'cases' in data, f"Invalid YAML structure in {filename}: missing 'cases' key"
            assert len(data['cases']) > 0, f"No test cases in {filename}"


def test_canary_data_structure():
    """Проверяет структуру данных в YAML файлах."""
    data_dir = Path(__file__).parent / "data"
    
    for yaml_file in data_dir.glob("*.yml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        assert 'cases' in data, f"Missing 'cases' key in {yaml_file.name}"
        
        for i, case in enumerate(data['cases']):
            assert 'name' in case, f"Missing 'name' in case {i} of {yaml_file.name}"
            assert 'input' in case, f"Missing 'input' in case {i} of {yaml_file.name}"
            assert 'invariants' in case, f"Missing 'invariants' in case {i} of {yaml_file.name}"
            
            # Проверяем, что input не пустой
            assert len(case['input'].strip()) > 0, f"Empty input in case {i} of {yaml_file.name}"


def test_canary_suite_import():
    """Проверяет, что CanaryTestSuite можно импортировать."""
    try:
        from tests.canary.test_canary_suites import CanaryTestSuite
        suite = CanaryTestSuite()
        assert hasattr(suite, 'normalize_text')
        assert hasattr(suite, 'check_invariants')
        assert hasattr(suite, 'load_canary_data')
    except ImportError as e:
        pytest.fail(f"Failed to import CanaryTestSuite: {e}")


def test_property_suite_import():
    """Проверяет, что property тесты можно импортировать."""
    try:
        from tests.property.test_normalization_properties import TestNormalizationProperties
        from tests.property.test_normalization_properties import PROPERTY_SETTINGS
        from tests.property.test_normalization_properties import letters_only, is_feminine
        # Проверяем, что класс и функции существуют
        assert hasattr(TestNormalizationProperties, 'test_idempotence')
        assert hasattr(TestNormalizationProperties, 'test_preserve_feminine')
        assert callable(letters_only)
        assert callable(is_feminine)
    except ImportError as e:
        pytest.fail(f"Failed to import property test components: {e}")


def test_canary_markers():
    """Проверяет, что маркеры pytest настроены правильно."""
    # Простая проверка, что маркеры определены в conftest.py
    import tests.conftest
    assert hasattr(tests.conftest, 'pytest_configure'), "pytest_configure not found in conftest.py"


def test_command_line_options():
    """Проверяет, что опции командной строки добавлены."""
    # Простая проверка, что функция добавления опций определена
    import tests.conftest
    assert hasattr(tests.conftest, 'pytest_addoption'), "pytest_addoption not found in conftest.py"
