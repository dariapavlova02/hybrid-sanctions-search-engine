#!/usr/bin/env python3
"""
Updated tests for Normalization Layer (Layer 5) - THE CORE.

Tests normalization service with new unified contracts and CLAUDE.md compliance.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.contracts import NormalizationResult, TokenTrace


class TestNormalizationContracts:
    """Test normalization service with new unified contracts"""

    @pytest.fixture
    async def service(self):
        """Create normalization service instance"""
        service = NormalizationService()
        return service

    @pytest.mark.asyncio
    async def test_normalization_result_structure(self, service):
        """Test that NormalizationResult has all required fields per new contracts"""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"

        result = await service.normalize_async(
            text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        # Assert result is the new NormalizationResult
        assert isinstance(result, NormalizationResult)

        # Core fields
        assert hasattr(result, 'normalized')
        assert hasattr(result, 'tokens')
        assert hasattr(result, 'trace')
        assert hasattr(result, 'errors')

        # Metadata fields
        assert hasattr(result, 'language')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'original_length')
        assert hasattr(result, 'normalized_length')
        assert hasattr(result, 'token_count')
        assert hasattr(result, 'processing_time')
        assert hasattr(result, 'success')

        # NEW: Core separation fields per CLAUDE.md
        assert hasattr(result, 'persons_core')
        assert hasattr(result, 'organizations_core')

        # Verify types
        assert isinstance(result.normalized, str)
        assert isinstance(result.tokens, list)
        assert isinstance(result.trace, list)
        assert isinstance(result.errors, list)

        # New core separation
        if result.persons_core:
            assert isinstance(result.persons_core, list)
        if result.organizations_core:
            assert isinstance(result.organizations_core, list)

    @pytest.mark.asyncio
    async def test_token_trace_completeness(self, service):
        """Test that every token has proper TokenTrace per CLAUDE.md requirement"""
        text = "П.І. Коваленко"

        result = await service.normalize_async(
            text,
            language="uk",
            enable_advanced_features=True
        )

        # Every normalized token must have trace
        assert len(result.trace) == len(result.tokens)

        for i, (token, trace) in enumerate(zip(result.tokens, result.trace)):
            assert isinstance(trace, TokenTrace)

            # Required TokenTrace fields per contract
            assert hasattr(trace, 'token')
            assert hasattr(trace, 'role')
            assert hasattr(trace, 'rule')
            assert hasattr(trace, 'output')

            # Optional fields
            assert hasattr(trace, 'morph_lang')
            assert hasattr(trace, 'normal_form')
            assert hasattr(trace, 'fallback')
            assert hasattr(trace, 'notes')

            # Verify role is from valid set per CLAUDE.md
            valid_roles = {'initial', 'patronymic', 'given', 'surname', 'unknown'}
            assert trace.role in valid_roles, f"Invalid role: {trace.role}"

            # Output should match token in normalized result
            assert trace.output == token

    @pytest.mark.asyncio
    async def test_organizations_core_separation(self, service):
        """Test that organizations are properly separated per CLAUDE.md"""
        text = 'ТОВ "ГАЗПРОМ" переказ коштів Іван Петров'

        result = await service.normalize_async(text, language="uk")

        # Normalized should contain ONLY person names per CLAUDE.md
        assert "Іван Петров" in result.normalized
        assert "ТОВ" not in result.normalized  # Legal form not in normalized
        assert "ГАЗПРОМ" not in result.normalized  # Org core not in normalized

        # Organizations core should contain company names without legal forms
        if result.organizations_core:
            assert "ГАЗПROM" in result.organizations_core or "ГАЗПРОМ" in result.organizations_core
            assert "ТОВ" not in result.organizations_core  # Legal form handled by Signals

    @pytest.mark.asyncio
    async def test_persons_core_structure(self, service):
        """Test persons_core structure per new contracts"""
        text = "Петро Іванович Коваленко"

        result = await service.normalize_async(text, language="uk")

        if result.persons_core:
            # Should be list of lists [[given, surname, patronymic], ...]
            assert isinstance(result.persons_core, list)
            assert len(result.persons_core) > 0

            person_core = result.persons_core[0]
            assert isinstance(person_core, list)

            # Should contain name components (normalized forms)
            expected_components = ["Петро", "Іванович", "Коваленко"]
            for component in expected_components:
                assert component in person_core

    @pytest.mark.asyncio
    async def test_flag_behavior_real_impact(self, service):
        """Test that flags have real behavioral impact per CLAUDE.md requirement"""
        text = "А.С.Пушкін"  # Text that shows clear preserve_names differences

        # Test different flag combinations that produce different results
        results = []
        flag_combinations = [
            {"preserve_names": True, "enable_advanced_features": True},
            {"preserve_names": False, "enable_advanced_features": True},
            {"preserve_names": True, "enable_advanced_features": False},
            {"preserve_names": False, "enable_advanced_features": False},
        ]

        for flags in flag_combinations:
            result = await service.normalize_async(text, language="uk", **flags)
            results.append((flags, result.normalized, len(result.tokens)))

        # Verify flags produce different results
        normalized_results = [r[1] for r in results]
        unique_results = set(normalized_results)

        assert len(unique_results) > 1, \
            f"Flags should produce different results but all were identical: {normalized_results}"

    @pytest.mark.asyncio
    async def test_org_acronyms_always_unknown(self, service):
        """Test that ORG_ACRONYMS are always tagged as unknown per CLAUDE.md"""
        # Test various legal forms
        legal_forms = ["ООО", "ТОВ", "LLC", "Ltd", "Inc", "Corp"]

        for legal_form in legal_forms:
            text = f"{legal_form} Іван Петров"
            result = await service.normalize_async(text, language="uk")

            # Legal form should not be in normalized (should be unknown/filtered)
            assert legal_form not in result.normalized

            # Should be in trace but marked as unknown
            legal_form_traces = [t for t in result.trace if t.token.upper() == legal_form.upper()]
            if legal_form_traces:
                assert legal_form_traces[0].role == "unknown"

    @pytest.mark.asyncio
    async def test_ascii_no_morph_in_cyrillic(self, service):
        """Test ASCII names in Cyrillic context don't get morphed per CLAUDE.md"""
        text = "John Smith працює в компанії"

        result = await service.normalize_async(
            text,
            language="uk",
            enable_advanced_features=True
        )

        # John Smith should be preserved as-is (no morphological changes)
        assert "John Smith" in result.normalized

        # Trace should show no morphology applied to ASCII tokens
        john_trace = [t for t in result.trace if t.token == "John"]
        smith_trace = [t for t in result.trace if t.token == "Smith"]

        if john_trace:
            assert john_trace[0].morph_lang is None  # No morphology
        if smith_trace:
            assert smith_trace[0].morph_lang is None  # No morphology

    @pytest.mark.asyncio
    async def test_womens_surnames_preserved(self, service):
        """Test that women's surnames are preserved per CLAUDE.md"""
        text = "Марія Коваленко-Петренко"

        result = await service.normalize_async(
            text,
            language="uk",
            enable_advanced_features=True
        )

        # Should preserve hyphenated feminine surname
        assert "Коваленко-Петренко" in result.normalized

        # Should not "masculinize" to "Коваленко-Петренків" or similar
        assert "Коваленків" not in result.normalized

    @pytest.mark.asyncio
    async def test_serialization_compatibility(self, service):
        """Test that result can be serialized per contract requirements"""
        text = "Тест нормализации"

        result = await service.normalize_async(text, language="uk")

        # Test to_dict method
        data = result.to_dict()
        assert isinstance(data, dict)
        assert "normalized" in data
        assert "tokens" in data
        assert "trace" in data

        # Test to_json method
        json_str = result.to_json()
        assert isinstance(json_str, str)
        assert "normalized" in json_str

    @pytest.mark.asyncio
    async def test_performance_requirements(self, service):
        """Test performance requirements per CLAUDE.md"""
        short_texts = [
            "Іван Петров",
            "John Smith",
            "А.Б. Коваленко",
            "ТОВ Тест"
        ]

        for text in short_texts:
            result = await service.normalize_async(text, language="uk")

            # CLAUDE.md requirement: short strings should be ≤ 10ms
            assert result.processing_time <= 0.01, \
                f"Processing too slow for '{text}': {result.processing_time:.3f}s"

    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling and success flags"""
        # Test with problematic input
        problematic_texts = [
            "",  # Empty
            "   ",  # Only spaces
            "123456",  # Only numbers
            "!!!@@@",  # Only symbols
        ]

        for text in problematic_texts:
            result = await service.normalize_async(text, language="uk")

            # Should handle gracefully
            assert isinstance(result, NormalizationResult)
            assert hasattr(result, 'success')
            assert hasattr(result, 'errors')

            if not result.success:
                assert len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])