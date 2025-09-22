"""
Smoke tests for English nickname resolution.

This module tests English nickname expansion functionality to ensure
that nicknames like Bill, Bob, etc. are correctly expanded to their
full forms like William, Robert, etc.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.utils.feature_flags import FeatureFlags


class TestEnglishNicknames:
    """Test English nickname resolution functionality."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Create test configuration with English nickname resolution enabled."""
        return NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=True,
            enable_advanced_features=True,
            debug_tracing=True
        )
    
    @pytest.fixture(scope="class")
    def test_flags(self):
        """Create test feature flags."""
        return FeatureFlags(
            enable_nameparser_en=True,
            enable_en_nicknames=True,
            debug_tracing=True
        )
    
    @pytest.mark.asyncio
    async def test_bill_gates_to_william_gates(self, normalization_factory, test_config, test_flags):
        """Test Bill Gates → William Gates nickname expansion."""
        test_cases = [
            ("Bill Gates", "William Gates"),
            ("bill gates", "William Gates"),
            ("BILL GATES", "William Gates"),
            ("Bill R. Gates", "William R. Gates"),
            ("Dr. Bill Gates", "Dr. William Gates"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that Bill was expanded to William
            assert "William" in result.normalized, f"Expected 'William' in result for '{input_text}', got '{result.normalized}'"
            assert "Bill" not in result.normalized, f"Unexpected 'Bill' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that Gates is preserved
            assert "Gates" in result.normalized, f"Expected 'Gates' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_bob_robert_expansion(self, normalization_factory, test_config, test_flags):
        """Test Bob → Robert nickname expansion."""
        test_cases = [
            ("Bob Smith", "Robert Smith"),
            ("bob smith", "Robert Smith"),
            ("BOB SMITH", "Robert Smith"),
            ("Bob R. Smith", "Robert R. Smith"),
            ("Mr. Bob Smith", "Mr. Robert Smith"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that Bob was expanded to Robert
            assert "Robert" in result.normalized, f"Expected 'Robert' in result for '{input_text}', got '{result.normalized}'"
            assert "Bob" not in result.normalized, f"Unexpected 'Bob' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that Smith is preserved
            assert "Smith" in result.normalized, f"Expected 'Smith' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_multiple_nickname_expansions(self, normalization_factory, test_config, test_flags):
        """Test multiple nickname expansions in one name."""
        test_cases = [
            ("Bill Bob Johnson", "William Robert Johnson"),
            ("Bob Bill Smith", "Robert William Smith"),
            ("Jim Bob Wilson", "James Robert Wilson"),
            ("Bill Jim Bob Davis", "William James Robert Davis"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that all nicknames were expanded
            if "Bill" in input_text:
                assert "William" in result.normalized, f"Expected 'William' in result for '{input_text}', got '{result.normalized}'"
                assert "Bill" not in result.normalized, f"Unexpected 'Bill' in result for '{input_text}', got '{result.normalized}'"
            
            if "Bob" in input_text:
                assert "Robert" in result.normalized, f"Expected 'Robert' in result for '{input_text}', got '{result.normalized}'"
                assert "Bob" not in result.normalized, f"Unexpected 'Bob' in result for '{input_text}', got '{result.normalized}'"
            
            if "Jim" in input_text:
                assert "James" in result.normalized, f"Expected 'James' in result for '{input_text}', got '{result.normalized}'"
                assert "Jim" not in result.normalized, f"Unexpected 'Jim' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_nickname_resolution_trace(self, normalization_factory, test_config, test_flags):
        """Test that nickname resolution appears in trace."""
        input_text = "Bill Gates"
        
        result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
        
        # Basic smoke test
        assert result is not None, f"Result is None for '{input_text}'"
        assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
        
        # Check that trace contains nickname resolution
        trace_text = " ".join(str(trace) for trace in result.trace)
        assert "nickname.resolved" in trace_text, f"Expected 'nickname.resolved' in trace for '{input_text}', trace: {result.trace}"
        assert "Bill" in trace_text, f"Expected 'Bill' in trace for '{input_text}', trace: {result.trace}"
        assert "William" in trace_text, f"Expected 'William' in trace for '{input_text}', trace: {result.trace}"
    
    @pytest.mark.asyncio
    async def test_no_nickname_expansion_when_disabled(self, normalization_factory):
        """Test that nicknames are not expanded when feature is disabled."""
        # Create config with nickname resolution disabled
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=False,  # Disabled
            enable_advanced_features=True,
            debug_tracing=True
        )

        # Create flags with nickname resolution disabled
        disabled_flags = FeatureFlags(
            enable_nameparser_en=True,
            enable_en_nicknames=False,  # Disabled
            debug_tracing=True
        )

        input_text = "Bill Gates"

        result = await normalization_factory.normalize_text(input_text, config, disabled_flags)
        
        # Basic smoke test
        assert result is not None, f"Result is None for '{input_text}'"
        assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
        
        # Check that Bill was NOT expanded to William
        assert "Bill" in result.normalized, f"Expected 'Bill' to remain unchanged for '{input_text}', got '{result.normalized}'"
        assert "William" not in result.normalized, f"Unexpected 'William' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_parity_with_nickname_expansion_disabled(self, normalization_factory):
        """Test that parity is maintained when nickname expansion is disabled."""
        # Test with nickname expansion enabled
        config_enabled = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=True,
            enable_advanced_features=True,
            debug_tracing=True
        )

        flags_enabled = FeatureFlags(
            enable_nameparser_en=True,
            enable_en_nicknames=True,
            debug_tracing=True
        )

        # Test with nickname expansion disabled
        config_disabled = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=False,
            enable_advanced_features=True,
            debug_tracing=True
        )

        flags_disabled = FeatureFlags(
            enable_nameparser_en=True,
            enable_en_nicknames=False,
            debug_tracing=True
        )

        test_cases = [
            "John Smith",  # No nickname
            "Robert Johnson",  # No nickname
            "Michael Brown",  # No nickname
        ]

        for input_text in test_cases:
            result_enabled = await normalization_factory.normalize_text(input_text, config_enabled, flags_enabled)
            result_disabled = await normalization_factory.normalize_text(input_text, config_disabled, flags_disabled)
            
            # Both should succeed
            assert result_enabled.success, f"Enabled config failed for '{input_text}': {result_enabled.errors}"
            assert result_disabled.success, f"Disabled config failed for '{input_text}': {result_disabled.errors}"
            
            # Results should be identical for non-nickname names
            assert result_enabled.normalized == result_disabled.normalized, \
                f"Results differ for '{input_text}': enabled='{result_enabled.normalized}', disabled='{result_disabled.normalized}'"
    
    @pytest.mark.asyncio
    async def test_female_nickname_expansions(self, normalization_factory, test_config, test_flags):
        """Test female nickname expansions."""
        test_cases = [
            ("Beth Johnson", "Elizabeth Johnson"),
            ("beth johnson", "Elizabeth Johnson"),
            ("Betty Smith", "Elizabeth Smith"),
            ("Liz Wilson", "Elizabeth Wilson"),
            ("Kate Brown", "Catherine Brown"),
            ("Katie Davis", "Katherine Davis"),
            ("Sue Miller", "Susan Miller"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that nickname was expanded
            if "Beth" in input_text or "Betty" in input_text or "Liz" in input_text:
                assert "Elizabeth" in result.normalized, f"Expected 'Elizabeth' in result for '{input_text}', got '{result.normalized}'"
            
            if "Kate" in input_text:
                assert "Catherine" in result.normalized, f"Expected 'Catherine' in result for '{input_text}', got '{result.normalized}'"
            if "Katie" in input_text:
                assert "Katherine" in result.normalized, f"Expected 'Katherine' in result for '{input_text}', got '{result.normalized}'"
            
            if "Sue" in input_text:
                assert "Susan" in result.normalized, f"Expected 'Susan' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, normalization_factory, test_config, test_flags):
        """Test edge cases for nickname resolution."""
        test_cases = [
            ("Bill", "William"),  # Single name
            ("Bob", "Robert"),    # Single name
            ("Bill-Bob Smith", "William Robert Smith"),  # Hyphenated nicknames
            ("O'Bill Smith", "O William Smith"),  # Apostrophe with nickname
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            
            # For single names, check that nickname was expanded
            if input_text in ["Bill", "Bob"]:
                assert expected in result.normalized, f"Expected '{expected}' in result for '{input_text}', got '{result.normalized}'"
            
            # For hyphenated names, check that both nicknames were expanded
            if "Bill-Bob" in input_text:
                assert "William Robert" in result.normalized, f"Expected 'William Robert' in result for '{input_text}', got '{result.normalized}'"
            
            # For apostrophe names, check that nickname was expanded
            if "O'Bill" in input_text:
                assert "O William" in result.normalized, f"Expected 'O William' in result for '{input_text}', got '{result.normalized}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
