"""
Pytest configuration for AI service tests
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Suppress warnings for cleaner test output
# pytest_plugins = ['pytest_warnings']  # Removed - plugin not available


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory path"""
    return Path(__file__).parent / 'data'


@pytest.fixture(scope="session")
def sample_texts():
    """Provide sample texts for testing"""
    return {
        'ukrainian': 'Привіт світ! Це тестовий текст українською мовою.',
        'russian': 'Привет мир! Это тестовый текст на русском языке.',
        'english': 'Hello world! This is a test text in English.',
        'mixed': 'Hello світ! Привет world!'
    }


@pytest.fixture(scope="session")
def sample_names():
    """Provide sample names for testing"""
    return {
        'ukrainian': ['Петро', 'Дарія', 'Володимир', 'Олена'],
        'russian': ['Сергей', 'Мария', 'Владимир', 'Анна'],
        'english': ['John', 'Mary', 'William', 'Elizabeth']
    }


@pytest.fixture(scope="function")
def mock_services():
    """Provide mocked services for testing"""
    from unittest.mock import Mock
    
    return {
        'language_service': Mock(),
        'normalization_service': Mock(),
        'variant_service': Mock(),
        'embedding_service': Mock(),
        'cache_service': Mock()
    }


@pytest.fixture(scope="function")
def orchestrator_service():
    """
    Provides a clean, isolated instance of OrchestratorService for each test.
    
    This ensures that each test gets a fresh instance with clean cache and statistics,
    preventing test contamination. Mocks heavy dependencies to avoid NLTK issues.
    """
    from unittest.mock import patch, MagicMock
    
    # Mock heavy dependencies to avoid initialization issues
    with patch('src.ai_service.data.dicts.stopwords.STOP_ALL') as mock_stopwords:
        
        # Configure mocks
        mock_stopwords.return_value = ['the', 'a', 'an']
        
        from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator as OrchestratorService
        from unittest.mock import Mock
        
        # Create mock services for required dependencies
        from unittest.mock import AsyncMock, Mock
        
        mock_validation_service = AsyncMock()
        mock_language_service = Mock()
        mock_unicode_service = Mock()
        mock_normalization_service = AsyncMock()
        mock_signals_service = AsyncMock()
        
        # Configure mock responses
        async def mock_validation(text):
            return {"is_valid": True, "sanitized_text": text}
        
        def mock_language_config_driven(text, config=None):
            from src.ai_service.utils.types import LanguageDetectionResult
            return LanguageDetectionResult(language="uk", confidence=0.9, details={})
        
        def mock_unicode_normalize_text(text, aggressive=False):
            return {"normalized_text": text, "original_text": text}
        
        def mock_unicode_normalize_unicode(text):
            return text
        
        async def mock_normalization(text, **kwargs):
            return type('obj', (object,), {
                'normalized': text,
                'tokens': text.split(),
                'trace': [],
                'success': True,
                'errors': []
            })()
        
        async def mock_signals(text, normalization_result, language, **kwargs):
            return type('obj', (object,), {
                'persons': [],
                'organizations': [],
                'extras': type('obj', (object,), {'dates': [], 'amounts': []})(),
                'confidence': 0.0
            })()
        
        mock_validation_service.validate_and_sanitize.side_effect = mock_validation
        mock_language_service.detect_language_config_driven.side_effect = mock_language_config_driven
        mock_unicode_service.normalize_text.side_effect = mock_unicode_normalize_text
        mock_unicode_service.normalize_unicode.side_effect = mock_unicode_normalize_unicode
        mock_normalization_service.normalize_async.side_effect = mock_normalization
        mock_signals_service.extract_signals.side_effect = mock_signals
        
        # Create mock for variants service
        mock_variants_service = AsyncMock()
        mock_variants_service.generate_variants.return_value = [
            "Gnatuk Abdulaeva Zhorzha Rashida",
            "Gnatuk Abdulaev Zhorzha Rashid",
            "Gnatuk Abdulaev Zhorzha Rashidovich",
            "Gnatuk Abdulaev Zhorzha Rashidovich Freedom",
            "Jean-Baptiste Müller Олександр Петренко-Сміт",
            "Jean-Baptiste Muller Олександр Петренко-Сміт",
            "Jean-Baptiste Muller Олександр Петренко-Смит",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Straße",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse"
        ]
        
        # Create mock cache service
        from src.ai_service.core.cache_service import CacheService
        mock_cache_service = CacheService(max_size=100, default_ttl=60)
        
        # Create mock embeddings service
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [0.1, 0.2, 0.3]
        mock_embeddings_service.find_similar_texts.return_value = []
        
        # Use small values for tests to speed them up
        service = OrchestratorService(
            validation_service=mock_validation_service,
            language_service=mock_language_service,
            unicode_service=mock_unicode_service,
            normalization_service=mock_normalization_service,
            signals_service=mock_signals_service,
            variants_service=mock_variants_service,
            embeddings_service=mock_embeddings_service
        )
        
        # Set the cache service for legacy compatibility
        service.cache_service = mock_cache_service
        
        # Set other legacy services for compatibility
        service.pattern_service = Mock()
        service.template_builder = Mock()
        
        # Ensure clean state before test
        # UnifiedOrchestrator doesn't have reset_stats/clear_cache methods
        
        yield service
        
        # Clean up after test to prevent state leakage
        # UnifiedOrchestrator doesn't have clear_cache/reset_stats methods


@pytest.fixture(scope="function")
def language_detection_service():
    """Provides a clean instance of LanguageDetectionService for each test"""
    from src.ai_service.layers.language.language_detection_service import LanguageDetectionService
    return LanguageDetectionService()


@pytest.fixture(scope="function")
def advanced_normalization_service():
    """Provides a clean instance of NormalizationService for each test"""
    from src.ai_service.layers.normalization.normalization_service import NormalizationService
    return NormalizationService()


@pytest.fixture(scope="function")
def variant_generation_service():
    """Provides a clean instance of VariantGenerationService for each test"""
    from src.ai_service.layers.variants.variant_generation_service import VariantGenerationService
    return VariantGenerationService()


@pytest.fixture(scope="function")
def unicode_service():
    """Provides a clean instance of UnicodeService for each test"""
    from src.ai_service.layers.unicode.unicode_service import UnicodeService
    return UnicodeService()


@pytest.fixture(scope="function")
def pattern_service():
    """Provides a clean instance of UnifiedPatternService for each test"""
    from src.ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService
    return UnifiedPatternService()


@pytest.fixture(scope="function")
def cache_service():
    """Provides a clean instance of CacheService for each test"""
    from src.ai_service.core.cache_service import CacheService
    service = CacheService(max_size=3, default_ttl=5)  # Small size and TTL for tests
    yield service
    # Clean up after test
    service.clear()


@pytest.fixture(scope="function")
def template_builder():
    """Provides a clean instance of TemplateBuilder for each test"""
    from src.ai_service.layers.variants.template_builder import TemplateBuilder
    return TemplateBuilder()
