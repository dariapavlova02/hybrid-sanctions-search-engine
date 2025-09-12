#!/usr/bin/env python3
"""
Unit tests for flag-based behavior in normalization service.
"""

import pytest
from ai_service.services.normalization_service import NormalizationService
from ai_service.services.stopwords import STOP_ALL


class TestFlagsBehavior:
    """Test that normalization service respects configuration flags."""
    
    @pytest.fixture
    def service(self):
        """Create normalization service instance."""
        return NormalizationService()
    
    def test_remove_stop_words_false(self, service):
        """Test that when remove_stop_words=False, STOP_ALL items remain among tokens."""
        # Use a text that contains stop words
        text = "Переказ коштів від імені Петро Іванович Коваленко"
        result = service._normalize_sync(text, language="uk", remove_stop_words=False)
        
        # Check that stop words are present in tokens
        tokens = result.tokens
        stop_words_found = [token.lower() for token in tokens if token.lower() in STOP_ALL]
        
        # Should find some stop words
        assert len(stop_words_found) > 0, f"Expected stop words in tokens {tokens}, but found none"
        
        # Verify specific stop words are present
        assert any(word in ["від", "переказ"] for word in stop_words_found), f"Expected 'від' or 'переказ' in {stop_words_found}"
    
    def test_remove_stop_words_true(self, service):
        """Test that when remove_stop_words=True, STOP_ALL items are filtered out."""
        # Use a text that contains stop words
        text = "Переказ коштів від імені Петро Іванович Коваленко"
        result = service._normalize_sync(text, language="uk", remove_stop_words=True)
        
        # Check that stop words are not present in tokens
        tokens = result.tokens
        stop_words_found = [token.lower() for token in tokens if token.lower() in STOP_ALL]
        
        # Should not find stop words
        assert len(stop_words_found) == 0, f"Expected no stop words in tokens {tokens}, but found {stop_words_found}"
    
    def test_preserve_names_false(self, service):
        """Test that when preserve_names=False, separators like O'Brien are split."""
        # Use a text with separators that should be split
        text = "Переказ коштів на ім'я O'Brien Петро-Іванович Коваленко"
        result = service._normalize_sync(text, language="uk", remove_stop_words=False, preserve_names=False)
        
        # Check that separators are split
        tokens = result.tokens
        normalized_text = result.normalized
        
        # O'Brien should be split into separate tokens
        assert "O'Brien" not in normalized_text, f"Expected O'Brien to be split, but found in: {normalized_text}"
        
        # Should have separate tokens for O and Brien
        assert any("O" in token for token in tokens), f"Expected 'O' token in {tokens}"
        assert any("Brien" in token for token in tokens), f"Expected 'Brien' token in {tokens}"
        
        # Петро-Іванович should also be split
        assert "Петро-Іванович" not in normalized_text, f"Expected Петро-Іванович to be split, but found in: {normalized_text}"
    
    def test_preserve_names_true(self, service):
        """Test that when preserve_names=True, separators are preserved."""
        # Use a text with separators that should be preserved
        text = "Переказ коштів на ім'я O'Brien Петро-Іванович Коваленко"
        result = service._normalize_sync(text, language="uk", preserve_names=True)
        
        # Check that separators are preserved
        tokens = result.tokens
        normalized_text = result.normalized
        
        # O'Brien should be preserved as a single token
        assert any("O'brien" in token for token in tokens), f"Expected O'brien to be preserved in tokens: {tokens}"
        
        # Петро-Іванович should also be preserved (case may be normalized)
        assert any("Петро-іванович" in token for token in tokens), f"Expected Петро-іванович to be preserved in tokens: {tokens}"
    
    def test_enable_advanced_features_false_slavic(self, service):
        """Test that when enable_advanced_features=False, morphology is skipped for Slavic text."""
        # Use Russian text that would normally be morphed
        text = "Сергея Петрова"
        result = service._normalize_sync(text, language="ru", enable_advanced_features=False)
        
        # Check that morphology was not applied
        tokens = result.tokens
        normalized_text = result.normalized
        
        # Should not be morphed to nominative case
        # "Сергея" should remain as "Сергея" (not "Сергей")
        # "Петрова" should remain as "Петрова" (not "Петров")
        assert "Сергей" not in normalized_text, f"Expected 'Сергея' to not be morphed to 'Сергей', but found: {normalized_text}"
        # Check that "Петров" is not a separate word in the text
        words = normalized_text.split()
        assert "Петров" not in words, f"Expected 'Петрова' to not be morphed to 'Петров', but found: {words}"
        
        # Should still have proper capitalization
        assert any("Сергея" in token for token in tokens), f"Expected 'Сергея' in tokens: {tokens}"
        assert any("Петрова" in token for token in tokens), f"Expected 'Петрова' in tokens: {tokens}"
        
        # Check traces to verify basic_capitalize rule was used
        for trace in result.trace:
            if trace.token in ["Сергея", "Петрова"]:
                assert trace.rule == "basic_capitalize", f"Expected basic_capitalize rule for {trace.token}, got {trace.rule}"
    
    def test_enable_advanced_features_true_slavic(self, service):
        """Test that when enable_advanced_features=True, morphology is applied for Slavic text."""
        # Use Russian text that should be morphed
        text = "Сергея Петрова"
        result = service._normalize_sync(text, language="ru", enable_advanced_features=True)
        
        # Check that morphology was applied
        tokens = result.tokens
        normalized_text = result.normalized
        
        # Should be morphed to nominative case
        # "Сергея" should become "Сергей"
        # "Петрова" should become "Петров"
        assert "Сергей" in normalized_text, f"Expected 'Сергея' to be morphed to 'Сергей', but found: {normalized_text}"
        assert "Петров" in normalized_text, f"Expected 'Петрова' to be morphed to 'Петров', but found: {normalized_text}"
    
    def test_enable_advanced_features_false_english(self, service):
        """Test that when enable_advanced_features=False, advanced features are skipped for English text."""
        # Use English text with nicknames
        text = "Bill Smith"
        result = service._normalize_sync(text, language="en", enable_advanced_features=False)
        
        # Check that nickname mapping was not applied
        tokens = result.tokens
        normalized_text = result.normalized
        
        # "Bill" should remain as "Bill" (not "William")
        assert "William" not in normalized_text, f"Expected 'Bill' to not be mapped to 'William', but found: {normalized_text}"
        assert "Bill" in normalized_text, f"Expected 'Bill' to remain as 'Bill', but found: {normalized_text}"
        
        # Check traces to verify basic_capitalize rule was used
        for trace in result.trace:
            if trace.token == "Bill":
                assert trace.rule == "basic_capitalize", f"Expected basic_capitalize rule for Bill, got {trace.rule}"
    
    def test_enable_advanced_features_true_english(self, service):
        """Test that when enable_advanced_features=True, advanced features are applied for English text."""
        # Use English text with nicknames
        text = "Bill Smith"
        result = service._normalize_sync(text, language="en", enable_advanced_features=True)
        
        # Check that nickname mapping was applied
        tokens = result.tokens
        normalized_text = result.normalized
        
        # "Bill" should be mapped to "William"
        assert "William" in normalized_text, f"Expected 'Bill' to be mapped to 'William', but found: {normalized_text}"
    
    def test_initial_cleanup_still_works_with_flags(self, service):
        """Test that initial cleanup still works regardless of flag settings."""
        # Use text with initials
        text = "П.І. Коваленко"
        result = service._normalize_sync(text, language="uk", 
                                       remove_stop_words=False, 
                                       preserve_names=False, 
                                       enable_advanced_features=False)
        
        # Check that initials are still cleaned up
        tokens = result.tokens
        normalized_text = result.normalized
        
        # Should have properly formatted initials (dots removed when preserve_names=False)
        assert any("П" in token for token in tokens), f"Expected 'П' in tokens: {tokens}"
        assert any("І" in token for token in tokens), f"Expected 'І' in tokens: {tokens}"
        
        # Check traces to verify basic_capitalize rule was used (since dots are removed when preserve_names=False)
        for trace in result.trace:
            if trace.token in ["П", "І"]:
                assert trace.rule == "basic_capitalize", f"Expected basic_capitalize rule for {trace.token}, got {trace.rule}"
    
    def test_all_flags_false(self, service):
        """Test behavior when all flags are False."""
        text = "Переказ коштів від імені O'Brien Петро-Іванович Коваленко"
        result = service._normalize_sync(text, language="uk", 
                                       remove_stop_words=False, 
                                       preserve_names=False, 
                                       enable_advanced_features=False)
        
        # Should have stop words
        tokens = result.tokens
        stop_words_found = [token.lower() for token in tokens if token.lower() in STOP_ALL]
        assert len(stop_words_found) > 0, f"Expected stop words when remove_stop_words=False, but found none in {tokens}"
        
        # Should have split separators
        assert "O'Brien" not in result.normalized, f"Expected O'Brien to be split when preserve_names=False"
        
        # Should have basic capitalization only
        for trace in result.trace:
            if trace.rule not in ["initial_cleanup", "basic_capitalize"]:
                # Only allow initial cleanup and basic capitalization
                assert trace.rule in ["initial_cleanup", "basic_capitalize"], f"Unexpected rule {trace.rule} when enable_advanced_features=False"
    
    def test_all_flags_true(self, service):
        """Test behavior when all flags are True (default behavior)."""
        text = "Переказ коштів від імені O'Brien Петро-Іванович Коваленко"
        result = service._normalize_sync(text, language="uk", 
                                       remove_stop_words=True, 
                                       preserve_names=True, 
                                       enable_advanced_features=True)
        
        # Should not have stop words
        tokens = result.tokens
        stop_words_found = [token.lower() for token in tokens if token.lower() in STOP_ALL]
        assert len(stop_words_found) == 0, f"Expected no stop words when remove_stop_words=True, but found {stop_words_found} in {tokens}"
        
        # Should preserve separators
        assert any("O'brien" in token for token in tokens), f"Expected O'brien to be preserved when preserve_names=True"
        
        # Should have advanced features (morphology, etc.)
        advanced_rules = [trace.rule for trace in result.trace if trace.rule not in ["initial_cleanup", "basic_capitalize"]]
        assert len(advanced_rules) > 0, f"Expected advanced rules when enable_advanced_features=True, but found only: {[trace.rule for trace in result.trace]}"
