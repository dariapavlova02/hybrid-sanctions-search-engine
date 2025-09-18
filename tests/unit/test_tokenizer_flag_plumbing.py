#!/usr/bin/env python3
"""
Unit tests for tokenizer feature-flag plumbing.

Tests that tokenizer flags can be changed per-request and that traces
include tokenizer improvements properly.
"""

import pytest
from unittest.mock import Mock, patch
from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from src.ai_service.utils.feature_flags import FeatureFlags
from src.ai_service.contracts.base_contracts import TokenTrace


class TestTokenizerFlagPlumbing:
    """Test tokenizer feature-flag plumbing functionality."""

    def test_tokenizer_flags_refreshed_per_request(self):
        """Test that tokenizer flags are refreshed from effective_flags before tokenization."""
        # Create factory with initial flags
        factory = NormalizationFactory()
        
        # Set initial tokenizer flags
        factory.tokenizer_service.fix_initials_double_dot = False
        factory.tokenizer_service.preserve_hyphenated_case = False
        
        # Create effective flags with different values
        effective_flags = Mock()
        effective_flags.fix_initials_double_dot = True
        effective_flags.preserve_hyphenated_case = True
        
        # Create config
        config = NormalizationConfig(
            language="ru",
            enable_cache=True,
            remove_stop_words=True,
            preserve_names=True
        )
        
        # Mock the tokenizer service to capture flag updates
        with patch.object(factory.tokenizer_service, 'tokenize') as mock_tokenize:
            mock_tokenize.return_value = Mock(
                tokens=["И..", "Петров"],
                traces=[],
                metadata={},
                token_traces=[]
            )
            
            # Call normalize_text with effective_flags
            import asyncio
            result = asyncio.run(factory.normalize_text("И.. Петров", config, effective_flags))
            
            # Verify flags were updated
            assert factory.tokenizer_service.fix_initials_double_dot == True
            assert factory.tokenizer_service.preserve_hyphenated_case == True

    def test_legacy_env_key_fallback(self):
        """Test that legacy ENV keys are accepted as fallback to AISVC_FLAG_*."""
        with patch.dict('os.environ', {
            'FIX_INITIALS_DOUBLE_DOT': 'true',
            'PRESERVE_HYPHENATED_CASE': 'true'
        }):
            from src.ai_service.utils.feature_flags import FeatureFlagManager
            manager = FeatureFlagManager()
            
            # Verify legacy keys are used as fallback
            assert manager._flags.fix_initials_double_dot == True
            assert manager._flags.preserve_hyphenated_case == True

    def test_tokenizer_improvements_emit_token_traces(self):
        """Test that tokenizer improvements emit TokenTrace objects."""
        # Create factory
        factory = NormalizationFactory()
        
        # Enable tokenizer improvements
        factory.tokenizer_service.fix_initials_double_dot = True
        factory.tokenizer_service.preserve_hyphenated_case = True
        
        # Test double dot collapse
        tokens = ["И..", "Петров"]
        processed_tokens, traces, token_traces = factory.tokenizer_service._apply_post_processing_rules(tokens)
        
        # Verify TokenTrace objects are created
        assert len(token_traces) > 0
        assert all(isinstance(trace, TokenTrace) for trace in token_traces)
        
        # Check for collapse_double_dots trace
        collapse_traces = [t for t in token_traces if t.rule == "collapse_double_dots"]
        assert len(collapse_traces) > 0
        
        # Verify trace content
        collapse_trace = collapse_traces[0]
        assert collapse_trace.token == "И.."
        assert collapse_trace.output == "И."
        assert collapse_trace.role == "tokenizer"
        assert collapse_trace.fallback == False

    def test_hyphen_preservation_emit_token_traces(self):
        """Test that hyphen preservation emits TokenTrace objects."""
        # Create factory
        factory = NormalizationFactory()
        
        # Enable hyphen preservation
        factory.tokenizer_service.preserve_hyphenated_case = True
        
        # Test hyphen preservation
        tokens = ["Петрова-Сидорова"]
        processed_tokens, traces, token_traces = factory.tokenizer_service._apply_post_processing_rules(tokens)
        
        # Verify TokenTrace objects are created
        assert len(token_traces) > 0
        assert all(isinstance(trace, TokenTrace) for trace in token_traces)
        
        # Check for preserve_hyphenated_name trace
        hyphen_traces = [t for t in token_traces if t.rule == "preserve_hyphenated_name"]
        assert len(hyphen_traces) > 0
        
        # Verify trace content
        hyphen_trace = hyphen_traces[0]
        assert hyphen_trace.token == "Петрова-Сидорова"
        assert hyphen_trace.role == "tokenizer"
        assert hyphen_trace.fallback == False

    def test_token_traces_merged_into_final_trace(self):
        """Test that tokenizer token traces are merged into the final trace."""
        # Create factory
        factory = NormalizationFactory()
        
        # Create effective flags
        effective_flags = Mock()
        effective_flags.fix_initials_double_dot = True
        effective_flags.preserve_hyphenated_case = True
        
        # Create config
        config = NormalizationConfig(
            language="ru",
            enable_cache=True,
            remove_stop_words=True,
            preserve_names=True
        )
        
        # Mock tokenizer service to return token traces
        mock_token_traces = [
            TokenTrace(
                token="И..",
                role="tokenizer",
                rule="collapse_double_dots",
                output="И.",
                fallback=False,
                notes="Evidence: initials"
            )
        ]
        
        with patch.object(factory.tokenizer_service, 'tokenize') as mock_tokenize:
            mock_tokenize.return_value = Mock(
                tokens=["И.", "Петров"],
                traces=[],
                metadata={},
                token_traces=mock_token_traces
            )
            
            # Call normalize_text
            import asyncio
            result = asyncio.run(factory.normalize_text("И.. Петров", config, effective_flags))
            
            # Verify token traces are in the final trace
            assert len(result.trace) > 0
            
            # Check for tokenizer traces
            tokenizer_traces = [t for t in result.trace if t.role == "tokenizer"]
            assert len(tokenizer_traces) > 0
            
            # Verify collapse_double_dots trace is present
            collapse_traces = [t for t in tokenizer_traces if t.rule == "collapse_double_dots"]
            assert len(collapse_traces) > 0

    def test_flag_flip_changes_output_and_trace(self):
        """Test that changing flags changes both output and trace."""
        # Create factory
        factory = NormalizationFactory()
        
        # Test with fix_initials_double_dot = False
        factory.tokenizer_service.fix_initials_double_dot = False
        tokens_false, traces_false, token_traces_false = factory.tokenizer_service._apply_post_processing_rules(["И.."])
        
        # Test with fix_initials_double_dot = True
        factory.tokenizer_service.fix_initials_double_dot = True
        tokens_true, traces_true, token_traces_true = factory.tokenizer_service._apply_post_processing_rules(["И.."])
        
        # Verify different outputs
        assert tokens_false[0] == "И.."  # No change when disabled
        assert tokens_true[0] == "И."    # Collapsed when enabled
        
        # Verify different traces
        assert len(token_traces_false) == 0  # No traces when disabled
        assert len(token_traces_true) > 0    # Traces when enabled
        
        # Verify trace content
        if token_traces_true:
            trace = token_traces_true[0]
            assert trace.rule == "collapse_double_dots"
            assert trace.token == "И.."
            assert trace.output == "И."


if __name__ == "__main__":
    pytest.main([__file__])
