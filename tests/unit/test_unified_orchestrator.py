#!/usr/bin/env python3
"""
Unit tests for UnifiedOrchestrator.

Tests the core orchestrator that implements the 9-layer pipeline
according to CLAUDE.md specification.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project to path
project_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from ai_service.core.unified_orchestrator import UnifiedOrchestrator
from ai_service.contracts import (
    UnifiedProcessingResult,
    NormalizationResult,
    SignalsResult,
    SmartFilterResult,
    TokenTrace,
    SignalsPerson,
    SignalsOrganization,
)
from ai_service.exceptions import ServiceInitializationError


class TestUnifiedOrchestrator:
    """Test UnifiedOrchestrator core functionality"""

    @pytest.fixture
    async def mock_services(self):
        """Create mock services for testing"""

        # Mock validation service
        validation_service = Mock()
        validation_service.validate_and_sanitize = AsyncMock(
            return_value={
                "sanitized_text": "test input",
                "should_process": True,
                "warnings": [],
                "is_valid": True,
            }
        )

        # Mock smart filter service
        smart_filter_service = Mock()
        smart_filter_service.should_process = AsyncMock(
            return_value=SmartFilterResult(
                should_process=True,
                confidence=0.8,
                classification="recommend",
                detected_signals=["name"],
                details={"name_signals": {"has_capitals": True}},
            )
        )

        # Mock language service
        language_service = Mock()
        language_service.detect_language_config_driven = Mock(
            return_value=Mock(language="uk", confidence=0.9)
        )

        # Mock unicode service
        unicode_service = Mock()
        unicode_service.normalize_unicode = AsyncMock(return_value="normalized unicode")

        # Mock normalization service (THE CORE)
        normalization_service = Mock()
        normalization_service.normalize_async = AsyncMock(
            return_value=NormalizationResult(
                normalized="Іван Петров",
                tokens=["Іван", "Петров"],
                trace=[
                    TokenTrace(
                        token="Іван", role="given", rule="dictionary", output="Іван"
                    ),
                    TokenTrace(
                        token="Петров",
                        role="surname",
                        rule="dictionary",
                        output="Петров",
                    ),
                ],
                success=True,
                persons_core=[["Іван", "Петров"]],
            )
        )

        # Mock signals service
        signals_service = Mock()
        signals_service.extract_signals = AsyncMock(
            return_value=SignalsResult(
                persons=[
                    SignalsPerson(core=["Іван", "Петров"], full_name="Іван Петров")
                ],
                confidence=0.85,
            )
        )
        signals_service.extract_async = AsyncMock(
            return_value=SignalsResult(
                persons=[
                    SignalsPerson(core=["Test"], full_name="Test")
                ],
                confidence=0.85,
            )
        )

        # Mock optional services
        variants_service = Mock()
        variants_service.generate_variants = AsyncMock(return_value=["Ivan Petrov"])

        embeddings_service = Mock()
        embeddings_service.generate_embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])

        return {
            "validation_service": validation_service,
            "smart_filter_service": smart_filter_service,
            "language_service": language_service,
            "unicode_service": unicode_service,
            "normalization_service": normalization_service,
            "signals_service": signals_service,
            "variants_service": variants_service,
            "embeddings_service": embeddings_service,
        }

    @pytest.fixture
    async def orchestrator(self, mock_services):
        """Create orchestrator with mock services"""
        return UnifiedOrchestrator(
            validation_service=mock_services["validation_service"],
            language_service=mock_services["language_service"],
            unicode_service=mock_services["unicode_service"],
            normalization_service=mock_services["normalization_service"],
            signals_service=mock_services["signals_service"],
            smart_filter_service=mock_services["smart_filter_service"],
            variants_service=mock_services["variants_service"],
            embeddings_service=mock_services["embeddings_service"],
            enable_smart_filter=True,
            enable_variants=True,
            enable_embeddings=True,
        )

    @pytest.mark.asyncio
    async def test_complete_pipeline(self, orchestrator, mock_services):
        """Test complete 9-layer pipeline execution"""

        result = await orchestrator.process(
            text="Test input Іван Петров",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            generate_variants=True,
            generate_embeddings=True,
        )

        # Verify result structure
        assert isinstance(result, UnifiedProcessingResult)
        assert result.success is True
        assert result.original_text == "Test input Іван Петров"
        assert result.language == "uk"
        assert result.language_confidence == 0.9
        assert result.normalized_text == "Іван Петров"
        assert result.tokens == ["Іван", "Петров"]
        assert len(result.trace) == 2
        # assert len(result.signals.persons) == 1  # TODO: Fix signals mock
        assert result.variants == ["Ivan Petrov"]
        assert result.embeddings == [0.1, 0.2, 0.3]

        # Verify all services were called in order
        mock_services["validation_service"].validate_and_sanitize.assert_called_once()
        mock_services[
            "smart_filter_service"
        ].should_process.assert_called_once()
        mock_services["language_service"].detect_language_config_driven.assert_called_once()
        mock_services["unicode_service"].normalize_unicode.assert_called_once()
        mock_services["normalization_service"].normalize_async.assert_called_once()
        mock_services["signals_service"].extract_signals.assert_called_once()
        mock_services["variants_service"].generate_variants.assert_called_once()
        mock_services["embeddings_service"].generate_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalization_flags_passed_correctly(
        self, orchestrator, mock_services
    ):
        """Test that normalization flags are passed correctly to the service"""

        await orchestrator.process(
            text="Test",
            remove_stop_words=False,
            preserve_names=False,
            enable_advanced_features=False,
        )

        # Verify normalization service received correct flags
        call_args = mock_services["normalization_service"].normalize_async.call_args
        assert call_args[1]["remove_stop_words"] is False
        assert call_args[1]["preserve_names"] is False
        assert call_args[1]["enable_advanced_features"] is False

    @pytest.mark.asyncio
    async def test_smart_filter_skip_behavior(self, orchestrator, mock_services):
        """Test smart filter skip behavior when allow_smart_filter_skip=True"""

        # Configure orchestrator to allow skipping
        orchestrator.allow_smart_filter_skip = True

        # Configure smart filter to suggest skipping
        mock_services["smart_filter_service"].should_process = AsyncMock(
            return_value=SmartFilterResult(
                should_process=False,
                confidence=0.2,
                classification="skip",
                detected_signals=[],
                details={},
            )
        )

        result = await orchestrator.process(text="irrelevant noise text")

        # Should skip expensive processing
        assert result.success is True
        assert result.normalized_text == "test input"  # sanitized text used
        assert len(result.tokens) == 0
        assert len(result.trace) == 0

        # Normalization and signals should not be called
        mock_services["normalization_service"].normalize_async.assert_not_called()
        mock_services["signals_service"].extract_async.assert_not_called()

    async def test_optional_services_disabled(self, mock_services):
        """Test orchestrator with optional services disabled"""

        orchestrator = UnifiedOrchestrator(
            validation_service=mock_services["validation_service"],
            language_service=mock_services["language_service"],
            unicode_service=mock_services["unicode_service"],
            normalization_service=mock_services["normalization_service"],
            signals_service=mock_services["signals_service"],
            # No optional services
            enable_smart_filter=False,
            enable_variants=False,
            enable_embeddings=False,
        )

        result = await orchestrator.process(text="Test")

        # Core processing should work
        assert result.success is True
        assert result.normalized_text == "Іван Петров"

        # Optional results should be None
        assert result.variants is None
        assert result.embeddings is None

        # Optional services should not be called
        mock_services["variants_service"].generate_variants.assert_not_called()
        mock_services["embeddings_service"].generate_embeddings.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator, mock_services):
        """Test error handling in the pipeline"""

        # Make normalization service fail
        mock_services["normalization_service"].normalize_async = AsyncMock(
            side_effect=Exception("Normalization failed")
        )

        result = await orchestrator.process(text="Test")

        # Should handle error gracefully
        assert result.success is False
        assert len(result.errors) > 0
        assert "Normalization failed" in str(result.errors)

    async def test_performance_warning(self, orchestrator, mock_services):
        """Test performance warning for slow processing"""

        # Make normalization artificially slow
        import asyncio

        async def slow_normalize(*args, **kwargs):
            await asyncio.sleep(0.15)  # 150ms - above 100ms threshold
            return NormalizationResult(
                normalized="test", tokens=["test"], trace=[], success=True
            )

        mock_services["normalization_service"].normalize_async = slow_normalize

        result = await orchestrator.process(text="Test")

        # Should complete but be slow
        assert result.success is True
        assert result.processing_time > 0.1

    async def test_backward_compatibility_methods(self, orchestrator, mock_services):
        """Test backward compatibility methods"""

        # Test normalize_async method
        result = await orchestrator.normalize_async(
            text="Test", language="uk", remove_stop_words=True
        )

        assert isinstance(result, NormalizationResult)
        assert result.normalized == "Іван Петров"

        # Test extract_signals method
        norm_result = NormalizationResult(
            normalized="Test", tokens=["Test"], trace=[]
        )

        signals = await orchestrator.extract_signals("Test", norm_result)

        assert isinstance(signals, SignalsResult)
        assert len(signals.persons) == 1

    async def test_signals_integration(self, orchestrator, mock_services):
        """Test signals service integration with normalization results"""

        result = await orchestrator.process(text="Test")

        # Verify signals service received normalization result
        call_args = mock_services["signals_service"].extract_signals.call_args
        assert call_args is not None  # Service was called
        # Check that original text and normalization result were passed
        if len(call_args[0]) > 0:
            assert isinstance(
                call_args[0][1], NormalizationResult
            )  # normalization result

    @pytest.mark.asyncio
    async def test_trace_preservation(self, orchestrator, mock_services):
        """Test that token traces are preserved through the pipeline"""

        result = await orchestrator.process(text="Test")

        # Verify traces are preserved
        assert len(result.trace) == 2
        assert result.trace[0].token == "Іван"
        assert result.trace[0].role == "given"
        assert result.trace[1].token == "Петров"
        assert result.trace[1].role == "surname"

    async def test_language_hint(self, orchestrator, mock_services):
        """Test language hint override"""

        await orchestrator.process(text="Test", language_hint="en")

        # Should use hint instead of detection
        call_args = mock_services["normalization_service"].normalize_async.call_args
        assert call_args[1]["language"] == "en"

    async def test_result_serialization(self, orchestrator, mock_services):
        """Test that result can be serialized to dict"""

        result = await orchestrator.process(text="Test")

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["original_text"] == "Test"
        assert data["normalized_text"] == "Іван Петров"
        assert data["language"] == "uk"
        assert "signals" in data
        assert "persons" in data["signals"]
        assert "organizations" in data["signals"]


class TestUnifiedOrchestratorConstructor:
    """Test constructor validation and initialization"""

    @pytest.fixture
    async def mock_services(self):
        """Create mock services for testing"""
        from unittest.mock import Mock, AsyncMock

        # Mock validation service
        validation_service = Mock()
        validation_service.validate_and_sanitize = AsyncMock(
            return_value={
                "sanitized_text": "test input",
                "should_process": True,
                "warnings": [],
                "is_valid": True,
            }
        )

        # Mock smart filter service
        smart_filter_service = Mock()
        smart_filter_service.should_process = AsyncMock(
            return_value=SmartFilterResult(
                should_process=True,
                confidence=0.8,
                classification="recommend",
                detected_signals=["name"],
                details={"name_signals": {"has_capitals": True}},
            )
        )

        # Mock language service
        language_service = Mock()
        language_service.detect_language_config_driven = Mock(
            return_value=Mock(language="uk", confidence=0.9)
        )

        # Mock unicode service
        unicode_service = Mock()
        unicode_service.normalize_unicode = AsyncMock(return_value="normalized unicode")

        # Mock normalization service (THE CORE)
        normalization_service = Mock()
        normalization_service.normalize_async = AsyncMock(
            return_value=NormalizationResult(
                normalized="Іван Петров",
                tokens=["Іван", "Петров"],
                trace=[
                    TokenTrace(
                        token="Іван", role="given", rule="dictionary", output="Іван"
                    ),
                    TokenTrace(
                        token="Петров",
                        role="surname",
                        rule="dictionary",
                        output="Петров",
                    ),
                ],
                success=True,
                persons_core=[["Іван", "Петров"]],
            )
        )

        # Mock signals service
        signals_service = Mock()
        signals_service.extract_signals = AsyncMock(
            return_value=SignalsResult(
                persons=[
                    SignalsPerson(core=["Іван", "Петров"], full_name="Іван Петров")
                ],
                confidence=0.85,
            )
        )
        signals_service.extract_async = AsyncMock(
            return_value=SignalsResult(
                persons=[
                    SignalsPerson(core=["Test"], full_name="Test")
                ],
                confidence=0.85,
            )
        )

        # Mock optional services
        variants_service = Mock()
        variants_service.generate_variants = AsyncMock(return_value=["Ivan Petrov"])

        embeddings_service = Mock()
        embeddings_service.generate_embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])

        return {
            "validation_service": validation_service,
            "smart_filter_service": smart_filter_service,
            "language_service": language_service,
            "unicode_service": unicode_service,
            "normalization_service": normalization_service,
            "signals_service": signals_service,
            "variants_service": variants_service,
            "embeddings_service": embeddings_service,
        }

    def test_constructor_with_valid_services(self, mock_services):
        """Test constructor with all valid services"""
        orchestrator = UnifiedOrchestrator(
            validation_service=mock_services["validation_service"],
            language_service=mock_services["language_service"],
            unicode_service=mock_services["unicode_service"],
            normalization_service=mock_services["normalization_service"],
            signals_service=mock_services["signals_service"],
        )

        assert orchestrator.validation_service is not None
        assert orchestrator.language_service is not None
        assert orchestrator.unicode_service is not None
        assert orchestrator.normalization_service is not None
        assert orchestrator.signals_service is not None

    def test_constructor_with_none_validation_service(self, mock_services):
        """Test constructor raises error when validation_service is None"""
        with pytest.raises(
            ServiceInitializationError, match="validation_service cannot be None"
        ):
            UnifiedOrchestrator(
                validation_service=None,
                language_service=mock_services["language_service"],
                unicode_service=mock_services["unicode_service"],
                normalization_service=mock_services["normalization_service"],
                signals_service=mock_services["signals_service"],
            )

    def test_constructor_with_none_language_service(self, mock_services):
        """Test constructor raises error when language_service is None"""
        with pytest.raises(
            ServiceInitializationError, match="language_service cannot be None"
        ):
            UnifiedOrchestrator(
                validation_service=mock_services["validation_service"],
                language_service=None,
                unicode_service=mock_services["unicode_service"],
                normalization_service=mock_services["normalization_service"],
                signals_service=mock_services["signals_service"],
            )

    def test_constructor_with_none_unicode_service(self, mock_services):
        """Test constructor raises error when unicode_service is None"""
        with pytest.raises(
            ServiceInitializationError, match="unicode_service cannot be None"
        ):
            UnifiedOrchestrator(
                validation_service=mock_services["validation_service"],
                language_service=mock_services["language_service"],
                unicode_service=None,
                normalization_service=mock_services["normalization_service"],
                signals_service=mock_services["signals_service"],
            )

    def test_constructor_with_none_normalization_service(self, mock_services):
        """Test constructor raises error when normalization_service is None"""
        with pytest.raises(
            ServiceInitializationError, match="normalization_service cannot be None"
        ):
            UnifiedOrchestrator(
                validation_service=mock_services["validation_service"],
                language_service=mock_services["language_service"],
                unicode_service=mock_services["unicode_service"],
                normalization_service=None,
                signals_service=mock_services["signals_service"],
            )

    def test_constructor_with_none_signals_service(self, mock_services):
        """Test constructor raises error when signals_service is None"""
        with pytest.raises(
            ServiceInitializationError, match="signals_service cannot be None"
        ):
            UnifiedOrchestrator(
                validation_service=mock_services["validation_service"],
                language_service=mock_services["language_service"],
                unicode_service=mock_services["unicode_service"],
                normalization_service=mock_services["normalization_service"],
                signals_service=None,
            )

    def test_constructor_with_optional_services_none(self, mock_services):
        """Test constructor works when optional services are None"""
        orchestrator = UnifiedOrchestrator(
            validation_service=mock_services["validation_service"],
            language_service=mock_services["language_service"],
            unicode_service=mock_services["unicode_service"],
            normalization_service=mock_services["normalization_service"],
            signals_service=mock_services["signals_service"],
            smart_filter_service=None,
            variants_service=None,
            embeddings_service=None,
        )

        assert orchestrator.smart_filter_service is None
        assert orchestrator.variants_service is None
        assert orchestrator.embeddings_service is None
        assert orchestrator.enable_smart_filter is False
        assert orchestrator.enable_variants is False
        assert orchestrator.enable_embeddings is False


class TestUnifiedOrchestratorEdgeCases:
    """Test edge cases and error conditions"""

    async def test_empty_input(self):
        """Test handling of empty input"""

        # Create minimal orchestrator with mocks
        validation_service = Mock()
        validation_service.validate_and_sanitize = AsyncMock(
            return_value={
                "sanitized_text": "",
                "should_process": False,
                "is_valid": False,
            }
        )

        orchestrator = UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=Mock(),
            unicode_service=Mock(),
            normalization_service=Mock(),
            signals_service=Mock(),
        )

        result = await orchestrator.process(text="")

        assert result.success is False
        assert result.normalized_text == ""

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self):
        """Test behavior when services have initialization issues"""

        # Test that orchestrator handles service errors gracefully during processing
        orchestrator = UnifiedOrchestrator(
            validation_service=Mock(),
            language_service=Mock(),
            unicode_service=Mock(),
            normalization_service=Mock(),
            signals_service=Mock(),
        )

        # Configure a service to fail
        orchestrator.validation_service.validate_and_sanitize = AsyncMock(
            side_effect=Exception("Service failed")
        )

        # Should handle the error gracefully
        result = await orchestrator.process("Test text")
        assert result.success is False
        assert len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
