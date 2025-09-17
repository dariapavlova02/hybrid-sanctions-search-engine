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

    def test_include_attrs_enabled(self):
        """Test that include_attrs=True is now implemented"""
        preprocessor = EmbeddingPreprocessor()
        
        # Should return True by default (enabled in config)
        assert preprocessor.should_include_attrs() is True
        
        # Test with attributes provided
        text = "Ivan Ivanov"
        attributes = {"country": "UA", "dob": "1980-01-01", "gender": "M"}
        result = preprocessor.normalize_for_embedding(text, include_attrs=True, attributes=attributes)
        
        # Should include attributes
        assert "Ivan Ivanov" in result
        assert "country:UA" in result
        assert "dob:1980-01-01" in result
        assert "gender:M" in result

    def test_extract_attributes_from_text(self):
        """Test attribute extraction from text"""
        preprocessor = EmbeddingPreprocessor()
        
        # Test country extraction
        text = "Ivan Ivanov country:UA"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "country:UA" in result
        
        # Test DOB extraction
        text = "Ivan Ivanov dob:1980-01-01"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "dob:1980-01-01" in result
        
        # Test gender extraction
        text = "Ivan Ivanov gender:M"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "gender:M" in result

    def test_attribute_normalization(self):
        """Test attribute value normalization"""
        preprocessor = EmbeddingPreprocessor()
        
        # Test country normalization
        text = "Ivan Ivanov country:ua"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "country:UA" in result
        
        # Test date normalization
        text = "Ivan Ivanov dob:01.01.1980"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "dob:1980-01-01" in result
        
        # Test gender normalization
        text = "Ivan Ivanov gender:male"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "gender:M" in result

    def test_normalize_with_attributes_method(self):
        """Test the convenience method for attribute normalization"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan Ivanov"
        attributes = {"country": "UA", "dob": "1980-01-01", "gender": "M"}
        result = preprocessor.normalize_with_attributes(text, attributes)
        
        assert "Ivan Ivanov" in result
        assert "country:UA" in result
        assert "dob:1980-01-01" in result
        assert "gender:M" in result

    def test_mixed_language_attributes(self):
        """Test attribute extraction in different languages"""
        preprocessor = EmbeddingPreprocessor()
        
        # Russian attributes
        text = "Иван Иванов страна:RU пол:М"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "Иван Иванов" in result
        assert "country:RU" in result
        assert "gender:M" in result
        
        # Ukrainian attributes
        text = "Іван Іванов країна:UA стать:Ч"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        assert "Іван Іванов" in result
        assert "country:UA" in result
        assert "gender:M" in result

    def test_include_attrs_with_dates_and_ids(self):
        """Test that dates and IDs are still removed when include_attrs=True"""
        preprocessor = EmbeddingPreprocessor()
        
        text = "Ivan Ivanov 1980-01-01 passport12345 country:UA"
        result = preprocessor.normalize_for_embedding(text, include_attrs=True)
        
        assert "Ivan Ivanov" in result
        assert "country:UA" in result
        assert "1980-01-01" not in result
        assert "passport12345" not in result

    def test_configuration_loading(self):
        """Test that configuration is loaded correctly"""
        preprocessor = EmbeddingPreprocessor()
        
        # Test that config is loaded
        assert preprocessor.config is not None
        assert "include_attrs" in preprocessor.config
        assert preprocessor.config["include_attrs"]["enabled"] is True
        assert "country" in preprocessor.config["include_attrs"]["attributes"]

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
