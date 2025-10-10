#!/usr/bin/env python3
"""
End-to-End Integration Tests for AI Service Pipeline

Tests all 9 layers working together according to CLAUDE.md specification:
1. Validation & Sanitization
2. Smart Filter
3. Language Detection
4. Unicode Normalization
5. Name Normalization (THE CORE)
6. Signals (enrichment)
7. Variants (optional)
8. Embeddings (optional)
9. Decision & Response

These tests reflect real payment texts and edge cases from production usage.
"""

import asyncio
import pytest
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project to path
project_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from ai_service.core.orchestrator_factory import OrchestratorFactory
from ai_service.contracts.base_contracts import UnifiedProcessingResult
from ai_service.utils.logging_config import get_logger

logger = get_logger(__name__)

# Test data structure
@dataclass
class IntegrationTestCase:
    """Test case for end-to-end pipeline testing"""
    name: str
    input_text: str
    expected_language: str
    expected_language_confidence_min: float
    expected_normalized: str
    expected_persons: List[Dict[str, Any]]
    expected_organizations: List[Dict[str, Any]]
    expected_numbers: Dict[str, Any]
    expected_dates: Dict[str, Any]
    expected_smart_filter_signals: List[str]
    expected_should_process: bool
    expected_trace_roles: List[str]  # Expected role sequence in trace
    notes: str = ""

# Real payment scenarios from CLAUDE.md specification
INTEGRATION_TEST_CASES = [
    IntegrationTestCase(
        name="ukrainian_simple_name",
        input_text="Платіж від Петра Порошенка",
        expected_language="uk",
        expected_language_confidence_min=0.8,
        expected_normalized="Петро Порошенко",
        expected_persons=[{
            "core": ["Петро", "Порошенко"],
            "full_name": "Петро Порошенко",
            "dob": None
        }],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["name"],
        expected_should_process=True,
        expected_trace_roles=["given", "surname"],
        notes="Simple Ukrainian name with proper morphology"
    ),

    IntegrationTestCase(
        name="ukrainian_full_name_with_patronymic",
        input_text="Оплата від Павлової Дар'ї Юріївни",
        expected_language="uk",
        expected_language_confidence_min=0.8,
        expected_normalized="Павлова Дар'я Юріївна",
        expected_persons=[{
            "core": ["Павлова", "Дар'я", "Юріївна"],
            "full_name": "Павлова Дар'я Юріївна",
            "dob": None
        }],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["name"],
        expected_should_process=True,
        expected_trace_roles=["surname", "given", "patronymic"],
        notes="Full Ukrainian name with patronymic - preserve women's surname form"
    ),

    IntegrationTestCase(
        name="ukrainian_company_with_legal_form",
        input_text="ТОВ 'ПриватБанк'",
        expected_language="ru",  # Short text, ТОВ can be detected as ru
        expected_language_confidence_min=0.5,
        expected_normalized="",  # No person names
        expected_persons=[],
        expected_organizations=[{
            "legal_form": "ТОВ",
            "core": "ПриватБанк",
            "full_name": "ТОВ ПриватБанк"
        }],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["company"],
        expected_should_process=True,
        expected_trace_roles=[],  # No person tokens in normalized
        notes="Company with legal form - legal form handled by Signals, not Normalization"
    ),

    IntegrationTestCase(
        name="mixed_person_and_company",
        input_text="Рахунок від П.І. Коваленко, ТОВ 'Агросвіт'",
        expected_language="uk",
        expected_language_confidence_min=0.8,
        expected_normalized="П. І. Коваленко",
        expected_persons=[{
            "core": ["П.", "І.", "Коваленко"],
            "full_name": "П. І. Коваленко",
            "dob": None
        }],
        expected_organizations=[{
            "legal_form": "ТОВ",
            "core": "Агросвіт",
            "full_name": "ТОВ Агросвіт"
        }],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["name", "company"],
        expected_should_process=True,
        expected_trace_roles=["initial", "initial", "surname"],
        notes="Mixed person with initials and company - proper initial formatting"
    ),

    IntegrationTestCase(
        name="person_with_birth_date",
        input_text="Перерахунок для Іванова Івана Івановича, дата народження 12.05.1980",
        expected_language="uk",
        expected_language_confidence_min=0.8,
        expected_normalized="Іванов Іван Іванович",
        expected_persons=[{
            "core": ["Іванов", "Іван", "Іванович"],
            "full_name": "Іванов Іван Іванович",
            "dob": "1980-05-12"
        }],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={"birth_dates": ["1980-05-12"]},
        expected_smart_filter_signals=["name"],
        expected_should_process=True,
        expected_trace_roles=["surname", "given", "patronymic"],
        notes="Person with birth date - signals should extract and normalize date"
    ),

    IntegrationTestCase(
        name="person_with_inn",
        input_text="Платеж Иванову П.С., ІПН 1234567890",
        expected_language="uk",  # Mixed but Ukrainian context
        expected_language_confidence_min=0.6,
        expected_normalized="П. С. Іванов",
        expected_persons=[{
            "core": ["П.", "С.", "Іванов"],
            "full_name": "П. С. Іванов",
            "dob": None
        }],
        expected_organizations=[],
        expected_numbers={"inn": ["1234567890"]},
        expected_dates={},
        expected_smart_filter_signals=["name", "number"],
        expected_should_process=True,
        expected_trace_roles=["initial", "initial", "surname"],
        notes="Person with INN - signals should extract identifier"
    ),

    IntegrationTestCase(
        name="mixed_script_names",
        input_text="Payment for John Smith and Олена Петренко",
        expected_language="en",  # English context dominates
        expected_language_confidence_min=0.6,
        expected_normalized="John Smith Олена Петренко",
        expected_persons=[
            {"core": ["John", "Smith"], "full_name": "John Smith", "dob": None},
            {"core": ["Олена", "Петренко"], "full_name": "Олена Петренко", "dob": None}
        ],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["name"],
        expected_should_process=True,
        expected_trace_roles=["given", "surname", "given", "surname"],
        notes="Mixed script - ASCII names in Cyrillic context should not be morphed"
    ),

    IntegrationTestCase(
        name="noise_context_should_filter",
        input_text="Оплата за послуги, рахунок 12345, дякуємо",
        expected_language="uk",
        expected_language_confidence_min=0.8,
        expected_normalized="",  # No names or organizations
        expected_persons=[],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=[],
        expected_should_process=False,  # Should be filtered out
        expected_trace_roles=[],
        notes="Noise context - SmartFilter should suggest skipping"
    ),

    IntegrationTestCase(
        name="quoted_company_with_person",
        input_text="ООО 'Тест Системс' перевод средств Ивану Петрову",
        expected_language="ru",
        expected_language_confidence_min=0.8,
        expected_normalized="Иван Петров",
        expected_persons=[{
            "core": ["Иван", "Петров"],
            "full_name": "Иван Петров",
            "dob": None
        }],
        expected_organizations=[{
            "legal_form": "ООО",
            "core": "Тест Системс",
            "full_name": "ООО Тест Системс"
        }],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["company", "name"],
        expected_should_process=True,
        expected_trace_roles=["given", "surname"],
        notes="Quoted company name with person transfer"
    ),

    IntegrationTestCase(
        name="hyphenated_surname",
        input_text="Платеж для Марії Коцюбинської-Гончаренко",
        expected_language="uk",
        expected_language_confidence_min=0.8,
        expected_normalized="Марія Коцюбинська-Гончаренко",
        expected_persons=[{
            "core": ["Марія", "Коцюбинська-Гончаренко"],
            "full_name": "Марія Коцюбинська-Гончаренко",
            "dob": None
        }],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=["name"],
        expected_should_process=True,
        expected_trace_roles=["given", "surname"],
        notes="Hyphenated surname - preserve_names should keep hyphens"
    ),

    IntegrationTestCase(
        name="overfit_canary",
        input_text="клавиатура, рахунок, дисплей, table",
        expected_language="uk",
        expected_language_confidence_min=0.6,
        expected_normalized="",
        expected_persons=[],
        expected_organizations=[],
        expected_numbers={},
        expected_dates={},
        expected_smart_filter_signals=[],
        expected_should_process=False,
        expected_trace_roles=[],
        notes="Overfit canary - random words should not become names"
    ),

    IntegrationTestCase(
        name="full_pipeline_stress_test",
        input_text="ТОВ 'Агросвіт', ФОП Іваненко Іван Іванович, ІПН 1234567890, дата народження 05.07.1975",
        expected_language="uk",
        expected_language_confidence_min=0.9,
        expected_normalized="Іваненко Іван Іванович",
        expected_persons=[{
            "core": ["Іваненко", "Іван", "Іванович"],
            "full_name": "Іваненко Іван Іванович",
            "dob": "1975-07-05"
        }],
        expected_organizations=[
            {"legal_form": "ТОВ", "core": "Агросвіт", "full_name": "ТОВ Агросвіт"},
            {"legal_form": "ФОП", "core": "Іваненко", "full_name": "ФОП Іваненко"}
        ],
        expected_numbers={"inn": ["1234567890"]},
        expected_dates={"birth_dates": ["1975-07-05"]},
        expected_smart_filter_signals=["company", "name", "number"],
        expected_should_process=True,
        expected_trace_roles=["surname", "given", "patronymic"],
        notes="Full pipeline stress test - all signals types present"
    )
]


class TestPipelineEnd2End:
    """End-to-end integration tests for the unified AI service pipeline"""

    orchestrator = None

    @classmethod
    def setup_class(cls):
        """Setup orchestrator for all tests"""
        logger.info("Setting up orchestrator for integration tests...")
        cls.orchestrator = asyncio.run(OrchestratorFactory.create_testing_orchestrator(minimal=False))
        logger.info("Orchestrator initialized successfully")

    @pytest.mark.parametrize("test_case", INTEGRATION_TEST_CASES, ids=lambda tc: tc.name)
    @pytest.mark.asyncio
    async def test_pipeline_integration(self, test_case: IntegrationTestCase):
        """Test complete pipeline integration with real payment scenarios"""

        logger.info(f"Testing: {test_case.name} - {test_case.notes}")
        logger.info(f"Input: {test_case.input_text}")

        # Process through unified pipeline
        result = await self.orchestrator.process(
            text=test_case.input_text,
            # Test with production-like settings per CLAUDE.md
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            generate_variants=False,  # Focus on core functionality
            generate_embeddings=False
        )

        # Assert processing succeeded
        if test_case.expected_should_process:
            assert result.success, f"Processing should succeed but failed: {result.errors}"

        # 1. Language Detection Layer Tests
        assert result.language == test_case.expected_language, \
            f"Expected language {test_case.expected_language}, got {result.language}"

        assert result.language_confidence >= test_case.expected_language_confidence_min, \
            f"Language confidence {result.language_confidence} below minimum {test_case.expected_language_confidence_min}"

        # 2. Smart Filter Layer Tests
        smart_filter_meta = result.__dict__.get('metadata', {}).get('smart_filter', {})
        if smart_filter_meta:
            detected_signals = smart_filter_meta.get('detected_signals', [])
            for expected_signal in test_case.expected_smart_filter_signals:
                assert expected_signal in detected_signals, \
                    f"Expected smart filter signal '{expected_signal}' not found in {detected_signals}"

        # 3. Normalization Layer Tests (THE CORE)
        assert result.normalized_text == test_case.expected_normalized, \
            f"Expected normalized '{test_case.expected_normalized}', got '{result.normalized_text}'"

        # 4. TokenTrace Validation (per CLAUDE.md requirement)
        if test_case.expected_trace_roles:
            trace_roles = [trace.role for trace in result.trace if hasattr(trace, 'role')]
            assert trace_roles == test_case.expected_trace_roles, \
                f"Expected trace roles {test_case.expected_trace_roles}, got {trace_roles}"

        # 5. Signals Layer Tests - Persons
        assert len(result.signals.persons) == len(test_case.expected_persons), \
            f"Expected {len(test_case.expected_persons)} persons, got {len(result.signals.persons)}"

        for i, expected_person in enumerate(test_case.expected_persons):
            if i < len(result.signals.persons):
                actual_person = result.signals.persons[i]
                assert actual_person.core == expected_person["core"], \
                    f"Person {i} core mismatch: expected {expected_person['core']}, got {actual_person.core}"

                if expected_person["dob"]:
                    assert actual_person.dob == expected_person["dob"], \
                        f"Person {i} DOB mismatch: expected {expected_person['dob']}, got {actual_person.dob}"

        # 6. Signals Layer Tests - Organizations
        assert len(result.signals.organizations) == len(test_case.expected_organizations), \
            f"Expected {len(test_case.expected_organizations)} orgs, got {len(result.signals.organizations)}"

        for i, expected_org in enumerate(test_case.expected_organizations):
            if i < len(result.signals.organizations):
                actual_org = result.signals.organizations[i]
                assert actual_org.legal_form == expected_org["legal_form"], \
                    f"Org {i} legal form mismatch: expected {expected_org['legal_form']}, got {actual_org.legal_form}"
                assert actual_org.core == expected_org["core"], \
                    f"Org {i} core mismatch: expected {expected_org['core']}, got {actual_org.core}"

        # 7. Performance Requirements (per CLAUDE.md)
        assert result.processing_time < 0.5, \
            f"Processing too slow: {result.processing_time}s (should be < 0.5s for integration tests)"

        logger.info(f"[OK] {test_case.name} passed - processing time: {result.processing_time:.3f}s")

    @pytest.mark.asyncio
    async def test_normalization_flags_behavior(self):
        """Test that normalization flags actually change behavior (CLAUDE.md requirement)"""

        test_text = "Іван Петрович Сидоренко и ООО компания"

        # Test different flag combinations
        flag_combinations = [
            {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
            {"remove_stop_words": False, "preserve_names": True, "enable_advanced_features": True},
            {"remove_stop_words": True, "preserve_names": False, "enable_advanced_features": True},
            {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": False},
        ]

        results = []
        for flags in flag_combinations:
            result = await self.orchestrator.process(text=test_text, **flags)
            results.append((flags, result.normalized_text, len(result.tokens)))

        # Verify flags produce different results
        normalized_results = [r[1] for r in results]
        unique_results = set(normalized_results)

        assert len(unique_results) > 1, \
            f"Flags should produce different results but all were identical: {normalized_results}"

        logger.info(f"[OK] Flags behavior test passed - {len(unique_results)} unique results from {len(flag_combinations)} flag combinations")

    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """Test performance requirements from CLAUDE.md"""

        short_texts = [
            "Іван Петров",
            "ООО Тест",
            "Payment for John",
            "ТОВ Агросвіт"
        ]

        for text in short_texts:
            result = await self.orchestrator.process(text=text)

            # CLAUDE.md requirement: p95 normalization ≤ 10 ms for short strings
            assert result.processing_time <= 0.01, \
                f"Short text '{text}' processing too slow: {result.processing_time:.3f}s (should be ≤ 0.01s)"

        logger.info("[OK] Performance requirements test passed")


# Standalone test runner
if __name__ == "__main__":
    async def run_tests():
        """Run integration tests standalone"""
        test_instance = TestPipelineEnd2End()
        test_instance.setup_class()

        print("[INIT] Running End-to-End Integration Tests")
        print("=" * 60)

        passed = 0
        failed = 0

        for test_case in INTEGRATION_TEST_CASES:
            try:
                await test_instance.test_pipeline_integration(test_case)
                passed += 1
                print(f"[OK] {test_case.name}")
            except Exception as e:
                failed += 1
                print(f"[ERROR] {test_case.name}: {e}")

        # Run additional tests
        try:
            await test_instance.test_normalization_flags_behavior()
            await test_instance.test_performance_requirements()
            passed += 2
            print("[OK] Flags behavior test")
            print("[OK] Performance requirements test")
        except Exception as e:
            failed += 2
            print(f"[ERROR] Additional tests failed: {e}")

        print("\n" + "=" * 60)
        print(f"Results: {passed} passed, {failed} failed")
        return failed == 0

    if asyncio.run(run_tests()):
        print("🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("💥 Some integration tests failed!")
        sys.exit(1)