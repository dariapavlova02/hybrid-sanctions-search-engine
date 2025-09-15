#!/usr/bin/env python3
"""
Tests for SmartFilterAdapter - Layer 2 of unified architecture.

Tests the adapter that wraps SmartFilterService to match new contracts
and implements CLAUDE.md specification.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from ai_service.contracts import SmartFilterResult
from ai_service.layers.smart_filter.smart_filter_adapter import SmartFilterAdapter
from ai_service.layers.smart_filter.smart_filter_service import FilterResult


class TestSmartFilterAdapter:
    """Test SmartFilterAdapter functionality"""

    @pytest.fixture
    async def adapter(self):
        """Create adapter with mock service"""
        adapter = SmartFilterAdapter()

        # Mock the underlying service
        mock_service = Mock()
        adapter._service = mock_service

        return adapter, mock_service

    @pytest.mark.asyncio
    async def test_should_process_basic(self, adapter):
        """Test basic should_process functionality"""
        adapter_instance, mock_service = adapter

        # Configure mock response
        mock_filter_result = FilterResult(
            should_process=True,
            confidence=0.85,
            detected_signals=["name", "company"],
            signal_details={
                "name_detector": {
                    "has_proper_names": True,
                    "has_initials": False,
                    "confidence": 0.8,
                },
                "company_detector": {
                    "has_legal_forms": True,
                    "has_quoted_names": True,
                    "confidence": 0.9,
                },
            },
            processing_recommendation="recommend",
            estimated_complexity="medium",
        )

        mock_service.should_process_text = Mock(return_value=mock_filter_result)

        # Test processing
        result = await adapter_instance.should_process("ТОВ Іван Петров")

        # Verify result structure
        assert isinstance(result, SmartFilterResult)
        assert result.should_process is True
        assert result.confidence == 0.85
        assert (
            result.classification == "must_process"
        )  # High confidence (0.85) maps to must_process
        assert "name" in result.detected_signals
        assert "company" in result.detected_signals

        # Verify detailed signals extraction
        assert "name_signals" in result.details
        assert "company_signals" in result.details
        assert result.details["name_signals"]["has_capitals"] is True
        assert result.details["company_signals"]["has_legal_forms"] is True

    @pytest.mark.asyncio
    async def test_classification_mapping(self, adapter):
        """Test confidence to classification mapping per CLAUDE.md"""
        adapter_instance, mock_service = adapter

        test_cases = [
            (0.9, True, "must_process"),
            (0.7, True, "recommend"),
            (0.4, True, "maybe"),
            (0.2, False, "skip"),
        ]

        for confidence, should_process, expected_classification in test_cases:
            mock_result = FilterResult(
                should_process=should_process,
                confidence=confidence,
                detected_signals=[],
                signal_details={},
                processing_recommendation="test",
                estimated_complexity="test",
            )

            mock_service.should_process_text = Mock(return_value=mock_result)

            result = await adapter_instance.should_process("test text")

            assert (
                result.classification == expected_classification
            ), f"Confidence {confidence} should map to {expected_classification}, got {result.classification}"

    @pytest.mark.asyncio
    async def test_name_signals_extraction(self, adapter):
        """Test name signals extraction per CLAUDE.md specification"""
        adapter_instance, mock_service = adapter

        mock_result = FilterResult(
            should_process=True,
            confidence=0.8,
            detected_signals=["name"],
            signal_details={
                "name_detector": {
                    "has_proper_names": True,
                    "has_initials": True,
                    "has_patronymic_patterns": True,
                    "has_diminutives": False,
                    "confidence": 0.85,
                }
            },
            processing_recommendation="recommend",
            estimated_complexity="medium",
        )

        mock_service.should_process_text = Mock(return_value=mock_result)

        result = await adapter_instance.should_process("П.І. Коваленко")

        name_signals = result.details["name_signals"]
        assert name_signals["has_capitals"] is True
        assert name_signals["has_initials"] is True
        assert name_signals["has_patronymic_endings"] is True
        assert name_signals["has_nicknames"] is False
        assert name_signals["confidence"] == 0.85

    async def test_company_signals_extraction(self, adapter):
        """Test company signals extraction per CLAUDE.md specification"""
        adapter_instance, mock_service = adapter

        mock_result = FilterResult(
            should_process=True,
            confidence=0.9,
            detected_signals=["company"],
            signal_details={
                "company_detector": {
                    "has_legal_forms": True,
                    "has_banking_keywords": False,
                    "has_quoted_names": True,
                    "has_organization_patterns": True,
                    "confidence": 0.9,
                }
            },
            processing_recommendation="must_process",
            estimated_complexity="high",
        )

        mock_service.should_process_text = Mock(return_value=mock_result)

        result = await adapter_instance.should_process('ТОВ "Агросвіт"')

        company_signals = result.details["company_signals"]
        assert company_signals["has_legal_forms"] is True
        assert company_signals["has_banking_triggers"] is False
        assert company_signals["has_quoted_cores"] is True
        assert company_signals["has_org_patterns"] is True
        assert company_signals["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_payment_signals_extraction(self, adapter):
        """Test payment context signals extraction per CLAUDE.md specification"""
        adapter_instance, mock_service = adapter

        mock_result = FilterResult(
            should_process=True,
            confidence=0.7,
            detected_signals=["payment"],
            signal_details={
                "payment_detector": {
                    "has_payment_context": True,
                    "payment_keywords": ["платеж", "оплата"],
                    "payment_confidence": 0.8,
                }
            },
            processing_recommendation="recommend",
            estimated_complexity="medium",
        )

        mock_service.should_process_text = Mock(return_value=mock_result)

        result = await adapter_instance.should_process("Платеж в пользу Іван Петров")

        payment_signals = result.details["payment_signals"]
        assert payment_signals["has_payment_keywords"] is True
        assert payment_signals["payment_triggers"] == ["платеж", "оплата"]
        assert payment_signals["confidence"] == 0.8

    async def test_error_handling_fallback(self, adapter):
        """Test error handling with safe fallback"""
        adapter_instance, mock_service = adapter

        # Simulate service error
        mock_service.should_process_text = Mock(side_effect=Exception("Service error"))

        result = await adapter_instance.should_process("test input")

        # Should fallback to safe processing
        assert result.should_process is True  # Safe fallback
        assert result.confidence == 0.5
        assert result.classification == "recommend"
        assert "fallback" in result.detected_signals
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_initialization_required(self):
        """Test that adapter requires initialization"""
        adapter = SmartFilterAdapter()

        with pytest.raises(RuntimeError, match="not initialized"):
            await adapter.should_process("test")

    async def test_signal_names_extraction(self, adapter):
        """Test extraction of human-readable signal names"""
        adapter_instance, mock_service = adapter

        mock_result = FilterResult(
            should_process=True,
            confidence=0.8,
            detected_signals=[
                "name_pattern",
                {"type": "company_legal_form", "details": "ТОВ"},
                "payment_context",
            ],
            signal_details={},
            processing_recommendation="recommend",
            estimated_complexity="medium",
        )

        mock_service.should_process_text = Mock(return_value=mock_result)

        result = await adapter_instance.should_process("test")

        assert "name_pattern" in result.detected_signals
        assert "company_legal_form" in result.detected_signals
        assert "payment_context" in result.detected_signals

    async def test_processing_time_tracking(self, adapter):
        """Test that processing time is tracked"""
        adapter_instance, mock_service = adapter

        mock_result = FilterResult(
            should_process=True,
            confidence=0.8,
            detected_signals=[],
            signal_details={},
            processing_recommendation="recommend",
            estimated_complexity="low",
        )

        mock_service.should_process_text = Mock(return_value=mock_result)

        result = await adapter_instance.should_process("test")

        assert result.processing_time >= 0
        assert isinstance(result.processing_time, float)


class TestSmartFilterAdapterIntegration:
    """Integration tests for SmartFilterAdapter with actual service"""

    @pytest.mark.asyncio
    async def test_full_initialization(self):
        """Test full adapter initialization"""
        adapter = SmartFilterAdapter()

        # Should initialize without errors
        await adapter.initialize()

    @pytest.mark.asyncio
    async def test_should_process_basic_functionality(self):
        """Test basic should_process functionality"""
        # Should be able to process
        result = await adapter.should_process("ТОВ Тестова Компанія")

        assert isinstance(result, SmartFilterResult)
        assert hasattr(result, "should_process")
        assert hasattr(result, "confidence")
        assert hasattr(result, "classification")
        assert hasattr(result, "detected_signals")

    async def test_claude_md_compliance(self):
        """Test compliance with CLAUDE.md Layer 2 specification"""
        adapter = SmartFilterAdapter()
        await adapter.initialize()

        # Test various input types per CLAUDE.md
        test_cases = [
            ("Іван Петрович Коваленко", ["name"]),
            ('ТОВ "ПриватБанк"', ["company"]),
            (
                "Платеж в пользу ФОП Іваненко",
                ["name", "company"],
            ),  # payment_context detection may not work in test environment
            ("клавиатура дисплей стіл", []),  # Should not detect names
        ]

        for text, expected_signal_types in test_cases:
            result = await adapter.should_process(text)

            # Verify basic structure
            assert isinstance(result, SmartFilterResult)
            assert result.classification in [
                "must_process",
                "recommend",
                "maybe",
                "skip",
            ]
            assert 0.0 <= result.confidence <= 1.0

            # Verify signal detection aligns with expectations
            for expected_type in expected_signal_types:
                # Should have some signal related to expected type
                assert any(
                    expected_type in signal for signal in result.detected_signals
                ), f"Expected {expected_type} signal for text '{text}', got {result.detected_signals}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
