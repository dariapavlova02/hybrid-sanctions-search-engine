#!/usr/bin/env python3
"""
Канареечные тесты для нормализации имён.

Этот модуль содержит фиксированные кейсы, которые исторически ломали нормализацию.
Цель: предотвратить регрессии в критических сценариях нормализации.

Тестируемые категории:
- Опасные фамилии (короткие, частые, омонимы)
- Транслиты (ru↔uk↔en), смешанные скрипты
- Гомоглифы (латинская a/о/е в кириллице, bidi)
- Апострофы (' vs ')
- Дефисные фамилии (двойные), инициалы с точками
- Org-контекст (ООО/ТОВ/LLC + CAPS), чтобы не утекало в person
"""

import os
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

import pytest

# Add src to path for module imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from ai_service.utils.feature_flags import get_feature_flag_manager, FeatureFlags


@dataclass
class CanaryInvariant:
    """Инвариант для проверки в канареечных тестах."""
    must_contain: Optional[List[str]] = None
    must_not_contain: Optional[List[str]] = None
    feminine_required: Optional[bool] = None
    hyphen_preserved: Optional[bool] = None
    initials_dot: Optional[bool] = None


@dataclass
class CanaryCase:
    """Канареечный тестовый кейс."""
    name: str
    input: str
    invariants: CanaryInvariant


class CanaryTestSuite:
    """Базовый класс для канареечных тестов."""
    
    def __init__(self):
        self.normalization_service = NormalizationService()
        self.feature_flags = get_feature_flag_manager()
        
    def load_canary_data(self, data_file: str) -> List[CanaryCase]:
        """Загружает канареечные данные из YAML файла."""
        data_path = Path(__file__).parent / "data" / data_file
        with open(data_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        cases = []
        for case_data in data['cases']:
            invariants = CanaryInvariant(**case_data.get('invariants', {}))
            case = CanaryCase(
                name=case_data['name'],
                input=case_data['input'],
                invariants=invariants
            )
            cases.append(case)
        
        return cases
    
    def normalize_text(self, text: str, flags: Optional[Dict[str, Any]] = None) -> Any:
        """Нормализует текст с помощью factory normalizer."""
        if flags is None:
            flags = {
                'remove_stop_words': False,
                'preserve_names': True,
                'enable_advanced_features': True
            }
        
        # Создаем конфигурацию для factory
        config = NormalizationConfig(
            remove_stop_words=flags.get('remove_stop_words', False),
            preserve_names=flags.get('preserve_names', True),
            enable_advanced_features=flags.get('enable_advanced_features', True)
        )
        
        # Создаем factory с конфигурацией
        factory = NormalizationFactory(config=config)
        
        # Нормализуем текст
        result = factory.normalize(text)
        return result
    
    def check_invariants(self, result: Any, invariants: CanaryInvariant) -> List[str]:
        """Проверяет инварианты для результата нормализации."""
        violations = []
        
        if not hasattr(result, 'normalized'):
            violations.append("Result missing 'normalized' attribute")
            return violations
        
        normalized = result.normalized
        tokens = getattr(result, 'tokens', [])
        
        # Проверка must_contain
        if invariants.must_contain:
            for required_token in invariants.must_contain:
                if required_token not in normalized:
                    violations.append(f"Missing required token: '{required_token}'")
        
        # Проверка must_not_contain
        if invariants.must_not_contain:
            for forbidden_token in invariants.must_not_contain:
                if forbidden_token in normalized:
                    violations.append(f"Contains forbidden token: '{forbidden_token}'")
        
        # Проверка feminine_required
        if invariants.feminine_required is not None:
            # Простая проверка на женские суффиксы
            feminine_suffixes = ['а', 'я', 'ова', 'ева', 'іна', 'ївна', 'овна', 'евна']
            has_feminine = any(normalized.endswith(suffix) for suffix in feminine_suffixes)
            if invariants.feminine_required and not has_feminine:
                violations.append("Expected feminine form but found masculine")
            elif not invariants.feminine_required and has_feminine:
                violations.append("Expected masculine form but found feminine")
        
        # Проверка hyphen_preserved
        if invariants.hyphen_preserved is not None:
            has_hyphen = '-' in normalized
            if invariants.hyphen_preserved and not has_hyphen:
                violations.append("Expected hyphen to be preserved")
            elif not invariants.hyphen_preserved and has_hyphen:
                violations.append("Unexpected hyphen found")
        
        # Проверка initials_dot
        if invariants.initials_dot is not None:
            has_initials_dot = any(token.endswith('.') for token in tokens)
            if invariants.initials_dot and not has_initials_dot:
                violations.append("Expected initials with dots")
            elif not invariants.initials_dot and has_initials_dot:
                violations.append("Unexpected initials with dots")
        
        return violations
    
    def measure_performance(self, text: str, iterations: int = 50) -> Dict[str, float]:
        """Измеряет производительность нормализации."""
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            self.normalize_text(text)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        times.sort()
        p95_index = int(len(times) * 0.95)
        
        return {
            'average': sum(times) / len(times),
            'p95': times[p95_index],
            'min': min(times),
            'max': max(times)
        }


# Фикстуры для тестов
@pytest.fixture(scope="module")
def canary_suite():
    """Фикстура для канареечного тестового набора."""
    return CanaryTestSuite()


@pytest.fixture(scope="module")
def dangerous_surnames_cases(canary_suite):
    """Фикстура для кейсов опасных фамилий."""
    return canary_suite.load_canary_data("dangerous_surnames.yml")


@pytest.fixture(scope="module")
def transliteration_cases(canary_suite):
    """Фикстура для кейсов транслитерации."""
    return canary_suite.load_canary_data("transliteration.yml")


@pytest.fixture(scope="module")
def homoglyphs_cases(canary_suite):
    """Фикстура для кейсов гомоглифов."""
    return canary_suite.load_canary_data("homoglyphs.yml")


@pytest.fixture(scope="module")
def apostrophes_cases(canary_suite):
    """Фикстура для кейсов апострофов."""
    return canary_suite.load_canary_data("apostrophes.yml")


@pytest.fixture(scope="module")
def hyphenated_cases(canary_suite):
    """Фикстура для кейсов дефисных фамилий."""
    return canary_suite.load_canary_data("hyphenated.yml")


@pytest.fixture(scope="module")
def org_context_cases(canary_suite):
    """Фикстура для кейсов организационного контекста."""
    return canary_suite.load_canary_data("org_context.yml")


# Параметризованные тесты для каждой категории
def test_dangerous_surnames(canary_suite, case):
    """Тест опасных фамилий (короткие, частые, омонимы)."""
    result = canary_suite.normalize_text(case.input)
    violations = canary_suite.check_invariants(result, case.invariants)
    
    if violations:
        pytest.fail(f"Invariant violations for '{case.input}': {violations}")


def test_transliteration(canary_suite, case):
    """Тест транслитерации (ru↔uk↔en), смешанные скрипты."""
    result = canary_suite.normalize_text(case.input)
    violations = canary_suite.check_invariants(result, case.invariants)
    
    if violations:
        pytest.fail(f"Invariant violations for '{case.input}': {violations}")


def test_homoglyphs(canary_suite, case):
    """Тест гомоглифов (латинская a/о/е в кириллице, bidi)."""
    result = canary_suite.normalize_text(case.input)
    violations = canary_suite.check_invariants(result, case.invariants)
    
    if violations:
        pytest.fail(f"Invariant violations for '{case.input}': {violations}")


def test_apostrophes(canary_suite, case):
    """Тест апострофов (' vs ')."""
    result = canary_suite.normalize_text(case.input)
    violations = canary_suite.check_invariants(result, case.invariants)
    
    if violations:
        pytest.fail(f"Invariant violations for '{case.input}': {violations}")


def test_hyphenated(canary_suite, case):
    """Тест дефисных фамилий (двойные), инициалы с точками."""
    result = canary_suite.normalize_text(case.input)
    violations = canary_suite.check_invariants(result, case.invariants)
    
    if violations:
        pytest.fail(f"Invariant violations for '{case.input}': {violations}")


def test_org_context(canary_suite, case):
    """Тест org-контекста (ООО/ТОВ/LLC + CAPS), чтобы не утекало в person."""
    result = canary_suite.normalize_text(case.input)
    violations = canary_suite.check_invariants(result, case.invariants)
    
    if violations:
        pytest.fail(f"Invariant violations for '{case.input}': {violations}")


# Тесты производительности
@pytest.mark.parametrize("text", [
    "Иван Петров",
    "Олександр Петренко",
    "John Smith",
    "Жан-Батист O'Connor",
    "Александр-Марія Петров-Сидоров"
])
def test_performance_short_texts(canary_suite, text):
    """Тест производительности на коротких текстах."""
    if pytest.config.getoption("--strict-perf", default=False):
        perf = canary_suite.measure_performance(text)
        
        if perf['p95'] > 10.0:  # 10ms threshold
            pytest.fail(f"Performance threshold exceeded: p95={perf['p95']:.2f}ms > 10ms")


# Тесты с разными флагами
@pytest.mark.parametrize("flags", [
    {'remove_stop_words': False, 'preserve_names': True, 'enable_advanced_features': True},
    {'remove_stop_words': True, 'preserve_names': True, 'enable_advanced_features': True},
    {'remove_stop_words': False, 'preserve_names': False, 'enable_advanced_features': True},
    {'remove_stop_words': False, 'preserve_names': True, 'enable_advanced_features': False},
])
def test_flags_behavior(canary_suite, flags):
    """Тест поведения с разными флагами."""
    test_text = "Иван Петров"
    result = canary_suite.normalize_text(test_text, flags)
    
    # Базовые проверки
    assert hasattr(result, 'normalized')
    assert isinstance(result.normalized, str)
    assert len(result.normalized) > 0


# Хелпер для создания параметризованных тестов
def pytest_generate_tests(metafunc):
    """Генерирует параметризованные тесты для канареечных кейсов."""
    if "case" in metafunc.fixturenames:
        # Определяем какой файл данных использовать
        test_name = metafunc.function.__name__
        data_file_map = {
            'test_dangerous_surnames': 'dangerous_surnames.yml',
            'test_transliteration': 'transliteration.yml',
            'test_homoglyphs': 'homoglyphs.yml',
            'test_apostrophes': 'apostrophes.yml',
            'test_hyphenated': 'hyphenated.yml',
            'test_org_context': 'org_context.yml',
        }
        
        if test_name in data_file_map:
            data_file = data_file_map[test_name]
            data_path = Path(__file__).parent / "data" / data_file
            
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                cases = []
                for case_data in data['cases']:
                    invariants = CanaryInvariant(**case_data.get('invariants', {}))
                    case = CanaryCase(
                        name=case_data['name'],
                        input=case_data['input'],
                        invariants=invariants
                    )
                    cases.append(case)
                
                metafunc.parametrize("case", cases, indirect=True)


# Хук для добавления опций командной строки
def pytest_addoption(parser):
    """Добавляет опции командной строки для канареечных тестов."""
    parser.addoption(
        "--strict-perf",
        action="store_true",
        default=False,
        help="Enable strict performance testing (p95 < 10ms)"
    )
    parser.addoption(
        "--allow-order-swap",
        action="store_true",
        default=False,
        help="Allow order swapping in test results"
    )


# Хук для генерации отчета
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Генерирует отчет о канареечных тестах."""
    if config.getoption("--strict-perf"):
        terminalreporter.write_sep("=", "Canary Test Performance Summary")
        terminalreporter.write_line("Performance testing enabled with strict thresholds")
        terminalreporter.write_line("p95 threshold: 10ms")
        terminalreporter.write_line("")
