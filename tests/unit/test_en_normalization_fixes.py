#!/usr/bin/env python3
"""
Unit tests for EN-specific normalization fixes.

Tests the four key behaviors:
1. Preserve hyphenated surnames when nameparser is unavailable
2. Normalize apostrophes to canonical form
3. Filter titles and suffixes when enabled
4. Expand nicknames when enabled
"""

import pytest
import asyncio
from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from src.ai_service.utils.feature_flags import FeatureFlags


class TestENNormalizationFixes:
    """Test EN-specific normalization fixes."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test."""
        self.factory = NormalizationFactory()

    async def test_preserve_hyphenated_surnames_without_nameparser(self):
        """Test that hyphenated surnames are preserved when nameparser is unavailable."""
        # Mock nameparser as unavailable
        with pytest.MonkeyPatch().context() as m:
            m.setattr("src.ai_service.layers.normalization.nameparser_adapter.NAMEPARSER_AVAILABLE", False)
            
            config = NormalizationConfig(
                language="en",
                enable_nameparser_en=True,
                filter_titles_suffixes=True
            )
            flags = FeatureFlags(
                enable_en_nicknames=True,
                filter_titles_suffixes=True
            )

            # Test hyphenated surname preservation
            result = await self.factory.normalize_text("Emily Blunt-Krasinski", config, flags)
            
            # Should preserve hyphenated surname
            assert "Blunt-Krasinski" in result.tokens
            assert "Emily" in result.tokens
            assert len(result.tokens) == 2  # Emily, Blunt-Krasinski

    async def test_normalize_apostrophes_to_canonical_form(self):
        """Test that ASCII apostrophes are normalized to canonical form."""
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            filter_titles_suffixes=True
        )
        flags = FeatureFlags(
            enable_en_nicknames=True,
            filter_titles_suffixes=True
        )

        # Test apostrophe normalization
        result = await self.factory.normalize_text("O'Connor, Sean", config, flags)
        
        # Should normalize apostrophe and reorder name
        assert "O'Connor" in result.tokens or "O'Connor" in result.normalized
        assert "Sean" in result.tokens
        # Check that canonical apostrophe is used
        normalized_text = result.normalized
        assert "'" in normalized_text  # Should contain canonical apostrophe, not ASCII

    async def test_filter_titles_and_suffixes_when_enabled(self):
        """Test that titles and suffixes are filtered when flag is enabled."""
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            filter_titles_suffixes=True  # Enable filtering
        )
        flags = FeatureFlags(
            enable_en_nicknames=True,
            filter_titles_suffixes=True
        )

        # Test title and suffix filtering
        result = await self.factory.normalize_text("Dr. John A. Smith Jr.", config, flags)
        
        # Should filter out title and suffix
        assert "Dr." not in result.tokens
        assert "Jr." not in result.tokens
        assert "John" in result.tokens
        assert "Smith" in result.tokens
        # Middle initial should be preserved (it's not a title/suffix)
        assert "A." in result.tokens

    async def test_expand_nicknames_when_enabled(self):
        """Test that nicknames are expanded when flag is enabled."""
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=True,  # Enable nickname expansion
            filter_titles_suffixes=True
        )
        flags = FeatureFlags(
            enable_en_nicknames=True,
            filter_titles_suffixes=True
        )

        # Test nickname expansion
        result = await self.factory.normalize_text("Bill Gates", config, flags)
        
        # Should expand nickname
        assert "William" in result.tokens or "William" in result.normalized
        assert "Gates" in result.tokens
        # Should not contain the nickname
        assert "Bill" not in result.tokens

    async def test_all_four_behaviors_combined(self):
        """Test all four behaviors working together."""
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=True,
            filter_titles_suffixes=True
        )
        flags = FeatureFlags(
            enable_en_nicknames=True,
            filter_titles_suffixes=True
        )

        # Test complex case with all behaviors
        result = await self.factory.normalize_text("Dr. Bill O'Connor-Smith Jr.", config, flags)
        
        # Should:
        # 1. Preserve hyphenated surname (O'Connor-Smith)
        # 2. Normalize apostrophe (O'Connor)
        # 3. Filter title and suffix (Dr., Jr.)
        # 4. Expand nickname (Bill -> William)
        
        tokens = result.tokens
        normalized = result.normalized
        
        # Check filtering
        assert "Dr." not in tokens
        assert "Jr." not in tokens
        
        # Check nickname expansion
        assert "William" in normalized or "William" in tokens
        
        # Check hyphenated surname preservation
        assert "O'Connor-Smith" in normalized or "O'Connor-Smith" in tokens
        
        # Check apostrophe normalization
        assert "'" in normalized  # Canonical apostrophe

    async def test_disable_title_suffix_filtering(self):
        """Test that titles and suffixes are preserved when filtering is disabled."""
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            filter_titles_suffixes=False  # Disable filtering
        )
        flags = FeatureFlags(
            enable_en_nicknames=True,
            filter_titles_suffixes=False
        )

        # Test with filtering disabled
        result = await self.factory.normalize_text("Dr. John A. Smith Jr.", config, flags)
        
        # Should preserve title and suffix
        assert "Dr." in result.tokens or "Dr." in result.normalized
        assert "Jr." in result.tokens or "Jr." in result.normalized
        assert "John" in result.tokens
        assert "Smith" in result.tokens

    async def test_disable_nickname_expansion(self):
        """Test that nicknames are not expanded when expansion is disabled."""
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=False,  # Disable nickname expansion
            filter_titles_suffixes=True
        )
        flags = FeatureFlags(
            enable_en_nicknames=False,
            filter_titles_suffixes=True
        )

        # Test with nickname expansion disabled
        result = await self.factory.normalize_text("Bill Gates", config, flags)
        
        # Should preserve nickname
        assert "Bill" in result.tokens
        assert "Gates" in result.tokens
        # Should not expand to William
        assert "William" not in result.tokens
        assert "William" not in result.normalized


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
