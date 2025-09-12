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
    with patch('src.ai_service.services.normalization_service.stopwords') as mock_stopwords, \
         patch('src.ai_service.services.normalization_service.spacy') as mock_spacy, \
         patch('src.ai_service.services.advanced_normalization_service.spacy') as mock_adv_spacy, \
         patch('src.ai_service.services.advanced_normalization_service.MorphAnalyzer') as mock_morph:
        
        # Configure mocks
        mock_stopwords.words.return_value = ['the', 'a', 'an']
        mock_spacy.load.return_value = MagicMock()
        mock_adv_spacy.load.return_value = MagicMock()
        mock_morph.return_value = MagicMock()
        
        from src.ai_service.services.orchestrator_service import OrchestratorService
        
        # Use small values for tests to speed them up
        service = OrchestratorService(cache_size=100, default_ttl=60)
        
        # Ensure clean state before test
        service.reset_stats()
        service.clear_cache()
        
        yield service
        
        # Clean up after test to prevent state leakage
        service.clear_cache()
        service.reset_stats()


@pytest.fixture(scope="function")
def language_detection_service():
    """Provides a clean instance of LanguageDetectionService for each test"""
    from src.ai_service.services.language_detection_service import LanguageDetectionService
    return LanguageDetectionService()


@pytest.fixture(scope="function")
def advanced_normalization_service():
    """Provides a clean instance of AdvancedNormalizationService for each test"""
    from src.ai_service.services.advanced_normalization_service import AdvancedNormalizationService
    return AdvancedNormalizationService()


@pytest.fixture(scope="function")
def variant_generation_service():
    """Provides a clean instance of VariantGenerationService for each test"""
    from src.ai_service.services.variant_generation_service import VariantGenerationService
    return VariantGenerationService()


@pytest.fixture(scope="function")
def unicode_service():
    """Provides a clean instance of UnicodeService for each test"""
    from src.ai_service.services.unicode_service import UnicodeService
    return UnicodeService()


@pytest.fixture(scope="function")
def pattern_service():
    """Provides a clean instance of PatternService for each test"""
    from src.ai_service.services.pattern_service import PatternService
    return PatternService()


@pytest.fixture(scope="function")
def cache_service():
    """Provides a clean instance of CacheService for each test"""
    from src.ai_service.services.cache_service import CacheService
    service = CacheService(max_size=3, default_ttl=5)  # Small size and TTL for tests
    yield service
    # Clean up after test
    service.clear()


@pytest.fixture(scope="function")
def template_builder():
    """Provides a clean instance of TemplateBuilder for each test"""
    from src.ai_service.services.template_builder import TemplateBuilder
    return TemplateBuilder()
