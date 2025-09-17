"""
Smoke tests for critical normalization cases.

These tests verify that the most important normalization scenarios work correctly
with various feature flags enabled. They are designed to be fast and catch
regressions in core functionality.
"""

import pytest
import time
from typing import Dict, Any, List
from unittest.mock import patch

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.utils.feature_flags import FeatureFlags
from src.ai_service.contracts.base_contracts import NormalizationResult


class TestNormalizationSmoke:
    """Smoke tests for critical normalization functionality."""

    @pytest.fixture
    def normalization_service(self):
        """Create normalization service instance."""
        return NormalizationService()

    @pytest.fixture
    def base_flags(self):
        """Base feature flags for testing."""
        return FeatureFlags(
            use_factory_normalizer=True,
            fix_initials_double_dot=False,
            preserve_hyphenated_case=False,
            strict_stopwords=False,
            enable_ac_tier0=False,
            enable_vector_fallback=False,
            enforce_nominative=True,
            preserve_feminine_surnames=True,
        )

    async def _measure_performance(self, func, *args, **kwargs) -> tuple[Any, float]:
        """Measure execution time of an async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        return result, execution_time

    @pytest.mark.parametrize("language", ["ru", "uk", "en"])
    @pytest.mark.asyncio
    async def test_initials_double_dot_collapse(self, normalization_service, base_flags, language):
        """Test A) Инициалы: И.. И. Петров → И. И. Петров."""
        # Enable the feature flag
        flags = FeatureFlags(**base_flags.__dict__)
        flags.fix_initials_double_dot = True
        
        test_cases = {
            "ru": "И.. И. Петров",
            "uk": "І.. І. Петренко", 
            "en": "J.. J. Smith"
        }
        
        input_text = test_cases[language]
        
        # Measure performance
        result, execution_time = await self._measure_performance(
            normalization_service.normalize_async,
            input_text,
            language=language,
            feature_flags=flags
        )
        
        # Verify performance (p95 < 20ms)
        assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
        
        # Verify normalization
        assert result.success, f"Normalization failed: {result.errors}"
        assert "И. И. Петров" in result.normalized or "І. І. Петренко" in result.normalized or "J. J. Smith" in result.normalized
        
        # Verify trace contains collapse_double_dots
        trace_rules = [entry.get("rule") for entry in result.trace if isinstance(entry, dict)]
        assert any("collapse_double_dots" in str(rule) for rule in trace_rules), "Missing collapse_double_dots rule in trace"

    @pytest.mark.parametrize("language", ["ru", "uk", "en"])
    @pytest.mark.asyncio
    async def test_hyphenated_names_preservation(self, normalization_service, base_flags, language):
        """Test B) Дефисы: Петрова-сидорова Олена → Олена Петрова-Сидорова."""
        # Enable the feature flag
        flags = FeatureFlags(**base_flags.__dict__)
        flags.preserve_hyphenated_case = True
        
        test_cases = {
            "ru": "Петрова-сидорова Олена",
            "uk": "Петренко-сидоренко Олена",
            "en": "O'Neil-Smith John"
        }
        
        input_text = test_cases[language]
        
        # Measure performance
        result, execution_time = await self._measure_performance(
            normalization_service.normalize_async,
            input_text,
            language=language,
            feature_flags=flags
        )
        
        # Verify performance (p95 < 20ms)
        assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
        
        # Verify normalization
        assert result.success, f"Normalization failed: {result.errors}"
        
        # Check that hyphenated parts are properly capitalized
        normalized = result.normalized
        if language in ["ru", "uk"]:
            # Should contain properly capitalized hyphenated surname
            assert any(part.isupper() for part in normalized.split("-") if "-" in normalized), "Hyphenated parts not properly capitalized"
        else:  # en
            # Should preserve hyphenated name structure
            assert "O'Neil-Smith" in normalized or "O'Neill-Smith" in normalized, "Hyphenated name not preserved"

    @pytest.mark.parametrize("language", ["ru", "uk", "en"])
    @pytest.mark.asyncio
    async def test_organization_context_filtering(self, normalization_service, base_flags, language):
        """Test C) Орг-контекст: Оплата ТОВ «ПРИВАТБАНК» Ивану Петрову → Иван Петров."""
        # Enable strict stopwords filtering
        flags = FeatureFlags(**base_flags.__dict__)
        flags.strict_stopwords = True
        
        test_cases = {
            "ru": "Оплата ТОВ «ПРИВАТБАНК» Ивану Петрову",
            "uk": "Оплата ТОВ «ПРИВАТБАНК» Івану Петренку",
            "en": "Payment to LLC «PRIVATBANK» John Smith"
        }
        
        input_text = test_cases[language]
        
        # Measure performance
        result, execution_time = await self._measure_performance(
            normalization_service.normalize_async,
            input_text,
            language=language,
            feature_flags=flags
        )
        
        # Verify performance (p95 < 20ms)
        assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
        
        # Verify normalization
        assert result.success, f"Normalization failed: {result.errors}"
        
        # Check that organization is filtered out
        normalized = result.normalized.lower()
        assert "тов" not in normalized, "Organization acronym not filtered"
        assert "оплата" not in normalized, "Payment word not filtered"
        
        # Check that person name is preserved
        if language == "ru":
            assert "иван петров" in normalized, "Person name not preserved"
        elif language == "uk":
            assert "іван петренко" in normalized, "Person name not preserved"
        else:  # en
            assert "john smith" in normalized, "Person name not preserved"

    @pytest.mark.parametrize("language", ["ru", "uk", "en"])
    @pytest.mark.asyncio
    async def test_apostrophes_preservation(self, normalization_service, base_flags, language):
        """Test D) Апострофы: O'Neil-Smith John → John O'Neil-Smith."""
        # Enable hyphenated case preservation
        flags = FeatureFlags(**base_flags.__dict__)
        flags.preserve_hyphenated_case = True
        
        test_cases = {
            "ru": "O'Брайен-Смит Джон",  # Mixed script case
            "uk": "O'Брайен-Сміт Джон",   # Mixed script case
            "en": "O'Neil-Smith John"
        }
        
        input_text = test_cases[language]
        
        # Measure performance
        result, execution_time = await self._measure_performance(
            normalization_service.normalize_async,
            input_text,
            language=language,
            feature_flags=flags
        )
        
        # Verify performance (p95 < 20ms)
        assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
        
        # Verify normalization
        assert result.success, f"Normalization failed: {result.errors}"
        
        # Check that apostrophe is preserved
        normalized = result.normalized
        assert "'" in normalized, "Apostrophe not preserved"
        
        # Check that name structure is maintained
        if language == "en":
            assert "O'Neil-Smith" in normalized, "Hyphenated name with apostrophe not preserved"

    @pytest.mark.parametrize("language", ["ru", "uk", "en"])
    @pytest.mark.asyncio
    async def test_multi_person_extraction(self, normalization_service, base_flags, language):
        """Test E) Мульти-персоны: Иван Петров; Олена Ковальська → both persons extracted."""
        # Use base flags without strict filtering to allow multiple persons
        flags = FeatureFlags(**base_flags.__dict__)
        
        test_cases = {
            "ru": "Иван Петров; Олена Ковальська",
            "uk": "Іван Петренко; Олена Коваленко",
            "en": "John Smith; Jane Doe"
        }
        
        input_text = test_cases[language]
        
        # Measure performance
        result, execution_time = await self._measure_performance(
            normalization_service.normalize_async,
            input_text,
            language=language,
            feature_flags=flags
        )
        
        # Verify performance (p95 < 20ms)
        assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
        
        # Verify normalization
        assert result.success, f"Normalization failed: {result.errors}"
        
        # Check that both persons are extracted
        normalized = result.normalized.lower()
        if language == "ru":
            assert "иван петров" in normalized, "First person not extracted"
            assert "олена ковальська" in normalized, "Second person not extracted"
        elif language == "uk":
            assert "іван петренко" in normalized, "First person not extracted"
            assert "олена коваленко" in normalized, "Second person not extracted"
        else:  # en
            assert "john smith" in normalized, "First person not extracted"
            assert "jane doe" in normalized, "Second person not extracted"
        
        # Check that stop words are not in normalized result
        stop_words = ["оплата", "платеж", "beneficiary", "sender", "payment"]
        for stop_word in stop_words:
            assert stop_word not in normalized, f"Stop word '{stop_word}' found in normalized result"

    @pytest.mark.asyncio
    async def test_stop_words_filtering(self, normalization_service, base_flags):
        """Test that service/payment words are filtered from normalized person names."""
        # Enable strict stopwords filtering
        flags = FeatureFlags(**base_flags.__dict__)
        flags.strict_stopwords = True
        
        test_cases = [
            "Оплата Ивану Петрову",
            "Payment to John Smith",
            "Beneficiary: Олена Ковальська",
            "Sender: Jane Doe"
        ]
        
        for input_text in test_cases:
            # Measure performance
            result, execution_time = await self._measure_performance(
                normalization_service.normalize_async,
                input_text,
                language="auto",
                feature_flags=flags
            )
            
            # Verify performance (p95 < 20ms)
            assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
            
            # Verify normalization
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            
            # Check that service words are filtered
            normalized = result.normalized.lower()
            service_words = ["оплата", "payment", "beneficiary", "sender", "to"]
            for word in service_words:
                assert word not in normalized, f"Service word '{word}' not filtered from '{input_text}'"

    @pytest.mark.asyncio
    async def test_performance_consistency(self, normalization_service, base_flags):
        """Test that performance is consistent across multiple runs."""
        input_text = "Иван Петров"
        flags = FeatureFlags(**base_flags.__dict__)
        
        execution_times = []
        for _ in range(10):
            _, execution_time = await self._measure_performance(
                normalization_service.normalize_async,
                input_text,
                language="ru",
                feature_flags=flags
            )
            execution_times.append(execution_time)
        
        # Calculate p95
        execution_times.sort()
        p95_index = int(0.95 * len(execution_times))
        p95_time = execution_times[p95_index]
        
        # Verify p95 < 20ms
        assert p95_time < 20.0, f"P95 performance too slow: {p95_time}ms (times: {execution_times})"

    @pytest.mark.asyncio
    async def test_trace_completeness(self, normalization_service, base_flags):
        """Test that trace contains all necessary information."""
        input_text = "И.. И. Петров"
        flags = FeatureFlags(**base_flags.__dict__)
        flags.fix_initials_double_dot = True
        
        result, execution_time = await self._measure_performance(
            normalization_service.normalize_async,
            input_text,
            language="ru",
            feature_flags=flags
        )
        
        # Verify performance
        assert execution_time < 20.0, f"Performance too slow: {execution_time}ms"
        
        # Verify result structure
        assert result.success, f"Normalization failed: {result.errors}"
        assert isinstance(result.trace, list), "Trace should be a list"
        assert len(result.trace) > 0, "Trace should not be empty"
        
        # Verify trace entries have required fields
        for entry in result.trace:
            if isinstance(entry, dict):
                assert "token" in entry or "type" in entry, f"Trace entry missing required fields: {entry}"
        
        # Verify metadata fields
        assert result.language is not None, "Language should be detected"
        assert result.original_length is not None, "Original length should be set"
        assert result.normalized_length is not None, "Normalized length should be set"
        assert result.token_count is not None, "Token count should be set"
        assert result.processing_time is not None, "Processing time should be set"
