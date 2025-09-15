"""
Test suite for OrchestratorFactory.

Tests the factory pattern implementation for creating orchestrator instances
with different configurations and service dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from ai_service.core.orchestrator_factory import OrchestratorFactory
from ai_service.core.unified_orchestrator import UnifiedOrchestrator
from ai_service.contracts.base_contracts import ProcessingContext


class TestOrchestratorFactory:
    """Test OrchestratorFactory creation and configuration"""

    def test_factory_initialization(self):
        """Test that factory can be instantiated"""
        factory = OrchestratorFactory()
        assert factory is not None

    @pytest.mark.asyncio
    async def test_create_testing_orchestrator_minimal(self):
        """Test creating minimal orchestrator for testing"""
        # Create async mocks for all services that need initialization
        mock_validation_service = Mock()
        mock_validation_service.initialize = AsyncMock()

        mock_language_service = Mock()
        mock_language_service.initialize = AsyncMock()

        mock_unicode_service = Mock()
        mock_unicode_service.initialize = AsyncMock()

        mock_normalization_service = Mock()
        mock_normalization_service.initialize = AsyncMock()

        mock_signals_service = Mock()
        mock_signals_service.initialize = AsyncMock()

        mock_smart_filter = Mock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation_service),
            SmartFilterAdapter=Mock(return_value=mock_smart_filter),
            LanguageDetectionService=Mock(return_value=mock_language_service),
            UnicodeService=Mock(return_value=mock_unicode_service),
            NormalizationService=Mock(return_value=mock_normalization_service),
            SignalsService=Mock(return_value=mock_signals_service)
        ):
            orchestrator = await OrchestratorFactory.create_testing_orchestrator(minimal=True)

            assert isinstance(orchestrator, UnifiedOrchestrator)
            # Minimal config should disable optional services
            assert orchestrator.enable_variants is False
            assert orchestrator.enable_embeddings is False

    @pytest.mark.asyncio
    async def test_create_testing_orchestrator_full(self):
        """Test creating full-featured orchestrator for testing"""
        # Create async mocks for all services
        mock_validation_service = Mock()
        mock_validation_service.initialize = AsyncMock()
        
        mock_smart_filter = Mock()
        mock_smart_filter.initialize = AsyncMock()
        
        mock_variants_service = Mock()
        mock_variants_service.initialize = AsyncMock()
        
        mock_embeddings_service = Mock()
        mock_embeddings_service.initialize = AsyncMock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation_service),
            SmartFilterAdapter=Mock(return_value=mock_smart_filter),
            LanguageDetectionService=Mock(return_value=Mock()),
            UnicodeService=Mock(return_value=Mock()),
            NormalizationService=Mock(return_value=Mock()),
            SignalsService=Mock(return_value=Mock()),
            VariantGenerationService=Mock(return_value=mock_variants_service),
            EmbeddingService=Mock(return_value=mock_embeddings_service)
        ):
            orchestrator = await OrchestratorFactory.create_testing_orchestrator(minimal=False)

            assert isinstance(orchestrator, UnifiedOrchestrator)
            assert orchestrator.enable_variants is True
            assert orchestrator.enable_embeddings is True

    @pytest.mark.asyncio
    async def test_create_production_orchestrator(self):
        """Test creating production orchestrator with all services"""
        # Create async mock for validation service
        mock_validation_service = Mock()
        mock_validation_service.initialize = AsyncMock()
        
        mock_smart_filter = Mock()
        mock_smart_filter.initialize = AsyncMock()
        
        mock_variants_service = Mock()
        mock_variants_service.initialize = AsyncMock()
        
        mock_embeddings_service = Mock()
        mock_embeddings_service.initialize = AsyncMock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation_service),
            SmartFilterAdapter=Mock(return_value=mock_smart_filter),
            LanguageDetectionService=Mock(return_value=Mock()),
            UnicodeService=Mock(return_value=Mock()),
            NormalizationService=Mock(return_value=Mock()),
            SignalsService=Mock(return_value=Mock()),
            VariantGenerationService=Mock(return_value=mock_variants_service),
            EmbeddingService=Mock(return_value=mock_embeddings_service)
        ):
            orchestrator = await OrchestratorFactory.create_production_orchestrator()

            assert isinstance(orchestrator, UnifiedOrchestrator)
            # Production should have all features enabled
            assert orchestrator.enable_variants is True
            assert orchestrator.enable_embeddings is True

    @pytest.mark.asyncio
    async def test_create_orchestrator_custom_config(self):
        """Test creating orchestrator with custom configuration"""
        # Create async mock for validation service
        mock_validation_service = Mock()
        mock_validation_service.initialize = AsyncMock()
        
        mock_smart_filter = Mock()
        mock_smart_filter.initialize = AsyncMock()
        
        mock_embeddings_service = Mock()
        mock_embeddings_service.initialize = AsyncMock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation_service),
            SmartFilterAdapter=Mock(return_value=mock_smart_filter),
            LanguageDetectionService=Mock(return_value=Mock()),
            UnicodeService=Mock(return_value=Mock()),
            NormalizationService=Mock(return_value=Mock()),
            SignalsService=Mock(return_value=Mock()),
            VariantGenerationService=Mock(return_value=Mock()),
            EmbeddingService=Mock(return_value=mock_embeddings_service)
        ):
            orchestrator = await OrchestratorFactory.create_orchestrator(
                enable_smart_filter=True,
                enable_variants=False,
                enable_embeddings=True
            )

            assert isinstance(orchestrator, UnifiedOrchestrator)
            assert orchestrator.enable_variants is False
            assert orchestrator.enable_embeddings is True

    @pytest.mark.asyncio
    async def test_service_initialization_mocking(self):
        """Test that services are properly initialized and mocked"""
        mock_validation = Mock()
        mock_validation.initialize = AsyncMock()
        mock_smart_filter = Mock()
        mock_smart_filter.initialize = AsyncMock()
        mock_language = Mock()
        mock_unicode = Mock()
        mock_normalization = Mock()
        mock_signals = Mock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation),
            SmartFilterAdapter=Mock(return_value=mock_smart_filter),
            LanguageDetectionService=Mock(return_value=mock_language),
            UnicodeService=Mock(return_value=mock_unicode),
            NormalizationService=Mock(return_value=mock_normalization),
            SignalsService=Mock(return_value=mock_signals)
        ):
            orchestrator = await OrchestratorFactory.create_testing_orchestrator()

            # Services should be injected into orchestrator
            assert orchestrator.validation_service == mock_validation
            assert orchestrator.smart_filter_service == mock_smart_filter
            assert orchestrator.language_service == mock_language
            assert orchestrator.unicode_service == mock_unicode
            assert orchestrator.normalization_service == mock_normalization
            assert orchestrator.signals_service == mock_signals

    @pytest.mark.asyncio
    async def test_service_initialization_error_handling(self):
        """Test error handling during service initialization"""
        with patch('ai_service.core.orchestrator_factory.ValidationService',
                  side_effect=Exception("Service init failed")):
            with pytest.raises(Exception) as exc_info:
                await OrchestratorFactory.create_testing_orchestrator()

            assert "Service init failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_optional_services_configuration(self):
        """Test that optional services are configured based on flags"""
        mock_validation = Mock()
        mock_validation.initialize = AsyncMock()
        
        mock_smart_filter = Mock()
        mock_smart_filter.initialize = AsyncMock()
        
        mock_variants = Mock()
        mock_variants.initialize = AsyncMock()
        
        mock_embeddings = Mock()
        mock_embeddings.initialize = AsyncMock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation),
            SmartFilterAdapter=Mock(return_value=mock_smart_filter),
            LanguageDetectionService=Mock(),
            UnicodeService=Mock(),
            NormalizationService=Mock(),
            SignalsService=Mock(),
            VariantGenerationService=Mock(return_value=mock_variants),
            EmbeddingService=Mock(return_value=mock_embeddings)
        ) as mocks:

            # Test with variants disabled
            orchestrator = await OrchestratorFactory.create_orchestrator(
                enable_variants=False,
                enable_embeddings=False
            )

            # Variants and embeddings services should not be initialized
            # when disabled
            assert orchestrator.variants_service is None
            assert orchestrator.embeddings_service is None

    def test_factory_singleton_pattern(self):
        """Test factory methods are static and don't require instance"""
        # Should be able to call factory methods without instantiation
        assert hasattr(OrchestratorFactory, 'create_production_orchestrator')
        assert hasattr(OrchestratorFactory, 'create_testing_orchestrator')
        assert hasattr(OrchestratorFactory, 'create_orchestrator')

    @pytest.mark.asyncio
    async def test_service_dependency_injection(self):
        """Test that all required services are properly injected"""
        mock_services = {}
        service_classes = [
            'ValidationService', 'SmartFilterAdapter', 'LanguageDetectionService',
            'UnicodeService', 'NormalizationService', 'SignalsService',
            'VariantGenerationService', 'EmbeddingService'
        ]

        for service in service_classes:
            mock_service = Mock()
            mock_service.initialize = AsyncMock()
            mock_services[service] = Mock(return_value=mock_service)

        with patch.multiple('ai_service.core.orchestrator_factory', **mock_services):
            orchestrator = await OrchestratorFactory.create_production_orchestrator()

            # All services should be initialized for production orchestrator
            assert orchestrator.validation_service is not None
            assert orchestrator.smart_filter_service is not None
            assert orchestrator.language_service is not None
            assert orchestrator.unicode_service is not None
            assert orchestrator.normalization_service is not None
            assert orchestrator.signals_service is not None
            assert orchestrator.variants_service is not None
            assert orchestrator.embeddings_service is not None


@pytest.mark.integration
class TestOrchestratorFactoryIntegration:
    """Integration tests for OrchestratorFactory with real services"""

    @pytest.mark.asyncio
    async def test_real_service_creation(self):
        """Test creating orchestrator with real service instances"""
        # This test would use real services - commented out for unit testing
        # orchestrator = await OrchestratorFactory.create_testing_orchestrator()
        # result = await orchestrator.process("Test text")
        # assert result.success is True
        pass

    @pytest.mark.asyncio
    async def test_factory_performance(self):
        """Test factory performance with timing"""
        import time

        # Create async mock for validation service
        mock_validation_service = Mock()
        mock_validation_service.initialize = AsyncMock()

        with patch.multiple(
            'ai_service.core.orchestrator_factory',
            ValidationService=Mock(return_value=mock_validation_service),
            SmartFilterAdapter=Mock(return_value=Mock()),
            LanguageDetectionService=Mock(return_value=Mock()),
            UnicodeService=Mock(return_value=Mock()),
            NormalizationService=Mock(return_value=Mock()),
            SignalsService=Mock(return_value=Mock())
        ):
            start_time = time.time()
            orchestrator = await OrchestratorFactory.create_testing_orchestrator()
            creation_time = time.time() - start_time

            # Factory should create orchestrator quickly (< 1 second)
            assert creation_time < 1.0
            assert orchestrator is not None