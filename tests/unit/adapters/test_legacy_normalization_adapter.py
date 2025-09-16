"""
Tests for LegacyNormalizationAdapter
"""

import asyncio
import pytest
from unittest.mock import Mock, patch

from src.ai_service.adapters.legacy_normalization_adapter import LegacyNormalizationAdapter
from src.ai_service.contracts.base_contracts import NormalizationResult, TokenTrace


class TestLegacyNormalizationAdapter:
    """Test legacy normalization adapter functionality"""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance for testing"""
        return LegacyNormalizationAdapter()

    @pytest.fixture
    def sample_normalization_result(self):
        """Sample normalization result for testing"""
        trace = TokenTrace(
            token="Иван",
            role="given",
            rule="case_normalized",
            output="Иван",
            morph_lang="ru",
            normal_form="иван",
            fallback=False,
            notes=None
        )

        return NormalizationResult(
            normalized="Иван Петров",
            tokens=["Иван", "Петров"],
            trace=[trace],
            errors=[],
            language="ru",
            confidence=0.95,
            original_length=15,
            normalized_length=11,
            token_count=2,
            processing_time=0.12,
            success=True
        )

    def test_convert_to_legacy_format(self, adapter, sample_normalization_result):
        """Test conversion to legacy format"""
        legacy_result = adapter.convert_to_legacy_format(sample_normalization_result)

        assert legacy_result["normalized_text"] == "Иван Петров"
        assert legacy_result["tokens"] == ["Иван", "Петров"]
        assert legacy_result["language"] == "ru"
        assert legacy_result["confidence"] == 0.95
        assert legacy_result["success"] is True
        assert legacy_result["processing_time"] == 0.12
        assert legacy_result["error"] is None

        # Check trace conversion
        assert len(legacy_result["trace"]) == 1
        trace = legacy_result["trace"][0]
        assert trace["token"] == "Иван"
        assert trace["role"] == "given"
        assert trace["rule"] == "case_normalized"
        assert trace["output"] == "Иван"

    def test_convert_from_legacy_format(self, adapter):
        """Test conversion from legacy format"""
        legacy_data = {
            "normalized_text": "Анна Иванова",
            "original_text": "Анны Ивановой",
            "tokens": ["Анна", "Иванова"],
            "language": "ru",
            "confidence": 0.88,
            "success": True,
            "processing_time": 0.08,
            "error": None,
            "trace": [
                {
                    "token": "Анны",
                    "role": "given",
                    "rule": "morph_gender_adjusted",
                    "output": "Анна",
                    "morph_lang": "ru",
                    "normal_form": "анна",
                    "fallback": False,
                    "notes": None
                }
            ]
        }

        result = adapter.convert_from_legacy_format(legacy_data)

        assert result.normalized == "Анна Иванова"
        assert result.tokens == ["Анна", "Иванова"]
        assert result.language == "ru"
        assert result.confidence == 0.88
        assert result.success is True
        assert result.processing_time == 0.08
        assert len(result.errors) == 0

        # Check trace conversion
        assert len(result.trace) == 1
        trace = result.trace[0]
        assert trace.token == "Анны"
        assert trace.role == "given"
        assert trace.rule == "morph_gender_adjusted"
        assert trace.output == "Анна"

    @pytest.mark.asyncio
    async def test_normalize_legacy(self, adapter):
        """Test legacy async normalization"""
        # Mock the normalization service
        mock_result = NormalizationResult(
            normalized="Петр Сидоров",
            tokens=["Петр", "Сидоров"],
            trace=[],
            errors=[],
            language="ru",
            confidence=0.92,
            original_length=10,
            normalized_length=12,
            token_count=2,
            processing_time=0.05,
            success=True
        )

        with patch.object(adapter.normalization_service, 'normalize_async', return_value=mock_result):
            result = await adapter.normalize_legacy("Петра Сидорова")

            assert result["normalized_text"] == "Петр Сидоров"
            assert result["original_text"] == "Петра Сидорова"
            assert result["success"] is True
            assert result["language"] == "ru"

    def test_normalize_legacy_sync(self, adapter):
        """Test legacy sync normalization"""
        # Mock the normalization service
        mock_result = NormalizationResult(
            normalized="Мария Козлова",
            tokens=["Мария", "Козлова"],
            trace=[],
            errors=[],
            language="ru",
            confidence=0.89,
            original_length=12,
            normalized_length=13,
            token_count=2,
            processing_time=0.07,
            success=True
        )

        with patch.object(adapter.normalization_service, 'normalize_async', return_value=mock_result):
            result = adapter.normalize_legacy_sync("Марии Козловой")

            assert result["normalized_text"] == "Мария Козлова"
            assert result["original_text"] == "Марии Козловой"
            assert result["success"] is True
            assert result["language"] == "ru"

    @pytest.mark.asyncio
    async def test_process_batch_legacy(self, adapter):
        """Test legacy batch processing"""
        texts = ["Иван Петров", "Анна Сидорова"]

        mock_result1 = NormalizationResult(
            normalized="Иван Петров", tokens=["Иван", "Петров"], trace=[], errors=[],
            language="ru", confidence=0.95, original_length=11, normalized_length=11,
            token_count=2, processing_time=0.03, success=True
        )
        mock_result2 = NormalizationResult(
            normalized="Анна Сидорова", tokens=["Анна", "Сидорова"], trace=[], errors=[],
            language="ru", confidence=0.93, original_length=12, normalized_length=12,
            token_count=2, processing_time=0.04, success=True
        )

        with patch.object(adapter.normalization_service, 'normalize_async', side_effect=[mock_result1, mock_result2]):
            results = await adapter.process_batch_legacy(texts)

            assert len(results) == 2
            assert results[0]["normalized_text"] == "Иван Петров"
            assert results[1]["normalized_text"] == "Анна Сидорова"

    def test_health_check(self, adapter):
        """Test adapter health check"""
        with patch.object(adapter, 'normalize_legacy_sync', return_value={"success": True}):
            health = adapter.health_check()

            assert health["status"] == "healthy"
            assert health["adapter_version"] == "1.0.0"
            assert health["normalization_service"] == "available"
            assert health["test_successful"] is True
            assert "normalize_legacy" in health["supported_methods"]

    def test_legacy_aliases(self, adapter):
        """Test legacy method aliases"""
        with patch.object(adapter, 'normalize_legacy') as mock_normalize:
            # Test process_text alias
            asyncio.run(adapter.process_text("test text"))
            mock_normalize.assert_called_once_with("test text")

        with patch.object(adapter, 'normalize_legacy_sync') as mock_normalize_sync:
            # Test process_text_sync alias
            adapter.process_text_sync("test text")
            mock_normalize_sync.assert_called_once_with("test text")

    def test_error_handling(self, adapter):
        """Test error handling in legacy methods"""
        with patch.object(adapter.normalization_service, 'normalize_async', side_effect=Exception("Test error")):
            result = adapter.normalize_legacy_sync("test text")

            assert result["success"] is False
            assert result["error"] == "Test error"
            assert result["normalized_text"] == ""
            assert result["original_text"] == "test text"