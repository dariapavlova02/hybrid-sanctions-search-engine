"""
Unit tests for embedding preprocessor
"""

import pytest
from ai_service.services.embedding_preprocessor import EmbeddingPreprocessor


class TestEmbeddingPreprocessor:
    """Test embedding preprocessor functionality"""

    def test_remove_dates_and_ids_by_default(self):
        """Test that dates and IDs are removed by default"""
        preprocessor = EmbeddingPreprocessor()
        
        # Test with date and ID
        text = "Ivan Ivanov 1980-01-01 passport12345"
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == "Ivan Ivanov"
        assert "1980-01-01" not in result
        assert "passport12345" not in result

    def test_remove_various_date_formats(self):
        """Test removal of various date formats"""
        preprocessor = EmbeddingPreprocessor()
        
        test_cases = [
            ("John Doe 1990-12-25", "John Doe"),
            ("Jane Smith 25.12.1990", "Jane Smith"),
            ("Bob Wilson 25/12/1990", "Bob Wilson"),
            ("Alice Brown 25 декабря 1990", "Alice Brown"),
            ("Charlie Green 25 December 1990", "Charlie Green"),
        ]
        
        for input_text, expected in test_cases:
            result = preprocessor.normalize_for_embedding(input_text)
            assert result == expected

    def test_remove_various_id_formats(self):
        """Test removal of various ID formats"""
        preprocessor = EmbeddingPreprocessor()
        
        test_cases = [
            ("John Doe passport12345", "John Doe"),
            ("Jane Smith passport №12345", "Jane Smith"),
            ("Bob Wilson ID12345", "Bob Wilson"),
            ("Alice Brown №12345", "Alice Brown"),
            ("Charlie Green 1234 5678 9012 3456", "Charlie Green"),
            ("David Lee 123-456-789", "David Lee"),
        ]
        
        for input_text, expected in test_cases:
            result = preprocessor.normalize_for_embedding(input_text)
            assert result == expected

    def test_fold_spaces(self):
        """Test that multiple spaces are folded into single space"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan    Ivanov   1980-01-01"
        result = preprocessor.normalize_for_embedding(text, fold_spaces=True)
        
        assert result == "Ivan Ivanov"
        assert "  " not in result  # No double spaces

    def test_preserve_spaces_when_fold_spaces_false(self):
        """Test that spaces are preserved when fold_spaces=False"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan    Ivanov   1980-01-01"
        result = preprocessor.normalize_for_embedding(text, fold_spaces=False)
        
        assert "Ivan" in result
        assert "Ivanov" in result
        assert "1980-01-01" not in result
        # Should still have multiple spaces since fold_spaces=False
        assert "    " in result

    def test_empty_text_handling(self):
        """Test handling of empty or whitespace-only text"""
        preprocessor = EmbeddingPreprocessor()
        
        assert preprocessor.normalize_for_embedding("") == ""
        assert preprocessor.normalize_for_embedding("   ") == ""
        assert preprocessor.normalize_for_embedding("\t\n") == ""

    def test_only_dates_and_ids(self):
        """Test text that contains only dates and IDs"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "1980-01-01 passport12345"
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == ""

    def test_extract_name_only_method(self):
        """Test the extract_name_only convenience method"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan Ivanov 1980-01-01 passport12345"
        result = preprocessor.extract_name_only(text)
        
        assert result == "Ivan Ivanov"

    def test_include_attrs_future_flag(self):
        """Test that include_attrs=True is not yet implemented"""
        preprocessor = EmbeddingPreprocessor()
        
        # Should return False by default
        assert preprocessor.should_include_attrs() is False
        
        # Should warn when include_attrs=True is used
        text = "Ivan Ivanov 1980-01-01 passport12345"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        
        # Should still remove dates/IDs since include_attrs is not implemented
        assert result == "Ivan Ivanov"

    def test_complex_text_processing(self):
        """Test processing of complex text with multiple dates and IDs"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan Petrovich Ivanov 1980-01-01 passport12345 ID789 25.12.1990"
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == "Ivan Petrovich Ivanov"
        assert "1980-01-01" not in result
        assert "passport12345" not in result
        assert "ID789" not in result
        assert "25.12.1990" not in result

    def test_organization_names(self):
        """Test processing of organization names with dates/IDs"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "ООО Рога и Копыта 1980-01-01 ИНН1234567890"
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == "ООО Рога и Копыта"
        assert "1980-01-01" not in result
        assert "ИНН1234567890" not in result

    def test_mixed_language_text(self):
        """Test processing of mixed language text"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan Иванов 1980-01-01 passport12345"
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == "Ivan Иванов"
        assert "1980-01-01" not in result
        assert "passport12345" not in result

    def test_whitespace_normalization(self):
        """Test that whitespace is properly normalized"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "  Ivan   Ivanov  \t\n 1980-01-01  "
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == "Ivan Ivanov"
        assert result.strip() == result  # No leading/trailing whitespace
        assert "  " not in result  # No double spaces

    def test_case_insensitive_removal(self):
        """Test that date/ID removal is case insensitive"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "John Doe PASSPORT12345 ID789"
        result = preprocessor.normalize_for_embedding(text)
        
        assert result == "John Doe"
        assert "PASSPORT12345" not in result
        assert "ID789" not in result
