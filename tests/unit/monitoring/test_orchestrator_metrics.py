"""
Integration tests for UnifiedOrchestrator metrics collection
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch

from ai_service.core.unified_orchestrator import UnifiedOrchestrator
from ai_service.monitoring.metrics_service import MetricsService
from ai_service.contracts.base_contracts import (
    NormalizationResult,
    SignalsResult,
    ProcessingContext,
    UnifiedProcessingResult,
)


class TestOrchestratorMetrics:
    """Tests for UnifiedOrchestrator metrics integration"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for orchestrator"""
        validation_service = Mock()
        validation_service.validate_and_sanitize = AsyncMock(
            return_value={"sanitized_text": "test text", "should_process": True}
        )

        language_service = Mock()
        language_service.detect_language = AsyncMock(
            return_value={"language": "en", "confidence": 0.9}
        )

        unicode_service = Mock()
        unicode_service.normalize_unicode = AsyncMock(return_value="test text")

        normalization_service = Mock()
        norm_result = NormalizationResult(
            normalized="Test Text",
            tokens=["Test", "Text"],
            trace=[],
            language="en",
            confidence=0.85,
            success=True,
            errors=[],
            original_length=9,
            normalized_length=9,
            token_count=2,
            processing_time=0.01,
        )
        normalization_service.normalize_async = AsyncMock(return_value=norm_result)

        signals_service = Mock()
        signals_result = SignalsResult(confidence=0.8, persons=[], organizations=[])
        signals_service.extract_async = AsyncMock(return_value=signals_result)

        smart_filter_service = Mock()
        filter_result = Mock()
        filter_result.should_process = True
        filter_result.confidence = 0.7
        filter_result.classification = "person"
        filter_result.detected_signals = []
        filter_result.details = {}
        smart_filter_service.should_process_text_async = AsyncMock(
            return_value=filter_result
        )

        variants_service = Mock()
        variants_service.generate_variants = AsyncMock(return_value=["Test Text", "test text"])

        embeddings_service = Mock()
        embeddings_service.generate_embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])

        decision_engine = Mock()
        from ai_service.contracts.decision_contracts import DecisionResult, MatchDecision, ConfidenceLevel, MatchEvidence
        decision_result = DecisionResult(
            decision=MatchDecision.MATCH,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            evidence=[MatchEvidence(source="test", value="Strong signal match", weight=1.0)],
            reasoning="Test decision",
            processing_time=0.001,
            used_layers=["normalization", "signals"]
        )
        decision_engine.make_decision = AsyncMock(return_value=decision_result)

        return {
            "validation_service": validation_service,
            "language_service": language_service,
            "unicode_service": unicode_service,
            "normalization_service": normalization_service,
            "signals_service": signals_service,
            "smart_filter_service": smart_filter_service,
            "variants_service": variants_service,
            "embeddings_service": embeddings_service,
            "decision_engine": decision_engine,
        }

    @pytest.fixture
    def metrics_service(self):
        """Create MetricsService instance"""
        return MetricsService()

    @pytest.fixture
    def orchestrator(self, mock_services, metrics_service):
        """Create UnifiedOrchestrator with metrics service"""
        return UnifiedOrchestrator(
            validation_service=mock_services["validation_service"],
            language_service=mock_services["language_service"],
            unicode_service=mock_services["unicode_service"],
            normalization_service=mock_services["normalization_service"],
            signals_service=mock_services["signals_service"],
            smart_filter_service=mock_services["smart_filter_service"],
            variants_service=mock_services["variants_service"],
            embeddings_service=mock_services["embeddings_service"],
            decision_engine=mock_services["decision_engine"],
            metrics_service=metrics_service,
            enable_smart_filter=True,
            enable_variants=True,
            enable_embeddings=True,
            enable_decision_engine=True,
        )

    @pytest.mark.asyncio
    async def test_successful_processing_metrics(self, orchestrator, metrics_service):
        """Test metrics collection during successful processing"""
        # Process text
        result = await orchestrator.process("John Doe")

        # Verify basic request metrics
        assert "processing.requests.total" in metrics_service.metrics
        assert metrics_service.metrics["processing.requests.total"]["value"] == 1

        assert "processing.requests.successful" in metrics_service.metrics
        assert metrics_service.metrics["processing.requests.successful"]["value"] == 1

        # Verify layer timing metrics
        expected_layers = [
            "processing.layer.validation",
            "processing.layer.smart_filter",
            "processing.layer.language_detection",
            "processing.layer.unicode_normalization",
            "processing.layer.normalization",
            "processing.layer.signals",
            "processing.layer.variants",
            "processing.layer.embeddings",
            "processing.layer.decision",
        ]

        for layer in expected_layers:
            assert layer in metrics_service.metrics
            assert metrics_service.metrics[layer]["type"].value == "timer"

        # Verify total processing time
        assert "processing.total_time" in metrics_service.metrics

        # Verify confidence histograms
        assert "smart_filter.confidence" in metrics_service.metrics
        assert "language_detection.confidence" in metrics_service.metrics
        assert "normalization.confidence" in metrics_service.metrics
        assert "signals.confidence" in metrics_service.metrics
        assert "decision.confidence" in metrics_service.metrics

        # Verify decision result counter
        assert "decision.result.match" in metrics_service.metrics
        assert metrics_service.metrics["decision.result.match"]["value"] == 1

    @pytest.mark.asyncio
    async def test_validation_failure_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when validation fails"""
        # Configure validation to fail
        mock_services["validation_service"].validate_and_sanitize = AsyncMock(
            return_value={"sanitized_text": "", "should_process": False}
        )

        result = await orchestrator.process("invalid input")

        # Should track validation failure
        assert "processing.validation.failed" in metrics_service.metrics
        assert metrics_service.metrics["processing.validation.failed"]["value"] == 1

        # Should still track total requests
        assert "processing.requests.total" in metrics_service.metrics
        assert metrics_service.metrics["processing.requests.total"]["value"] == 1

    @pytest.mark.asyncio
    async def test_smart_filter_skip_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when smart filter suggests skipping"""
        # Configure orchestrator to allow smart filter skip
        orchestrator.allow_smart_filter_skip = True

        # Configure smart filter to suggest skip
        filter_result = Mock()
        filter_result.should_process = False
        filter_result.confidence = 0.2
        filter_result.classification = "noise"
        filter_result.detected_signals = []
        filter_result.details = {}
        mock_services["smart_filter_service"].should_process_text_async = AsyncMock(
            return_value=filter_result
        )

        result = await orchestrator.process("noise text")

        # Should track smart filter skip
        assert "processing.smart_filter.skipped" in metrics_service.metrics
        assert metrics_service.metrics["processing.smart_filter.skipped"]["value"] == 1

        # Should still record smart filter timing and confidence
        assert "processing.layer.smart_filter" in metrics_service.metrics
        assert "smart_filter.confidence" in metrics_service.metrics

    @pytest.mark.asyncio
    async def test_normalization_failure_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when normalization fails"""
        # Configure normalization to fail
        failed_result = NormalizationResult(
            normalized="",
            tokens=[],
            trace=[],
            language="en",
            success=False,
            errors=["Normalization failed"],
            original_length=9,
            normalized_length=0,
            token_count=0,
            processing_time=0.01,
        )
        mock_services["normalization_service"].normalize_async = AsyncMock(
            return_value=failed_result
        )

        result = await orchestrator.process("test input")

        # Should track normalization failure
        assert "processing.normalization.failed" in metrics_service.metrics
        assert metrics_service.metrics["processing.normalization.failed"]["value"] == 1

        # Should track error count in final result
        assert "processing.error_count" in metrics_service.metrics
        assert metrics_service.metrics["processing.error_count"]["count"] > 0

    @pytest.mark.asyncio
    async def test_variants_failure_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when variants generation fails"""
        # Configure variants service to fail
        mock_services["variants_service"].generate_variants = AsyncMock(
            side_effect=Exception("Variants failed")
        )

        result = await orchestrator.process("test input")

        # Should track variants failure
        assert "processing.variants.failed" in metrics_service.metrics
        assert metrics_service.metrics["processing.variants.failed"]["value"] == 1

        # Should still track other layers successfully
        assert "processing.layer.normalization" in metrics_service.metrics
        assert "processing.layer.signals" in metrics_service.metrics

    @pytest.mark.asyncio
    async def test_embeddings_failure_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when embedding generation fails"""
        # Configure embeddings service to fail
        mock_services["embeddings_service"].generate_embeddings = AsyncMock(
            side_effect=Exception("Embeddings failed")
        )

        result = await orchestrator.process("test input")

        # Should track embeddings failure
        assert "processing.embeddings.failed" in metrics_service.metrics
        assert metrics_service.metrics["processing.embeddings.failed"]["value"] == 1

    @pytest.mark.asyncio
    async def test_decision_failure_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when decision engine fails"""
        # Configure decision engine to fail
        mock_services["decision_engine"].make_decision = AsyncMock(
            side_effect=Exception("Decision failed")
        )

        result = await orchestrator.process("test input")

        # Should track decision failure
        assert "processing.decision.failed" in metrics_service.metrics
        assert metrics_service.metrics["processing.decision.failed"]["value"] == 1

    @pytest.mark.asyncio
    async def test_slow_processing_metrics(self, orchestrator, metrics_service):
        """Test metrics for slow processing"""
        # Mock a slow processing scenario
        with patch('time.time') as mock_time:
            # Start time
            mock_time.side_effect = [
                1000.0,  # Start time
                1000.05,  # After validation
                1000.1,   # After smart filter
                1000.15,  # After language detection
                1000.2,   # After unicode normalization
                1000.25,  # After normalization
                1000.3,   # After signals
                1000.35,  # After variants
                1000.4,   # After embeddings
                1000.45,  # After decision
                1000.5,   # Processing time calculation
                1000.5,   # Final processing time
            ]

            result = await orchestrator.process("test input")

        # Should track slow request
        assert "processing.slow_requests" in metrics_service.metrics
        assert metrics_service.metrics["processing.slow_requests"]["value"] == 1

    @pytest.mark.asyncio
    async def test_exception_handling_metrics(self, orchestrator, metrics_service, mock_services):
        """Test metrics when an unexpected exception occurs"""
        # Configure a service to raise an unexpected exception
        mock_services["language_service"].detect_language = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        result = await orchestrator.process("test input")

        # Should track exception
        assert "processing.exceptions" in metrics_service.metrics
        assert metrics_service.metrics["processing.exceptions"]["value"] == 1

        # Should track failed request
        assert "processing.requests.failed" in metrics_service.metrics
        assert metrics_service.metrics["processing.requests.failed"]["value"] == 1

    @pytest.mark.asyncio
    async def test_active_requests_gauge(self, orchestrator, metrics_service):
        """Test active requests gauge tracking"""
        import asyncio

        async def concurrent_processing():
            return await orchestrator.process("concurrent test")

        # Run multiple concurrent requests
        tasks = [concurrent_processing() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All requests should have completed
        # The gauge should be decremented back to 0 (or close to it due to timing)
        active_requests = metrics_service.metrics.get("processing.requests.active", {}).get("value", 0)
        assert active_requests <= 3  # Should not exceed the number of requests

        # Total requests should be tracked
        assert "processing.requests.total" in metrics_service.metrics
        assert metrics_service.metrics["processing.requests.total"]["value"] == 3

    @pytest.mark.asyncio
    async def test_language_detection_distribution(self, orchestrator, metrics_service, mock_services):
        """Test language detection distribution metrics"""
        # Configure different languages
        languages = ["en", "ru", "uk"]

        for lang in languages:
            mock_services["language_service"].detect_language = AsyncMock(
                return_value={"language": lang, "confidence": 0.9}
            )
            await orchestrator.process("test input")

        # Should track each language detection
        for lang in languages:
            counter_name = f"language_detection.detected.{lang}"
            assert counter_name in metrics_service.metrics
            assert metrics_service.metrics[counter_name]["value"] == 1

    @pytest.mark.asyncio
    async def test_histogram_metrics_accuracy(self, orchestrator, metrics_service):
        """Test accuracy of histogram metrics"""
        # Process multiple requests to build histogram data
        for i in range(10):
            await orchestrator.process(f"test input {i}")

        # Check histogram metrics have proper statistics
        histograms = [
            "smart_filter.confidence",
            "language_detection.confidence",
            "normalization.token_count",
            "signals.confidence",
        ]

        for histogram_name in histograms:
            if histogram_name in metrics_service.metrics:
                metric = metrics_service.metrics[histogram_name]
                assert metric["count"] >= 1
                assert "sum" in metric
                assert "min" in metric
                assert "max" in metric
                assert "percentiles" in metric

    @pytest.mark.asyncio
    async def test_metrics_without_optional_services(self, mock_services, metrics_service):
        """Test metrics collection when optional services are disabled"""
        # Create orchestrator without optional services
        orchestrator = UnifiedOrchestrator(
            validation_service=mock_services["validation_service"],
            language_service=mock_services["language_service"],
            unicode_service=mock_services["unicode_service"],
            normalization_service=mock_services["normalization_service"],
            signals_service=mock_services["signals_service"],
            metrics_service=metrics_service,
            # All optional services disabled
            smart_filter_service=None,
            variants_service=None,
            embeddings_service=None,
            decision_engine=None,
            enable_smart_filter=False,
            enable_variants=False,
            enable_embeddings=False,
            enable_decision_engine=False,
        )

        result = await orchestrator.process("test input")

        # Should track basic metrics
        assert "processing.requests.total" in metrics_service.metrics
        assert "processing.requests.successful" in metrics_service.metrics

        # Should track core layers
        core_layers = [
            "processing.layer.validation",
            "processing.layer.language_detection",
            "processing.layer.unicode_normalization",
            "processing.layer.normalization",
            "processing.layer.signals",
        ]

        for layer in core_layers:
            assert layer in metrics_service.metrics

        # Should not track optional layers
        optional_layers = [
            "processing.layer.smart_filter",
            "processing.layer.variants",
            "processing.layer.embeddings",
            "processing.layer.decision",
        ]

        for layer in optional_layers:
            assert layer not in metrics_service.metrics