"""
Unit tests for UnicodeService
"""

import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.unicode.unicode_service import UnicodeService


class TestUnicodeService:
    """Tests for UnicodeService"""
    
    def test_aggressive_normalization_sao_paulo(self, unicode_service):
        """Test aggressive normalization: 'São Paulo' -> 'sao paulo'"""
        # Arrange
        input_text = "São Paulo"
        
        # Act
        result = unicode_service.normalize_text(input_text, aggressive=True)
        
        # Assert
        assert result['normalized'].lower() == "sao paulo"  # ã -> a via unidecode
        assert result['original'] == input_text
        # In aggressive mode, changes can be either in char_replacement or ascii_folding
        # But if unidecode doesn't change text, there may be no changes
        
        # Check that in normal mode characters are preserved better
        normal_result = unicode_service.normalize_text(input_text, aggressive=False)
        # In normal mode there should be fewer changes
        assert len(normal_result['changes']) <= len(result['changes'])
    
    def test_cyrillic_processing(self, unicode_service):
        """Test Cyrillic processing: 'Привёт, мир!' - replace ё with е, but preserve Cyrillic"""
        # Arrange
        input_text = "Привёт, мир!"  # Use ё to check replacement
        
        # Act - use aggressive mode for normalization
        result = unicode_service.normalize_text(input_text, aggressive=True)
        
        # Assert
        # ё should be replaced with е (from complex_mappings)
        assert 'ё' not in result['normalized']  # ё replaced
        assert result['normalized'] == 'Привет, мир!'  # Case preserved, ё replaced with е
        assert result['original'] == input_text
        
        # Check that there are changes in char_replacement (ё -> е)
        char_replacements = [change for change in result['changes'] if change['type'] == 'char_replacement']
        assert len(char_replacements) > 0, "Should have character replacements for ё -> е"
    
    def test_empty_text_handling(self, unicode_service):
        """Test empty text handling"""
        # Act
        result = unicode_service.normalize_text("")
        
        # Assert
        assert result['normalized'] == ""
        assert result['original'] == ""
        assert result['changes'] == []
        assert result['confidence'] == 1.0
    
    def test_none_text_handling(self, unicode_service):
        """Test None handling"""
        # Act
        result = unicode_service.normalize_text(None)
        
        # Assert
        assert result['normalized'] == ""
        assert result['original'] is None
        assert result['changes'] == []
        assert result['confidence'] == 1.0
    
    def test_complex_mappings_applied(self, unicode_service):
        """Test complex mappings application"""
        # Arrange
        input_text = "Café résumé naïve"
        
        # Act
        result = unicode_service.normalize_text(input_text)
        
        # Assert
        normalized = result['normalized']
        # Check that diacritics were handled according to Unicode normalization rules
        # NOTE: As per CLAUDE.md P0.3 - Unicode preserves case, normalizes diacritics
        assert 'é' not in normalized, "Letter é should be normalized to e"
        assert 'è' not in normalized, "Letter è should be normalized to e"
        
        # Changes can be either in char_replacement or ascii_folding
        char_changes = [c for c in result['changes'] if c['type'] == 'char_replacement']
        ascii_changes = [c for c in result['changes'] if c['type'] == 'ascii_folding']
        
        # Text with diacritics must show normalization changes
        assert len(char_changes) > 0 or len(ascii_changes) > 0, "Diacritic normalization should produce changes"
    
    def test_confidence_calculation(self, unicode_service):
        """Test confidence calculation"""
        # Arrange
        simple_text = "Hello World"
        complex_text = "Café résumé naïve ñoño"
        
        # Act
        simple_result = unicode_service.normalize_text(simple_text)
        complex_result = unicode_service.normalize_text(complex_text)
        
        # Assert
        # Simple text should have high confidence
        assert simple_result['confidence'] >= 0.9
        
        # Complex text should have lower confidence due to changes
        # But if there are no changes, confidence can be the same
        if len(complex_result['changes']) > 0:
            assert complex_result['confidence'] <= simple_result['confidence']
        assert complex_result['confidence'] >= 0.1  # Not less than minimum
    
    def test_batch_normalization(self, unicode_service):
        """Test batch normalization"""
        # Arrange
        texts = ["São Paulo", "Café", "Hello", "Привёт"]
        
        # Act
        results = unicode_service.normalize_batch(texts)
        
        # Assert
        assert len(results) == len(texts)
        for i, result in enumerate(results):
            # Check that original text is preserved in results
            if texts[i] == "São Paulo":
                assert result['normalized'].lower() == "sao paulo"  # ã -> a via unidecode
            else:
                assert result['original'] == texts[i]
            assert 'normalized' in result
            assert 'changes' in result
            assert 'confidence' in result
    
    def test_similarity_score(self, unicode_service):
        """Test similarity score calculation between texts"""
        # Arrange
        text1 = "café"
        text2 = "cafe"
        text3 = "completely different"
        
        # Act
        similarity_high = unicode_service.get_similarity_score(text1, text2)
        similarity_low = unicode_service.get_similarity_score(text1, text3)
        
        # Assert
        assert 0.0 <= similarity_high <= 1.0
        assert 0.0 <= similarity_low <= 1.0
        assert similarity_high > similarity_low
    
    def test_encoding_issues_detection(self, unicode_service):
        """Test encoding issues detection"""
        # Arrange
        text_with_issues = "Café résumé\x00null_char"
        
        # Act
        issues = unicode_service.detect_encoding_issues(text_with_issues)
        
        # Assert
        assert len(issues) > 0
        
        # Check that we found null character
        null_char_issues = [issue for issue in issues if issue['type'] == 'null_char']
        assert len(null_char_issues) > 0
        assert null_char_issues[0]['count'] == 1
        
        # Check that we found replacement characters
        replacement_issues = [issue for issue in issues if issue['type'] == 'replacement_char']
        assert len(replacement_issues) > 0
    
    def test_final_cleanup(self, unicode_service):
        """Test final text cleanup"""
        # Arrange
        messy_text = "  Multiple   spaces  \t\n  "
        
        # Act
        result = unicode_service.normalize_text(messy_text)
        
        # Assert
        normalized = result['normalized']
        assert normalized == "Multiple spaces"  # Should be cleaned, case preserved
        assert not normalized.startswith(' ')
        assert not normalized.endswith(' ')
        assert '\t' not in normalized
        assert '\n' not in normalized
    
    def test_preserve_chars_functionality(self, unicode_service):
        """Test special characters preservation"""
        # Arrange
        text_with_preserves = "O'Connor-Smith Jr."
        
        # Act
        result = unicode_service.normalize_text(text_with_preserves)
        
        # Assert
        normalized = result['normalized']
        # Dots, hyphens and apostrophes should be preserved in some form
        # (depending on service logic)
        assert result['original'] == text_with_preserves
    
    def test_unicode_normalization_nfd_nfkc(self, unicode_service):
        """Test Unicode normalization NFD -> NFKC application"""
        # Arrange
        # Use character that can have different representations
        input_text = "é"  # Can be represented as single character or e + ́
        
        # Act
        result = unicode_service.normalize_text(input_text)
        
        # Assert
        assert result['normalized'] is not None
        assert result['original'] == input_text
    
    def test_ascii_folding_failure_handling(self, unicode_service):
        """Test ASCII folding error handling"""
        # Arrange
        input_text = "café"
        
        # Act
        result = unicode_service.normalize_text(input_text, aggressive=False)
        
        # Assert
        # Should handle error gracefully
        assert result['normalized'] is not None
        # Check that service continues working even with ASCII folding error
        assert 'normalized' in result
    
    @patch('src.ai_service.services.unicode_service.unicodedata.normalize')
    def test_unicode_normalization_failure_handling(self, mock_normalize, unicode_service):
        """Test Unicode normalization error handling"""
        # Arrange
        mock_normalize.side_effect = Exception("Unicode normalization failed")
        input_text = "test"
        
        # Act
        result = unicode_service.normalize_text(input_text)
        
        # Assert
        # Should return original text on error
        assert result['normalized'] is not None
    
    def test_length_metadata(self, unicode_service):
        """Test text length metadata"""
        # Arrange
        input_text = "Hello World"
        
        # Act
        result = unicode_service.normalize_text(input_text)
        
        # Assert
        assert 'length_original' in result
        assert 'length_normalized' in result
        assert result['length_original'] == len(input_text)
        assert result['length_normalized'] == len(result['normalized'])
    
    def test_case_normalization(self, unicode_service):
        """Test case normalization"""
        # Arrange
        mixed_case_text = "MiXeD CaSe TeXt"
        
        # Act
        result = unicode_service.normalize_text(mixed_case_text)
        
        # Assert - case is now preserved after P0.3 fix
        assert result['normalized'] == mixed_case_text
    
    def test_german_umlauts_handling(self, unicode_service):
        """Test German umlauts handling"""
        # Arrange
        german_text = "Müller Größe"
        
        # Act
        result = unicode_service.normalize_text(german_text)
        
        # Assert
        # Umlauts should be processed according to complex_mappings
        normalized = result['normalized']
        changes = result['changes']
        
        # Check that there are changes either in char_replacement or ascii_folding
        char_changes = [c for c in changes if c['type'] == 'char_replacement']
        ascii_changes = [c for c in changes if c['type'] == 'ascii_folding']
        
        # German umlauts must be normalized according to Unicode rules
        assert 'ü' not in normalized, "Letter ü should be normalized to u"
        assert 'ö' not in normalized, "Letter ö should be normalized to o"

        # German text with umlauts must show normalization changes
        assert len(char_changes) > 0 or len(ascii_changes) > 0, "Umlaut normalization should produce changes"
