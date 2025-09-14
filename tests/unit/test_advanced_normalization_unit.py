"""
Unit tests for NormalizationService using pytest fixtures
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Mock heavy dependencies before importing
with patch('spacy.load') as mock_spacy, \
     patch('pymorphy3.MorphAnalyzer') as mock_morph, \
     patch('nltk.corpus.stopwords') as mock_stopwords:
    
    # Configure mocks
    mock_spacy.return_value = MagicMock()
    mock_morph.return_value = MagicMock()
    mock_stopwords.words.return_value = ['the', 'a', 'an']
    
    # Now import our module (it will use the mocked dependencies)
    from ai_service.layers.normalization.normalization_service import NormalizationService


class TestNormalizationService:
    """Test cases for NormalizationService"""

    @pytest.fixture(autouse=True)
    def setup_service(self):
        """Set up test fixtures before each test method"""
        # Create a NormalizationService instance
        self.service = NormalizationService()
        
        # Mock the slow dependencies
        self._mock_slow_dependencies()

    def _mock_slow_dependencies(self):
        """Mock all slow dependencies to avoid loading real models"""
        # Mock UkrainianMorphologyAnalyzer
        self.service.uk_morphology = MagicMock()
        
        # Mock spacy models
        self.service.nlp_models = {
            'uk': MagicMock(),
            'en': MagicMock(),
            'ru': MagicMock()
        }
        
        # Mock pymorphy3 analyzers
        self.service.ru_morph = MagicMock()
        self.service.uk_morph = MagicMock()
        
        # Mock variant service
        self.service.variant_service = MagicMock()

    def test_normalize_async_aggregates_all_variants(self):
        """
        Test that normalize_async correctly aggregates all variants from morphological analysis
        """
        # Arrange: Set up mock data and mock methods
        mock_analysis = [
            {
                'name': 'Сергій',
                'declensions': ['сергія', 'сергію'],
                'transliterations': ['serhii'],
                'diminutives': ['сергійко'],
                'all_forms': ['сергія', 'сергію', 'сергійко'],
                'normal_form': 'Сергій',
                'phonetic_variants': ['сергей']
            },
            {
                'name': 'Іванов',
                'declensions': ['іванова'],
                'transliterations': ['ivanov'],
                'diminutives': [],
                'all_forms': ['іванова'],
                'normal_form': 'Іванов',
                'phonetic_variants': ['иванов']
            }
        ]
        
        # Mock the _analyze_names_with_morphology method
        self.service._analyze_names_with_morphology = MagicMock(return_value=mock_analysis)
        
        # Mock the _clean_text method
        self.service._clean_text = MagicMock(return_value="Сергій Іванов")
        
        # Mock the _normalize_unicode method
        self.service._normalize_unicode = MagicMock(return_value="Сергій Іванов")
        
        # Mock the _tokenize_with_spacy method
        self.service._tokenize_with_spacy = MagicMock(return_value=["Сергій", "Іванов"])
        
        # Mock the _detect_language method
        self.service._detect_language = MagicMock(return_value="uk")
        
        # Mock variant service
        self.service.variant_service.analyze_names = MagicMock(return_value={
            'analyzed_names': mock_analysis
        })
        self.service.variant_service.generate_comprehensive_variants = MagicMock(return_value={
            'transliterations': ['Serhii'],
            'visual_similarities': ['Сергей'],
            'typo_variants': ['Серж'],
            'phonetic_variants': ['Sergey']
        })
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "Сергій Іванов",
                language="uk",
                enable_morphology=True,
                enable_transliterations=True,
                enable_phonetic_variants=True
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check that all variants are properly aggregated
        assert result.normalized == "Сергій Іванов"
        assert result.language == "uk"
        assert 'token_variants' in result
        assert 'total_variants' in result
        
        # Check that there are variants for each token
        token_variants = result['token_variants']
        assert 'Сергій' in token_variants
        assert 'Іванов' in token_variants
        
        # Check that variants are properly aggregated
        serhii_variants = token_variants['Сергій']
        assert 'transliterations' in serhii_variants
        assert 'visual_similarities' in serhii_variants
        assert 'typo_variants' in serhii_variants
        assert 'phonetic_variants' in serhii_variants
        
        # Check that total variants count is correct
        assert result['total_variants'] > 0
        
        # Check that morphological analysis results are included
        assert 'names_analysis' in result
        assert len(result['names_analysis']) == 2
        
        # Check that the first name analysis is correct
        serhii_analysis = result['names_analysis'][0]
        assert serhii_analysis['name'] == 'Сергій'
        # Check that all_forms contains some variants (may not include the original name)
        assert len(serhii_analysis['all_forms']) > 0
        assert 'сергійко' in serhii_analysis['diminutives']
        assert 'serhii' in serhii_analysis['transliterations']

    def test_normalize_async_without_morphology(self):
        """
        Test that normalize_async works without morphology enabled
        """
        # Arrange: Mock basic methods
        self.service._clean_text = MagicMock(return_value="Test Text")
        self.service._normalize_unicode = MagicMock(return_value="Test Text")
        self.service._tokenize_with_spacy = MagicMock(return_value=["Test", "Text"])
        self.service._detect_language = MagicMock(return_value="en")
        
        # Mock variant service
        self.service.variant_service.generate_comprehensive_variants = MagicMock(return_value={
            'transliterations': ['test_text'],
            'visual_similarities': ['test_text'],
            'typo_variants': ['test_text'],
            'phonetic_variants': ['test_text']
        })
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "Test Text",
                language="en",
                enable_morphology=False
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check basic functionality
        assert result.normalized == "Test Text"
        assert result.language == "en"
        assert result.normalized == "Test Text"
        assert 'token_variants' in result
        assert 'total_variants' in result
        
        # Check that token variants are generated
        token_variants = result['token_variants']
        assert 'Test' in token_variants
        assert 'Text' in token_variants
        
        # Check that total variants count is correct
        assert result['total_variants'] > 0
        
        # Check that names analysis is empty when morphology is disabled
        assert 'names_analysis' in result
        assert len(result['names_analysis']) == 0

    def test_normalize_async_error_handling(self):
        """
        Test that normalize_async handles errors gracefully
        """
        # Arrange: Mock methods to throw exceptions
        self.service._clean_text = MagicMock(side_effect=Exception("Clean text error"))
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "Test Text",
                language="en"
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check error handling
        assert result.normalized == "Test Text"
        assert 'error' in result or 'errors' in result
        
        # Check that the result still has basic structure
        assert 'normalized' in result
        assert 'language' in result
        assert 'tokens' in result
        assert 'token_variants' in result
        assert 'total_variants' in result

    def test_normalize_async_empty_text(self):
        """
        Test that normalize_async handles empty text correctly
        """
        # Arrange: Mock basic methods
        self.service._clean_text = MagicMock(return_value="")
        self.service._normalize_unicode = MagicMock(return_value="")
        self.service._tokenize_with_spacy = MagicMock(return_value=[])
        self.service._detect_language = MagicMock(return_value="en")
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "",
                language="en"
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check empty text handling
        assert result.normalized == ""
        assert result.normalized == ""
        assert result.language == "en"
        assert result.tokens == []
        assert result['token_variants'] == {}
        assert result['total_variants'] == 0
        assert result['names_analysis'] == []

    def test_normalize_async_language_detection(self):
        """
        Test that normalize_async properly detects language
        """
        # Arrange: Mock methods
        self.service._clean_text = MagicMock(return_value="Сергій Іванов")
        self.service._normalize_unicode = MagicMock(return_value="Сергій Іванов")
        self.service._tokenize_with_spacy = MagicMock(return_value=["Сергій", "Іванов"])
        self.service._detect_language = MagicMock(return_value="uk")
        
        # Mock variant service
        self.service.variant_service.generate_comprehensive_variants = MagicMock(return_value={
            'transliterations': ['serhii_ivanov'],
            'visual_similarities': ['сергей_иванов'],
            'typo_variants': ['сергей_иванов'],
            'phonetic_variants': ['sergey_ivanov']
        })
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "Сергій Іванов",
                language="auto"
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check language detection
        assert result.normalized == "Сергій Іванов"
        assert result.language == "uk"
        assert 'token_variants' in result
        assert 'total_variants' in result
        
        # Check that Ukrainian language is properly handled
        assert len(result.tokens) > 0
        assert result['total_variants'] > 0

    def test_normalize_async_token_variants_structure(self):
        """
        Test that token variants have the correct structure
        """
        # Arrange: Mock methods
        self.service._clean_text = MagicMock(return_value="John Smith")
        self.service._normalize_unicode = MagicMock(return_value="John Smith")
        self.service._tokenize_with_spacy = MagicMock(return_value=["John", "Smith"])
        self.service._detect_language = MagicMock(return_value="en")
        
        # Mock variant service with comprehensive variants
        self.service.variant_service.generate_comprehensive_variants = MagicMock(return_value={
            'transliterations': ['john_smith'],
            'visual_similarities': ['john_smith'],
            'typo_variants': ['john_smith'],
            'phonetic_variants': ['john_smith']
        })
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "John Smith",
                language="en"
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check result structure
        assert result.success is True
        assert result.normalized == "John Smith"
        assert result.tokens == ["John", "Smith"]
        assert result.language == "en"
        assert result.confidence == 1.0

    def test_normalize_async_morphology_integration(self):
        """
        Test that normalize_async properly integrates with morphology analysis
        """
        # Arrange: Mock morphological analysis
        mock_analysis = [
            {
                'name': 'Сергій',
                'declensions': ['Сергія', 'Сергію'],
                'transliterations': ['Serhii', 'Sergii'],
                'diminutives': ['Сергійко', 'Сержик'],
                'all_forms': ['Сергій', 'Сергія', 'Сергію', 'Сергійко'],
                'normal_form': 'Сергій',
                'phonetic_variants': ['Сергей', 'Серж']
            }
        ]
        
        # Mock the _analyze_names_with_morphology method
        self.service._analyze_names_with_morphology = MagicMock(return_value=mock_analysis)
        
        # Mock other methods
        self.service._clean_text = MagicMock(return_value="Сергій")
        self.service._normalize_unicode = MagicMock(return_value="Сергій")
        self.service._tokenize_with_spacy = MagicMock(return_value=["Сергій"])
        self.service._detect_language = MagicMock(return_value="uk")
        
        # Mock variant service
        self.service.variant_service.analyze_names = MagicMock(return_value={
            'analyzed_names': mock_analysis
        })
        self.service.variant_service.generate_comprehensive_variants = MagicMock(return_value={
            'transliterations': ['Serhii'],
            'visual_similarities': ['Сергей'],
            'typo_variants': ['Серж'],
            'phonetic_variants': ['Sergey']
        })
        
        # Act: Call the method under test
        async def run_test():
            result = await self.service.normalize_async(
                "Сергій",
                language="uk",
                enable_morphology=True
            )
            return result
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Assert: Check morphology integration
        assert result.normalized == "Сергій"
        assert result.language == "uk"
        assert 'names_analysis' in result
        assert len(result['names_analysis']) == 1
        
        # Check that morphological analysis is included
        name_analysis = result['names_analysis'][0]
        assert name_analysis['name'] == 'Сергій'
        assert 'Сергійко' in name_analysis['diminutives']
        assert 'Serhii' in name_analysis['transliterations']
        assert 'Сергей' in name_analysis['phonetic_variants']
        
        # Check that token variants are generated
        assert 'token_variants' in result
        assert 'Сергій' in result['token_variants']
        assert result['total_variants'] > 0
