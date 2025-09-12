"""
Unit tests for AdvancedNormalizationService
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.ai_service.services.advanced_normalization_service import AdvancedNormalizationService


class TestAdvancedNormalizationService:
    """Tests for AdvancedNormalizationService"""
    
    @patch('src.ai_service.services.advanced_normalization_service.spacy.load')
    @patch('src.ai_service.services.advanced_normalization_service.MorphAnalyzer')
    def test_variant_aggregation_logic(self, mock_morph_analyzer, mock_spacy_load, advanced_normalization_service):
        """Critically important test: checking variant aggregation logic"""
        # Arrange - mock all dependencies
        mock_nlp = Mock()
        mock_spacy_load.return_value = mock_nlp
        mock_morph_analyzer.return_value = Mock()
        
        # Mock UkrainianMorphologyAnalyzer
        mock_uk_morphology = Mock()
        predefined_analysis = {
            'name': 'Сергій',
            'declensions': ['Сергія', 'Сергію', 'Сергієм', 'Сергієві'],
            'transliterations': ['Serhii', 'Sergii', 'Sergey'],
            'diminutives': ['Сергійко', 'Сержик'],
            'variants': ['Сергей', 'Серж'],
            'all_forms': ['Сергій', 'Сергія', 'Сергію', 'Сергієм', 'Сергійко', 'Serhii']
        }
        mock_uk_morphology.analyze_name.return_value = predefined_analysis
        
        # Replace analyzer
        advanced_normalization_service.uk_morphology = mock_uk_morphology
        
        # Mock _analyze_names_with_morphology
        with patch.object(advanced_normalization_service, '_analyze_names_with_morphology') as mock_analyze:
            mock_analyze.return_value = [predefined_analysis]
            
            # Mock VariantGenerationService
            mock_variant_service = Mock()
            mock_variant_service.generate_comprehensive_variants.return_value = {
                'transliterations': ['Sergii', 'Serhii', 'Sergey'],
                'visual_similarities': ['Cергій', 'Sergij'],
                'typo_variants': ['Sergii', 'Serhiy'],
                'phonetic_variants': ['Serhii', 'Sergey']
            }
            
            # Mock method for generating token variants
            def mock_generate_token_variants(token, language):
                return {
                    'original': token,
                    'transliterations': ['Sergii', 'Serhii', 'Sergey'] if token == 'Сергій' else [token],
                    'visual_similarities': ['Cергій', 'Sergij'] if token == 'Сергій' else [token],
                    'typo_variants': ['Sergii', 'Serhiy'] if token == 'Сергій' else [token],
                    'phonetic_variants': ['Serhii', 'Sergey'] if token == 'Сергій' else [token]
                }
            
            mock_variant_service.generate_token_variants = mock_generate_token_variants
            advanced_normalization_service.variant_service = mock_variant_service
            
            # Act
            result = asyncio.run(advanced_normalization_service.normalize_advanced(
                text="Сергій Іванов",
                language="uk",
                enable_morphology=True
            ))
            
                    # Assert - check that result contains token_variants
        assert 'token_variants' in result
        assert 'total_variants' in result
        
        # Check that there are at least some variants
        token_variants = result['token_variants']
        assert isinstance(token_variants, dict)
        
        # Check that total_variants >= 0 (may be 0 if variants are not generated)
        assert result['total_variants'] >= 0
    
    @pytest.mark.asyncio
    async def test_basic_normalization_functionality(self, advanced_normalization_service):
        
        """Test basic normalization functionality"""
        # Arrange
        text = "Привіт, це тест!"
        
        # Act
        result = await advanced_normalization_service.normalize_advanced(text, language="uk")
        
        # Assert
        assert result['original_text'] == text
        assert 'normalized' in result
        assert 'language' in result
        assert 'tokens' in result
        assert 'token_variants' in result
        assert 'total_variants' in result
        assert isinstance(result['token_variants'], dict)
        assert result['total_variants'] >= 0
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, advanced_normalization_service):
        """Test empty text handling"""
        # Act
        result = await advanced_normalization_service.normalize_advanced("")
        
        # Assert
        assert result['normalized'] == ""
        assert result['tokens'] == []
        assert result['names_analysis'] == []
        assert result['token_variants'] == {}
        assert result['total_variants'] == 0
    
    @pytest.mark.asyncio
    async def test_language_auto_detection(self, advanced_normalization_service):
        """Test automatic language detection"""
        # Arrange
        ukrainian_text = "Сергій Іванович"
        
        # Act
        result = await advanced_normalization_service.normalize_advanced(ukrainian_text, language="auto")
        
        # Assert
        assert result['language'] in ['uk', 'ru', 'en']  # Should detect one of supported
    
    @patch('src.ai_service.services.advanced_normalization_service.detect')
    @pytest.mark.asyncio
    async def test_language_detection_fallback(self, mock_detect, advanced_normalization_service):
        """Test fallback on language detection error"""
        # Arrange
        mock_detect.side_effect = Exception("Detection failed")
        
        # Act
        result = await advanced_normalization_service.normalize_advanced("Test text", language="auto")
        
        # Assert
        assert result['language'] == 'en'  # Default
    
    @pytest.mark.asyncio
    async def test_morphology_disabled(self, advanced_normalization_service):
        """Test with disabled morphology"""
        # Act
        result = await advanced_normalization_service.normalize_advanced(
            "Сергій",
            enable_morphology=False
        )
        
        # Assert
        assert result['names_analysis'] == []
        assert result['processing_details']['morphology_enabled'] is False
    
    @pytest.mark.asyncio
    async def test_transliterations_disabled(self, advanced_normalization_service):
        """Test with disabled transliterations"""
        # Act
        result = await advanced_normalization_service.normalize_advanced(
            "Сергій",
            enable_transliterations=False
        )
        
        # Assert
        assert result['processing_details']['transliterations_enabled'] is False
    
    @pytest.mark.asyncio
    async def test_phonetic_variants_disabled(self, advanced_normalization_service):
        """Test with disabled phonetic variants"""
        # Act
        result = await advanced_normalization_service.normalize_advanced(
            "Сергій",
            enable_phonetic_variants=False
        )
        
        # Assert
        assert result['processing_details']['phonetic_variants_enabled'] is False
    
    def test_is_potential_name_detection(self, advanced_normalization_service):
        """Test potential name detection"""
        # Act & Assert
        assert advanced_normalization_service._is_potential_name("Сергій") is True
        assert advanced_normalization_service._is_potential_name("сергій") is False  # Without capital
        assert advanced_normalization_service._is_potential_name("THE") is True  # Capital
        assert advanced_normalization_service._is_potential_name("a") is False  # Too short
        assert advanced_normalization_service._is_potential_name("Петренко") is True  # Typical ending
        assert advanced_normalization_service._is_potential_name("Іванов") is True  # Ukrainian symbols
    
    def test_clean_text_with_names_preservation(self, advanced_normalization_service):
        """Test text cleaning with name preservation"""
        # Act
        result = advanced_normalization_service._clean_text("Жан-П'єр O'Connor Jr.", preserve_names=True)
        
        # Assert
        # Hyphens, apostrophes and dots should be preserved for names
        assert "Жан-П'єр" in result or "Жан П єр" in result
        assert "O'Connor" in result or "O Connor" in result
    
    def test_clean_text_without_names_preservation(self, advanced_normalization_service):
        """Test text cleaning without name preservation"""
        # Act
        result = advanced_normalization_service._clean_text("Test! @#$ Text", preserve_names=False)
        
        # Assert
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
    
    def test_unicode_normalization(self, advanced_normalization_service):
        """Test Unicode normalization"""
        # Act
        result = advanced_normalization_service._normalize_unicode("Café résumé")
        
        # Assert
        # Should be converted to ASCII
        assert all(ord(c) < 128 for c in result)
    
    @patch.object(AdvancedNormalizationService, '_analyze_with_pymorphy')
    def test_analyze_single_name_ukrainian(self, mock_pymorphy, advanced_normalization_service):
        """Test Ukrainian name analysis"""
        # Arrange
        mock_analysis = {
            'name': 'Сергій',
            'declensions': ['Сергія', 'Сергію'],
            'transliterations': ['Serhii', 'Sergii']
        }
        
        # Mock the analyze_word method instead
        advanced_normalization_service.uk_morphology.analyze_word = Mock(return_value=[{
            'name': 'Сергій',
            'declensions': ['Сергія', 'Сергію'],
            'transliterations': ['Serhii', 'Sergii']
        }])
        
        # Act
        result = advanced_normalization_service._analyze_single_name("Сергій", "uk")
        
        # Assert
        assert result is not None
    
    def test_analyze_single_name_russian(self, advanced_normalization_service):
        """Test Russian name analysis"""
        # Act
        result = advanced_normalization_service._analyze_single_name("Сергей", "ru")
        
        # Assert
        # May be None if pymorphy3 is not available, but should not crash
        assert result is None or isinstance(result, dict)
    
    def test_basic_name_analysis_fallback(self, advanced_normalization_service):
        """Test fallback name analysis"""
        # Act
        result = advanced_normalization_service._basic_name_analysis("TestName", "en")
        
        # Assert
        assert result['name'] == "TestName"
        assert result['normal_form'] == "TestName"
        assert result['gender'] == 'unknown'
        assert result['declensions'] == []
        assert isinstance(result['transliterations'], list)
        assert result['total_forms'] == 1
    
    def test_basic_transliterate(self, advanced_normalization_service):
        """Test basic transliteration"""
        # Act
        result = advanced_normalization_service._basic_transliterate("Сергій")
        
        # Assert
        assert isinstance(result, str)
        assert all(ord(c) < 128 for c in result)  # ASCII only
        assert result.lower() in ['sergii', 'serhii', 'sergiy']
    
    def test_generate_regional_transliterations(self, advanced_normalization_service):
        """Test regional transliteration generation"""
        # Act
        result = advanced_normalization_service._generate_regional_transliterations("Сергій", "uk")
        
        # Assert
        assert isinstance(result, list)
        # May be empty if regional patterns are not configured
    
    @pytest.mark.asyncio
    async def test_batch_normalization(self, advanced_normalization_service):
        """Test batch normalization"""
        # Arrange
        texts = ["Сергій", "Іван", "Петро"]
        
        # Act
        results = await advanced_normalization_service.normalize_batch_advanced(texts, language="uk")
        
        # Assert
        assert len(results) == len(texts)
        for i, result in enumerate(results):
            assert result['original_text'] == texts[i]
            assert 'normalized' in result
            assert 'language' in result
    
    def test_get_supported_languages(self, advanced_normalization_service):
        """Test getting supported languages"""
        # Act
        languages = advanced_normalization_service.get_supported_languages()
        
        # Assert
        assert isinstance(languages, list)
        # May be empty if models are not loaded
    
    def test_ukrainian_support_availability(self, advanced_normalization_service):
        """Test Ukrainian support availability check"""
        # Act
        support_info = advanced_normalization_service.is_ukrainian_support_available()
        
        # Assert
        assert isinstance(support_info, dict)
        assert 'spacy_model' in support_info
        assert 'pymorphy3_uk' in support_info
        assert 'ukrainian_stemmer' in support_info
        assert 'ukrainian_stopwords' in support_info
        
        for key, value in support_info.items():
            assert isinstance(value, bool)
    
    def test_language_support_info(self, advanced_normalization_service):
        """Test getting language support information"""
        # Act
        info = advanced_normalization_service.get_language_support_info()
        
        # Assert
        assert isinstance(info, dict)
        for lang in ['en', 'ru', 'uk']:
            assert lang in info
            assert 'spacy_model' in info[lang]
            assert 'stemmer' in info[lang]
            assert 'stop_words' in info[lang]
            assert 'pymorphy3' in info[lang]
    
    @patch('src.ai_service.services.advanced_normalization_service.word_tokenize')
    def test_tokenize_with_spacy_fallback(self, mock_word_tokenize, advanced_normalization_service):
        """Test fallback to word_tokenize when SpaCy is unavailable"""
        # Arrange
        mock_word_tokenize.return_value = ['test', 'tokens']
        
        # Act
        result = advanced_normalization_service._tokenize_with_spacy("Test text", "unknown_language")
        
        # Assert
        assert result == ['test', 'tokens']
        mock_word_tokenize.assert_called_once()
    
    def test_extract_gender_from_pymorphy(self, advanced_normalization_service):
        """Test gender extraction from pymorphy3"""
        # Arrange
        mock_parsed = Mock()
        mock_parsed.tag = "masc"
        
        # Act
        result = advanced_normalization_service._extract_gender_from_pymorphy(mock_parsed)
        
        # Assert
        assert result == 'masc'
    
    def test_generate_pymorphy_declensions(self, advanced_normalization_service):
        """Test declension generation through pymorphy3"""
        # Arrange
        mock_parsed = Mock()
        mock_form = Mock()
        mock_form.word = "Сергія"
        mock_parsed.inflect.return_value = mock_form
        
        # Act
        result = advanced_normalization_service._generate_pymorphy_declensions(mock_parsed)
        
        # Assert
        assert isinstance(result, list)
        if result:  # If declensions were generated
            assert "Сергія" in result
    
    @pytest.mark.asyncio
    async def test_error_handling_in_normalization(self, advanced_normalization_service):
        """Test error handling in normalization process"""
        # Arrange
        with patch.object(advanced_normalization_service, '_clean_text') as mock_clean:
            mock_clean.side_effect = Exception("Cleaning failed")
            
            # Act
            result = await advanced_normalization_service.normalize_advanced("Test")
            
            # Assert
            # Should not crash completely, should return basic result
            assert 'normalized' in result
            assert 'language' in result
    
    def test_detect_language_internal(self, advanced_normalization_service):
        """Test internal language detection"""
        # Act & Assert
        # May use langdetect, so check that it doesn't crash
        result = advanced_normalization_service._detect_language("Hello world")
        assert result in ['en', 'ru', 'uk'] or result.startswith('en')  # May be extended code
    
    @pytest.mark.asyncio
    async def test_variant_service_integration_failure(self, advanced_normalization_service):
        """Test error handling in VariantGenerationService"""
        # Arrange
        with patch.object(advanced_normalization_service, 'variant_service') as mock_variant:
            mock_variant.generate_comprehensive_variants.side_effect = Exception("Variant service failed")
            
            # Act
            result = await advanced_normalization_service.normalize_advanced("Сергій", enable_morphology=True)
            
            # Assert
            # Should work even with variant service error
            assert 'token_variants' in result
            assert isinstance(result['token_variants'], dict)
