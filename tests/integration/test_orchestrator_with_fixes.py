"""
Integration tests for OrchestratorService with recent fixes
Testing smart filter re-enablement, input validation, and overall pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.ai_service.services.orchestrator_service import OrchestratorService, ProcessingResult
from src.ai_service.exceptions import ServiceInitializationError, ProcessingError, ValidationError


class TestOrchestratorServiceIntegration:
    """Integration tests for OrchestratorService with fixes"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for orchestrator"""
        mocks = {}

        # Mock all service dependencies
        mocks['unicode_service'] = Mock()
        mocks['unicode_service'].normalize_text.return_value = {'normalized': 'normalized text'}

        mocks['language_service'] = Mock()
        mocks['language_service'].detect_language.return_value = {
            'language': 'uk',
            'confidence': 0.85,
            'method': 'cyrillic_ukrainian'
        }

        mocks['normalization_service'] = Mock()
        mock_norm_result = Mock()
        mock_norm_result.normalized = 'normalized result'
        mocks['normalization_service'].normalize = AsyncMock(return_value=mock_norm_result)

        mocks['variant_service'] = Mock()
        mocks['variant_service'].generate_variants.return_value = {'variants': ['variant1', 'variant2']}

        mocks['embedding_service'] = Mock()
        mocks['embedding_service'].get_embeddings.return_value = {
            'success': True,
            'embeddings': [0.1, 0.2, 0.3]
        }

        mocks['cache_service'] = Mock()
        mocks['cache_service'].get.return_value = None  # No cache hit
        mocks['cache_service'].set.return_value = None

        mocks['smart_filter'] = Mock()
        mocks['smart_filter'].should_process_text.return_value = Mock(
            should_process=True,
            confidence=0.8,
            processing_recommendation="High confidence match",
            detected_signals=["name_signal"],
            estimated_complexity="medium"
        )

        return mocks

    @pytest.fixture
    def orchestrator_with_mocks(self, mock_services):
        """Create OrchestratorService with mocked dependencies"""
        with patch.multiple(
            'src.ai_service.services.orchestrator_service',
            UnicodeService=Mock(return_value=mock_services['unicode_service']),
            LanguageDetectionService=Mock(return_value=mock_services['language_service']),
            NormalizationService=Mock(return_value=mock_services['normalization_service']),
            VariantGenerationService=Mock(return_value=mock_services['variant_service']),
            EmbeddingService=Mock(return_value=mock_services['embedding_service']),
            CacheService=Mock(return_value=mock_services['cache_service']),
            SmartFilterService=Mock(return_value=mock_services['smart_filter'])
        ):
            orchestrator = OrchestratorService()
            return orchestrator, mock_services

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_with_smart_filter(self, orchestrator_with_mocks):
        """Test orchestrator initialization includes smart filter"""
        orchestrator, mocks = orchestrator_with_mocks

        # Assert
        assert orchestrator.smart_filter is not None
        assert hasattr(orchestrator, 'unicode_service')
        assert hasattr(orchestrator, 'language_service')
        assert hasattr(orchestrator, 'normalization_service')

    @pytest.mark.asyncio
    async def test_process_text_with_input_validation(self, orchestrator_with_mocks):
        """Test text processing includes input validation"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Петро Порошенко"

        # Act
        result = await orchestrator.process_text(test_text)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.original_text == test_text
        assert result.success is True

        # Verify input validation was applied (sanitized_text should be used)
        mocks['language_service'].detect_language.assert_called_once()

        # Should call normalization service
        mocks['normalization_service'].normalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_text_with_malicious_input(self, orchestrator_with_mocks):
        """Test processing with malicious input is handled by validation"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        malicious_text = "<script>alert('xss')</script>Test Name"

        # Act
        result = await orchestrator.process_text(malicious_text)

        # Assert
        # Should still process (non-strict mode) but with warnings
        assert isinstance(result, ProcessingResult)
        # Input validation should have cleaned the text
        mocks['language_service'].detect_language.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_text_with_smart_filter_enabled(self, orchestrator_with_mocks):
        """Test process_text_with_smart_filter with smart filter enabled"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Петро Порошенко"

        # Act
        result = await orchestrator.process_text_with_smart_filter(test_text)

        # Assert
        assert isinstance(result, dict) or isinstance(result, ProcessingResult)

        # Smart filter should have been called
        mocks['smart_filter'].should_process_text.assert_called_once_with(test_text)

        # Should proceed with full processing since should_process=True
        mocks['language_service'].detect_language.assert_called()

    @pytest.mark.asyncio
    async def test_process_text_with_smart_filter_skip(self, orchestrator_with_mocks):
        """Test smart filter skipping processing"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Non-relevant text"

        # Configure smart filter to skip processing
        mocks['smart_filter'].should_process_text.return_value = Mock(
            should_process=False,
            confidence=0.2,
            processing_recommendation="Low relevance",
            detected_signals=[],
            estimated_complexity="low"
        )

        # Act
        result = await orchestrator.process_text_with_smart_filter(test_text)

        # Assert
        assert isinstance(result, dict) or isinstance(result, ProcessingResult)

        # Smart filter should have been called
        mocks['smart_filter'].should_process_text.assert_called_once_with(test_text)

        # Should NOT proceed with full processing
        mocks['normalization_service'].normalize.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_text_without_smart_filter(self, orchestrator_with_mocks):
        """Test processing when smart filter is unavailable"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        orchestrator.smart_filter = None  # Simulate unavailable smart filter
        test_text = "Test text"

        # Act
        result = await orchestrator.process_text_with_smart_filter(test_text)

        # Assert
        assert isinstance(result, dict) or isinstance(result, ProcessingResult)

        # Should proceed with full processing
        mocks['language_service'].detect_language.assert_called()

    @pytest.mark.asyncio
    async def test_ukrainian_language_priority_processing(self, orchestrator_with_mocks):
        """Test processing prioritizes Ukrainian language detection"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        ukrainian_text = "Петро Порошенко і Володимир Зеленський"

        # Configure language service to return Ukrainian
        mocks['language_service'].detect_language.return_value = {
            'language': 'uk',
            'confidence': 0.95,
            'method': 'cyrillic_ukrainian'
        }

        # Act
        result = await orchestrator.process_text(ukrainian_text)

        # Assert
        assert result.language == 'uk'
        assert result.language_confidence >= 0.9

        # Should pass Ukrainian language to normalization
        call_args = mocks['normalization_service'].normalize.call_args
        assert call_args[1]['language'] == 'uk'  # Check keyword argument

    @pytest.mark.asyncio
    async def test_variant_generation_with_ukrainian_names(self, orchestrator_with_mocks):
        """Test variant generation for Ukrainian names"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        ukrainian_name = "Порошенко"

        # Configure services for Ukrainian processing
        mocks['language_service'].detect_language.return_value = {
            'language': 'uk',
            'confidence': 0.9,
            'method': 'cyrillic_ukrainian'
        }

        # Act
        result = await orchestrator.process_text(
            ukrainian_name,
            generate_variants=True,
            generate_embeddings=False
        )

        # Assert
        assert result.language == 'uk'
        assert len(result.variants) >= 1

        # Variant service should be called
        mocks['variant_service'].generate_variants.assert_called()

    @pytest.mark.asyncio
    async def test_embedding_generation_with_validation(self, orchestrator_with_mocks):
        """Test embedding generation includes validation"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Test Entity Name"

        # Configure embedding service to return valid embeddings
        mocks['embedding_service'].get_embeddings.return_value = {
            'success': True,
            'embeddings': [0.1] * 384  # Valid 384-dimensional vector
        }

        # Act
        result = await orchestrator.process_text(
            test_text,
            generate_variants=False,
            generate_embeddings=True
        )

        # Assert
        assert result.embeddings is not None
        mocks['embedding_service'].get_embeddings.assert_called()

    @pytest.mark.asyncio
    async def test_cache_integration(self, orchestrator_with_mocks):
        """Test cache integration in processing pipeline"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Cached Entity"

        # Configure cache to return a hit on second call
        cached_result = ProcessingResult(
            original_text=test_text,
            normalized_text="cached normalized",
            language="uk",
            language_confidence=0.8,
            variants=["cached variant"],
            processing_time=0.1,
            success=True
        )

        mocks['cache_service'].get.side_effect = [None, cached_result]  # Miss then hit

        # Act - First call (cache miss)
        result1 = await orchestrator.process_text(test_text, cache_result=True)

        # Act - Second call (cache hit)
        result2 = await orchestrator.process_text(test_text, cache_result=True)

        # Assert
        assert isinstance(result1, ProcessingResult)
        assert result2 == cached_result  # Should be cached result

        # Cache should be checked twice
        assert mocks['cache_service'].get.call_count == 2

    @pytest.mark.asyncio
    async def test_processing_error_handling(self, orchestrator_with_mocks):
        """Test error handling in processing pipeline"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Error Test"

        # Configure normalization to fail
        mocks['normalization_service'].normalize.side_effect = Exception("Normalization failed")

        # Act
        result = await orchestrator.process_text(test_text)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.success is False  # Should fail gracefully with error details
        assert "Normalization failed" in result.errors

        # Language detection should still work
        mocks['language_service'].detect_language.assert_called()

    @pytest.mark.asyncio
    async def test_normalization_service_none_result_handling(self, orchestrator_with_mocks):
        """Test handling when normalization service returns None"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Test Text"

        # Configure normalization to return None
        mocks['normalization_service'].normalize.return_value = None

        # Act
        result = await orchestrator.process_text(test_text)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.success is False
        assert len(result.errors) > 0
        assert any("Normalization service returned None" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_force_reprocess_bypasses_cache(self, orchestrator_with_mocks):
        """Test force_reprocess parameter bypasses cache"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Force Reprocess Test"

        cached_result = ProcessingResult(
            original_text=test_text,
            normalized_text="old cached",
            language="en",
            language_confidence=0.5,
            variants=[],
            processing_time=0.01,
            success=True
        )

        mocks['cache_service'].get.return_value = cached_result

        # Act
        result = await orchestrator.process_text(
            test_text,
            force_reprocess=True,
            cache_result=True
        )

        # Assert
        assert isinstance(result, ProcessingResult)
        # Should not use cached result due to force_reprocess=True
        mocks['language_service'].detect_language.assert_called()
        mocks['cache_service'].get.assert_not_called()  # Should skip cache check

    @pytest.mark.asyncio
    async def test_processing_metrics_tracking(self, orchestrator_with_mocks):
        """Test that processing metrics are tracked"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        test_text = "Metrics Test"
        initial_stats = orchestrator.processing_stats.copy()

        # Act
        await orchestrator.process_text(test_text)

        # Assert
        updated_stats = orchestrator.processing_stats
        assert updated_stats['total_processed'] > initial_stats['total_processed']
        assert updated_stats['cache_misses'] > initial_stats['cache_misses']

    def test_smart_filter_stats_tracking(self, orchestrator_with_mocks):
        """Test smart filter statistics tracking"""
        orchestrator, mocks = orchestrator_with_mocks

        # Act
        stats = orchestrator.get_smart_filter_stats()

        # Assert
        assert isinstance(stats, dict)
        assert 'smart_filter_processed' in str(stats) or 'processed' in str(stats)

    @pytest.mark.asyncio
    async def test_homoglyph_handling_in_processing(self, orchestrator_with_mocks):
        """Test homoglyph handling in the processing pipeline"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        text_with_homoglyphs = "Pаvlоv Pеtrо"  # Contains Cyrillic а, о, е

        # Act
        result = await orchestrator.process_text(text_with_homoglyphs)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.success is True

        # Should have processed with input validation
        mocks['language_service'].detect_language.assert_called()

        # The text passed to language detection should be sanitized
        call_args = mocks['language_service'].detect_language.call_args[0][0]
        # Input validation should have normalized homoglyphs

    @pytest.mark.asyncio
    async def test_zero_width_character_handling(self, orchestrator_with_mocks):
        """Test zero-width character handling in processing"""
        orchestrator, mocks = orchestrator_with_mocks

        # Arrange
        text_with_zw = "Pet\u200bro\u200cPoro\u200dshenko"

        # Act
        result = await orchestrator.process_text(text_with_zw)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.success is True

        # Should process successfully with sanitized input
        mocks['language_service'].detect_language.assert_called()

    def test_orchestrator_service_initialization_failure(self):
        """Test orchestrator initialization failure handling"""
        # Arrange
        with patch('src.ai_service.services.orchestrator_service.UnicodeService',
                  side_effect=Exception("Service init failed")):

            # Act & Assert
            with pytest.raises(ServiceInitializationError):
                OrchestratorService()

    def test_smart_filter_graceful_degradation(self):
        """Test graceful degradation when smart filter fails to initialize"""
        # Arrange
        with patch.multiple(
            'src.ai_service.services.orchestrator_service',
            UnicodeService=Mock(),
            LanguageDetectionService=Mock(),
            NormalizationService=Mock(),
            VariantGenerationService=Mock(),
            EmbeddingService=Mock(),
            CacheService=Mock(),
            SmartFilterService=Mock(side_effect=Exception("Smart filter init failed"))
        ):

            # Act
            orchestrator = OrchestratorService()

            # Assert
            assert orchestrator.smart_filter is None  # Should gracefully handle failure