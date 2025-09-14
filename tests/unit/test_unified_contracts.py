#!/usr/bin/env python3
"""
Unit tests for unified contracts and interfaces.

Tests the new contract system that implements the CLAUDE.md specification.
These tests replace older contract tests and ensure compatibility.
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any
from dataclasses import asdict

# Add project to path
project_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from ai_service.contracts import (
    TokenTrace,
    NormalizationResult,
    SignalsPerson,
    SignalsOrganization,
    SignalsExtras,
    SignalsResult,
    SmartFilterResult,
    ProcessingContext,
    UnifiedProcessingResult,
)


class TestTokenTrace:
    """Test TokenTrace contract"""

    def test_token_trace_creation(self):
        """Test TokenTrace creation with required fields"""
        trace = TokenTrace(
            token="Іван",
            role="given",
            rule="name_dictionary",
            output="Іван"
        )

        assert trace.token == "Іван"
        assert trace.role == "given"
        assert trace.rule == "name_dictionary"
        assert trace.output == "Іван"
        assert trace.morph_lang is None
        assert trace.fallback is False

    def test_token_trace_with_morphology(self):
        """Test TokenTrace with morphology information"""
        trace = TokenTrace(
            token="іваном",
            role="given",
            rule="morphology_normalization",
            morph_lang="uk",
            normal_form="іван",
            output="Іван",
            notes="Instrumental case normalized to nominative"
        )

        assert trace.morph_lang == "uk"
        assert trace.normal_form == "іван"
        assert trace.notes == "Instrumental case normalized to nominative"

    def test_token_trace_serialization(self):
        """Test TokenTrace can be serialized/deserialized"""
        trace = TokenTrace(
            token="Smith",
            role="surname",
            rule="positional_default",
            output="Smith",
            fallback=True,
            notes="ASCII name in Cyrillic context"
        )

        # Test model_dump for Pydantic compatibility
        data = trace.model_dump()
        assert isinstance(data, dict)
        assert data["token"] == "Smith"
        assert data["fallback"] is True


class TestNormalizationResult:
    """Test NormalizationResult contract"""

    def test_normalization_result_basic(self):
        """Test basic NormalizationResult creation"""
        result = NormalizationResult(
            normalized="Іван Петров",
            tokens=["Іван", "Петров"],
            trace=[
                TokenTrace(token="Іван", role="given", rule="dict", output="Іван"),
                TokenTrace(token="Петров", role="surname", rule="dict", output="Петров")
            ]
        )

        assert result.normalized == "Іван Петров"
        assert result.tokens == ["Іван", "Петров"]
        assert len(result.trace) == 2
        assert result.success is True  # Default value

    def test_normalization_result_with_metadata(self):
        """Test NormalizationResult with full metadata"""
        result = NormalizationResult(
            normalized="П. І. Коваленко",
            tokens=["П.", "І.", "Коваленко"],
            trace=[],
            language="uk",
            confidence=0.95,
            original_length=25,
            normalized_length=15,
            token_count=3,
            processing_time=0.05,
            success=True,
            persons_core=[["П.", "І.", "Коваленко"]],
            organizations_core=["GAZPROM"]
        )

        assert result.language == "uk"
        assert result.confidence == 0.95
        assert result.persons_core == [["П.", "І.", "Коваленко"]]
        assert result.organizations_core == ["GAZPROM"]

    def test_normalization_result_serialization(self):
        """Test NormalizationResult serialization"""
        result = NormalizationResult(
            normalized="Test",
            tokens=["Test"],
            trace=[]
        )

        # Test to_dict method
        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["normalized"] == "Test"

        # Test to_json method
        json_str = result.to_json()
        assert isinstance(json_str, str)
        assert "Test" in json_str


class TestSignalsContracts:
    """Test signals-related contracts"""

    def test_signals_person(self):
        """Test SignalsPerson dataclass"""
        person = SignalsPerson(
            core=["Іван", "Петров"],
            full_name="Іван Петров",
            dob="1985-06-15",
            ids=[{"type": "inn", "value": "123456789012", "valid": True}],
            confidence=0.85,
            evidence=["name_dictionary_match", "patronymic_pattern"]
        )

        assert person.core == ["Іван", "Петров"]
        assert person.dob == "1985-06-15"
        assert len(person.ids) == 1
        assert person.ids[0]["type"] == "inn"
        assert person.confidence == 0.85
        assert "name_dictionary_match" in person.evidence

    def test_signals_organization(self):
        """Test SignalsOrganization dataclass"""
        org = SignalsOrganization(
            core="ГАЗПРОМ",
            legal_form="ООО",
            full_name="ООО ГАЗПРОМ",
            ids=[{"type": "ogrn", "value": "1234567890123", "valid": True}],
            confidence=0.92,
            evidence=["legal_form_pattern", "quoted_core", "banking_context"]
        )

        assert org.core == "ГАЗПРОМ"
        assert org.legal_form == "ООО"
        assert org.full_name == "ООО ГАЗПРОМ"
        assert org.confidence == 0.92
        assert "quoted_core" in org.evidence

    def test_signals_result(self):
        """Test complete SignalsResult"""
        result = SignalsResult(
            persons=[
                SignalsPerson(
                    core=["Іван", "Іванович"],
                    full_name="Іван Іванович",
                    confidence=0.8
                )
            ],
            organizations=[
                SignalsOrganization(
                    core="Тест",
                    legal_form="ТОВ",
                    full_name="ТОВ Тест",
                    confidence=0.9
                )
            ],
            extras=SignalsExtras(
                dates=[{"value": "1990-01-01", "precision": "day"}],
                amounts=[{"value": 1000.0, "currency": "UAH"}]
            ),
            confidence=0.85
        )

        assert len(result.persons) == 1
        assert len(result.organizations) == 1
        assert result.confidence == 0.85
        assert len(result.extras.dates) == 1


class TestSmartFilterResult:
    """Test SmartFilterResult contract"""

    def test_smart_filter_result_basic(self):
        """Test basic SmartFilterResult"""
        result = SmartFilterResult(
            should_process=True,
            confidence=0.85,
            classification="recommend",
            detected_signals=["name", "company"],
            details={
                "name_signals": {"has_capitals": True, "has_initials": False},
                "company_signals": {"has_legal_forms": True, "has_quoted_cores": True}
            },
            processing_time=0.003
        )

        assert result.should_process is True
        assert result.confidence == 0.85
        assert result.classification == "recommend"
        assert "name" in result.detected_signals
        assert result.details["name_signals"]["has_capitals"] is True

    def test_smart_filter_classifications(self):
        """Test all SmartFilter classification levels per CLAUDE.md"""
        classifications = ["must_process", "recommend", "maybe", "skip"]

        for classification in classifications:
            result = SmartFilterResult(
                should_process=classification != "skip",
                confidence=0.5,
                classification=classification,
                detected_signals=[]
            )
            assert result.classification == classification


class TestUnifiedProcessingResult:
    """Test UnifiedProcessingResult contract"""

    def test_unified_result_complete(self):
        """Test complete UnifiedProcessingResult"""
        result = UnifiedProcessingResult(
            original_text="ТОВ Іван Петров",
            language="uk",
            language_confidence=0.9,
            normalized_text="Іван Петров",
            tokens=["Іван", "Петров"],
            trace=[
                TokenTrace(token="Іван", role="given", rule="dict", output="Іван")
            ],
            signals=SignalsResult(
                persons=[SignalsPerson(core=["Іван", "Петров"], full_name="Іван Петров")],
                organizations=[SignalsOrganization(core="Test", legal_form="ТОВ", full_name="ТОВ Test")],
                confidence=0.8
            ),
            variants=["Ivan Petrov", "I. Petrov"],
            embeddings=[0.1, 0.2, 0.3],
            processing_time=0.05,
            success=True,
            errors=[]
        )

        assert result.original_text == "ТОВ Іван Петров"
        assert result.normalized_text == "Іван Петров"
        assert len(result.signals.persons) == 1
        assert len(result.signals.organizations) == 1
        assert result.variants == ["Ivan Petrov", "I. Petrov"]
        assert result.embeddings == [0.1, 0.2, 0.3]
        assert result.success is True

    def test_unified_result_serialization(self):
        """Test UnifiedProcessingResult to_dict method"""
        result = UnifiedProcessingResult(
            original_text="Test",
            language="en",
            language_confidence=0.8,
            normalized_text="Test",
            tokens=["Test"],
            trace=[],
            signals=SignalsResult()
        )

        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["original_text"] == "Test"
        assert data["language"] == "en"
        assert "signals" in data
        assert isinstance(data["signals"], dict)
        assert "persons" in data["signals"]
        assert "organizations" in data["signals"]

    def test_unified_result_backward_compatibility(self):
        """Test backward compatibility with legacy response format"""
        result = UnifiedProcessingResult(
            original_text="Test",
            language="en",
            language_confidence=0.8,
            normalized_text="Test",
            tokens=["Test"],
            trace=[],
            signals=SignalsResult()
        )

        data = result.to_dict()

        # Check that legacy fields are present for backward compatibility
        assert "original_text" in data
        assert "normalized_text" in data
        assert "language" in data
        assert "language_confidence" in data
        assert "processing_time" in data
        assert "success" in data
        assert "errors" in data

        # Check signals structure matches expected format
        signals = data["signals"]
        assert "persons" in signals
        assert "organizations" in signals
        assert "numbers" in signals  # Legacy compatibility
        assert "dates" in signals
        assert "confidence" in signals


class TestProcessingContext:
    """Test ProcessingContext"""

    def test_processing_context_basic(self):
        """Test basic ProcessingContext creation"""
        context = ProcessingContext(
            original_text="Test input",
            sanitized_text="Test input",
            language="en",
            language_confidence=0.9,
            should_process=True,
            processing_flags={"remove_stop_words": True},
            metadata={"test": True}
        )

        assert context.original_text == "Test input"
        assert context.language == "en"
        assert context.should_process is True
        assert context.processing_flags["remove_stop_words"] is True
        assert context.metadata["test"] is True


# Integration test for contract compatibility
class TestContractCompatibility:
    """Test contract compatibility and integration"""

    def test_contract_chain_compatibility(self):
        """Test that contracts work together in a processing chain"""

        # Create a processing result that would flow through the system
        trace = [
            TokenTrace(token="Іван", role="given", rule="dictionary", output="Іван"),
            TokenTrace(token="Петров", role="surname", rule="dictionary", output="Петров")
        ]

        norm_result = NormalizationResult(
            normalized="Іван Петров",
            tokens=["Іван", "Петров"],
            trace=trace,
            persons_core=[["Іван", "Петров"]]
        )

        signals_result = SignalsResult(
            persons=[
                SignalsPerson(
                    core=["Іван", "Петров"],
                    full_name="Іван Петров",
                    confidence=0.85
                )
            ],
            confidence=0.85
        )

        final_result = UnifiedProcessingResult(
            original_text="Payment to Іван Петров",
            language="uk",
            language_confidence=0.9,
            normalized_text=norm_result.normalized,
            tokens=norm_result.tokens,
            trace=norm_result.trace,
            signals=signals_result
        )

        # Verify the chain works
        assert final_result.normalized_text == "Іван Петров"
        assert len(final_result.signals.persons) == 1
        assert final_result.signals.persons[0].core == ["Іван", "Петров"]
        assert final_result.trace[0].token == "Іван"

        # Verify serialization works end-to-end
        data = final_result.to_dict()
        assert data["normalized_text"] == "Іван Петров"
        assert len(data["signals"]["persons"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])