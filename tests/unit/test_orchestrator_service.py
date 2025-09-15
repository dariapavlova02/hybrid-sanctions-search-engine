
"""
Unit tests for UnifiedOrchestrator - Updated to match current implementation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.contracts.base_contracts import UnifiedProcessingResult, TokenTrace, SignalsResult


class TestUnifiedOrchestrator:
    """Tests for UnifiedOrchestrator"""
    
    @pytest.fixture
    def orchestrator_service(self):
        """Create a UnifiedOrchestrator instance for testing"""
        # Mock all required services - use AsyncMock for async methods
        validation_service = Mock()
        validation_service.validate_and_sanitize = AsyncMock()
        
        language_service = Mock()
        language_service.detect_language_config_driven = Mock()
        
        unicode_service = Mock()
        unicode_service.normalize_text = Mock()
        
        normalization_service = Mock()
        normalization_service.normalize_async = AsyncMock()
        
        signals_service = Mock()
        signals_service.extract_signals = AsyncMock()
        
        # Mock optional services
        smart_filter_service = Mock()
        smart_filter_service.should_process = AsyncMock()
        
        variants_service = Mock()
        variants_service.generate_variants = AsyncMock()
        
        embeddings_service = Mock()
        embeddings_service.generate_embeddings = AsyncMock()
        
        decision_engine = Mock()
        decision_engine.decide = Mock()
        
        return UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
            smart_filter_service=smart_filter_service,
            variants_service=variants_service,
            embeddings_service=embeddings_service,
            decision_engine=decision_engine,
            enable_smart_filter=True,
            enable_variants=True,
            enable_embeddings=True,
            enable_decision_engine=True,
            allow_smart_filter_skip=True
        )
    
    @pytest.mark.asyncio
    async def test_process_basic_functionality(self, orchestrator_service):
        """Test basic process functionality"""
        # Arrange
        test_text = "Test text"
        
        # Setup mocks
        orchestrator_service.validation_service.validate_and_sanitize.return_value = {'valid': True, 'errors': [], 'should_process': True}
        
        # Mock smart filter result
        mock_filter_result = Mock()
        mock_filter_result.should_process = True
        mock_filter_result.confidence = 0.8
        mock_filter_result.classification = 'normal'
        mock_filter_result.detected_signals = []
        mock_filter_result.details = {}
        orchestrator_service.smart_filter_service.should_process.return_value = mock_filter_result
        
        # Mock language result
        mock_lang_result = Mock()
        mock_lang_result.language = 'en'
        mock_lang_result.confidence = 0.9
        orchestrator_service.language_service.detect_language_config_driven.return_value = mock_lang_result
        orchestrator_service.unicode_service.normalize_text.return_value = {'normalized_text': 'test text'}
        
        # Mock normalization result
        mock_normalize_result = Mock()
        mock_normalize_result.normalized = 'test text'
        mock_normalize_result.tokens = ['test', 'text']
        mock_normalize_result.trace = [TokenTrace(token='test', role='given', rule='capitalize', output='test')]
        mock_normalize_result.success = True
        orchestrator_service.normalization_service.normalize_async.return_value = mock_normalize_result
        
        # Mock signals result
        mock_signals_result = Mock()
        mock_signals_result.persons = []
        mock_signals_result.organizations = []
        mock_signals_result.confidence = 0.5
        orchestrator_service.signals_service.extract_signals.return_value = mock_signals_result
        
        orchestrator_service.variants_service.generate_variants.return_value = ['test text', 'test']
        orchestrator_service.embeddings_service.generate_embeddings.return_value = [0.1, 0.2, 0.3]
        
        # Mock decision result
        mock_decision_result = Mock()
        mock_decision_result.risk = Mock()
        mock_decision_result.risk.value = 'low'
        mock_decision_result.score = 0.8
        orchestrator_service.decision_engine.decide.return_value = mock_decision_result
        
        # Act
        result = await orchestrator_service.process(test_text)
        
        # Assert
        assert isinstance(result, UnifiedProcessingResult)
        assert result.success is True
        assert result.original_text == test_text
        assert result.normalized_text == 'test text'
        assert result.language == 'en'
        assert result.language_confidence == 0.9
        assert result.tokens == ['test', 'text']
        assert len(result.trace) > 0
        assert result.variants == ['test text', 'test']
        assert result.embeddings == [0.1, 0.2, 0.3]
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_process_with_smart_filter_skip(self, orchestrator_service):
        """Test process when smart filter decides to skip"""
        # Arrange
        test_text = "Test text"
        
        # Setup mocks
        orchestrator_service.validation_service.validate_and_sanitize.return_value = {'valid': True, 'errors': [], 'should_process': True}
        
        # Mock smart filter result - should skip
        mock_filter_result = Mock()
        mock_filter_result.should_process = False
        mock_filter_result.confidence = 0.8
        mock_filter_result.classification = 'skip'
        mock_filter_result.detected_signals = []
        mock_filter_result.details = {}
        orchestrator_service.smart_filter_service.should_process.return_value = mock_filter_result
        
        # Act
        result = await orchestrator_service.process(test_text)
        
        # Assert
        assert isinstance(result, UnifiedProcessingResult)
        assert result.success is True
        assert result.original_text == test_text
        # When skipped, should return minimal result with empty tokens and trace
        assert result.tokens == []
        assert result.trace == []
        assert result.normalized_text == test_text
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_process_with_validation_error(self, orchestrator_service):
        """Test process with validation error"""
        # Arrange
        test_text = "Invalid text"
        
        # Setup mocks
        orchestrator_service.validation_service.validate_and_sanitize.return_value = {'valid': False, 'errors': ['Invalid input'], 'should_process': False}
        
        # Act
        result = await orchestrator_service.process(test_text)
        
        # Assert
        assert isinstance(result, UnifiedProcessingResult)
        assert result.success is False
        assert 'Input validation failed' in result.errors
    
    @pytest.mark.asyncio
    async def test_process_with_language_detection_failure(self, orchestrator_service):
        """Test process when language detection fails"""
        # Arrange
        test_text = "Test text"
        
        # Setup mocks
        orchestrator_service.validation_service.validate_and_sanitize.return_value = {'valid': True, 'errors': []}
        orchestrator_service.smart_filter_service.should_skip.return_value = False
        orchestrator_service.language_service.detect_language.side_effect = Exception("Language detection failed")
        
        # Act
        result = await orchestrator_service.process(test_text)
        
        # Assert
        assert isinstance(result, UnifiedProcessingResult)
        # Should handle the error gracefully
    
    @pytest.mark.asyncio
    async def test_process_with_normalization_failure(self, orchestrator_service):
        """Test process when normalization fails"""
        # Arrange
        test_text = "Test text"
        
        # Setup mocks
        orchestrator_service.validation_service.validate_and_sanitize.return_value = {'valid': True, 'errors': []}
        orchestrator_service.smart_filter_service.should_skip.return_value = False
        orchestrator_service.language_service.detect_language.return_value = {'language': 'en', 'confidence': 0.9}
        orchestrator_service.unicode_service.normalize_text.return_value = {'normalized': 'test text'}
        orchestrator_service.normalization_service.normalize.side_effect = Exception("Normalization failed")
        
        # Act
        result = await orchestrator_service.process(test_text)
        
        # Assert
        assert isinstance(result, UnifiedProcessingResult)
        # Should handle the error gracefully
    
    def test_orchestrator_initialization(self, orchestrator_service):
        """Test orchestrator initialization"""
        # Assert
        assert orchestrator_service.validation_service is not None
        assert orchestrator_service.language_service is not None
        assert orchestrator_service.unicode_service is not None
        assert orchestrator_service.normalization_service is not None
        assert orchestrator_service.signals_service is not None
        assert orchestrator_service.smart_filter_service is not None
        assert orchestrator_service.variants_service is not None
        assert orchestrator_service.embeddings_service is not None
        assert orchestrator_service.decision_engine is not None
        
        # Check configuration flags
        assert orchestrator_service.enable_smart_filter is True
        assert orchestrator_service.enable_variants is True
        assert orchestrator_service.enable_embeddings is True
        assert orchestrator_service.enable_decision_engine is True
    
    def test_orchestrator_without_optional_services(self):
        """Test orchestrator initialization without optional services"""
        # Mock required services
        validation_service = Mock()
        language_service = Mock()
        unicode_service = Mock()
        normalization_service = Mock()
        signals_service = Mock()
        
        # Create orchestrator without optional services
        orchestrator = UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
            smart_filter_service=None,
            variants_service=None,
            embeddings_service=None,
            decision_engine=None
        )
        
        # Assert
        assert orchestrator.smart_filter_service is None
        assert orchestrator.variants_service is None
        assert orchestrator.embeddings_service is None
        assert orchestrator.decision_engine is None
        
        # Check configuration flags should be False when services are None
        assert orchestrator.enable_smart_filter is False
        assert orchestrator.enable_variants is False
        assert orchestrator.enable_embeddings is False
        assert orchestrator.enable_decision_engine is False
