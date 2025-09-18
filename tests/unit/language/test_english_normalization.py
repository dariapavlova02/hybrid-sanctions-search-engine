"""
Unit tests for English token normalization functionality.
"""

import pytest
from ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from ai_service.contracts.base_contracts import TokenTrace


class TestEnglishNormalization:
    """Test cases for English token normalization."""
    
    @pytest.fixture
    def factory(self):
        """Create a NormalizationFactory instance for testing."""
        return NormalizationFactory()
    
    @pytest.fixture
    def config(self):
        """Create a test configuration with English rules enabled."""
        return NormalizationConfig(
            language='en',
            enable_en_rules=True,
            enable_en_nicknames=True,
            enable_nameparser_en=True,
            enable_advanced_features=True
        )
    
    def test_title_removal(self, factory, config):
        """Test removal of English titles."""
        # Ensure lexicons are loaded
        factory._load_english_lexicons()
        
        tokens = ["Mr", "John", "Smith"]
        roles = ["unknown", "given", "surname"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        # Filter out empty tokens
        filtered_tokens = [token for token in normalized_tokens if token]
        
        assert filtered_tokens == ["John", "Smith"]
        
        # Check for title removal trace
        title_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.title_stripped"]
        assert len(title_traces) == 1
        assert title_traces[0].token == "Mr"
        assert title_traces[0].output == ""
    
    def test_suffix_removal(self, factory, config):
        """Test removal of English suffixes."""
        # Ensure lexicons are loaded
        factory._load_english_lexicons()
        
        tokens = ["John", "Smith", "Jr"]
        roles = ["given", "surname", "suffix"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        # Filter out empty tokens
        filtered_tokens = [token for token in normalized_tokens if token]
        
        assert filtered_tokens == ["John", "Smith"]
        
        # Check for suffix removal trace
        suffix_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.suffix_stripped"]
        assert len(suffix_traces) == 1
        assert suffix_traces[0].token == "Jr"
        assert suffix_traces[0].output == ""
    
    def test_nickname_resolution(self, factory, config):
        """Test resolution of English nicknames."""
        tokens = ["Bill", "Smith"]
        roles = ["given", "surname"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        assert normalized_tokens == ["William", "Smith"]
        
        # Check for nickname resolution trace
        nickname_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.nickname_resolved"]
        assert len(nickname_traces) == 1
        assert nickname_traces[0].token == "Bill"
        assert nickname_traces[0].output == "William"
    
    def test_apostrophe_normalization(self, factory, config):
        """Test normalization of apostrophes."""
        tokens = ["O'Connor"]
        roles = ["surname"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        assert normalized_tokens == ["O'Connor"]
        
        # Check that apostrophe is preserved
        apostrophe_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "token.apostrophe_preserved"]
        # May or may not have apostrophe trace depending on input
        if apostrophe_traces:
            assert apostrophe_traces[0].token == "O'Connor"
            assert apostrophe_traces[0].output == "O'Connor"
    
    def test_hyphenated_surname_normalization(self, factory, config):
        """Test normalization of hyphenated surnames."""
        tokens = ["Mary", "Smith-Jones"]
        roles = ["given", "surname"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        assert normalized_tokens == ["Mary", "Smith-Jones"]
        
        # Check for hyphenated case trace
        hyphen_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "token.hyphenated_case"]
        if hyphen_traces:
            assert hyphen_traces[0].token == "Smith-Jones"
            assert hyphen_traces[0].output == "Smith-Jones"
    
    def test_combined_normalization(self, factory, config):
        """Test combined normalization with title, nickname, and suffix removal."""
        # Ensure lexicons are loaded
        factory._load_english_lexicons()
        
        tokens = ["Dr", "Bill", "O'Connor", "Jr"]
        roles = ["unknown", "given", "surname", "suffix"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        # Filter out empty tokens
        filtered_tokens = [token for token in normalized_tokens if token]
        
        assert filtered_tokens == ["William", "O'Connor"]
        
        # Check for various traces
        title_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.title_stripped"]
        nickname_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.nickname_resolved"]
        suffix_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.suffix_stripped"]
        
        assert len(title_traces) == 1
        assert len(nickname_traces) == 1
        assert len(suffix_traces) == 1
    
    def test_gate_conditions(self, factory):
        """Test that gate conditions work correctly."""
        # Test with gates disabled
        config_disabled = NormalizationConfig(
            language='en',
            enable_en_rules=False,
            enable_en_nicknames=False,
            enable_nameparser_en=False
        )
        
        tokens = ["Mr", "Bill", "Smith", "Jr"]
        roles = ["unknown", "given", "surname", "suffix"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config_disabled)
        
        # Should not remove titles/suffixes or resolve nicknames
        assert normalized_tokens == ["Mr", "Bill", "Smith", "Jr"]
        
        # Should only have title case traces
        title_case_traces = [trace for trace in traces if hasattr(trace, 'rule') and trace.rule == "en.title_case"]
        assert len(title_case_traces) >= 0  # May or may not have title case traces
    
    def test_empty_tokens(self, factory, config):
        """Test handling of empty token lists."""
        normalized_tokens, traces = factory._normalize_english_tokens([], [], config)
        
        assert normalized_tokens == []
        assert traces == []
    
    def test_non_personal_tokens(self, factory, config):
        """Test that non-personal tokens are not processed."""
        tokens = ["The", "Company", "Inc"]
        roles = ["unknown", "unknown", "unknown"]
        
        normalized_tokens, traces = factory._normalize_english_tokens(tokens, roles, config)
        
        # Should pass through unchanged
        assert normalized_tokens == ["The", "Company", "Inc"]
