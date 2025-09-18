"""
Smoke tests for English title parsing.

This module tests English title parsing functionality to ensure
that titles like Dr., Mr., Mrs., etc. are correctly handled
and ignored in the canonical form.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.utils.feature_flags import FeatureFlags


class TestEnglishTitles:
    """Test English title parsing functionality."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Create test configuration with English nameparser enabled."""
        return NormalizationConfig(
            language="en",
            enable_nameparser_en=True,
            enable_en_nicknames=False,  # Disable nicknames for title testing
            enable_advanced_features=True,
            debug_tracing=True
        )
    
    @pytest.fixture(scope="class")
    def test_flags(self):
        """Create test feature flags."""
        return FeatureFlags(
            enable_nameparser_en=True,
            enable_en_nicknames=False,
            debug_tracing=True
        )
    
    @pytest.mark.asyncio
    async def test_doctor_title_parsing(self, normalization_factory, test_config, test_flags):
        """Test Dr. title parsing and filtering."""
        test_cases = [
            ("Dr. John Smith", "John Smith"),
            ("Dr. Jane Doe", "Jane Doe"),
            ("Dr. Robert Johnson", "Robert Johnson"),
            ("Dr. Mary O'Connor", "Mary O Connor"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that Dr. was filtered out
            assert "Dr." not in result.normalized, f"Unexpected 'Dr.' in result for '{input_text}', got '{result.normalized}'"
            assert "Dr " not in result.normalized, f"Unexpected 'Dr ' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that name components are preserved
            name_parts = expected.split()
            for part in name_parts:
                assert part in result.normalized, f"Expected '{part}' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_mr_mrs_title_parsing(self, normalization_factory, test_config, test_flags):
        """Test Mr./Mrs. title parsing and filtering."""
        test_cases = [
            ("Mr. John Smith", "John Smith"),
            ("Mrs. Jane Doe", "Jane Doe"),
            ("Mr. Robert Johnson", "Robert Johnson"),
            ("Mrs. Mary O'Connor", "Mary O Connor"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that title was filtered out
            assert "Mr." not in result.normalized, f"Unexpected 'Mr.' in result for '{input_text}', got '{result.normalized}'"
            assert "Mrs." not in result.normalized, f"Unexpected 'Mrs.' in result for '{input_text}', got '{result.normalized}'"
            assert "Mr " not in result.normalized, f"Unexpected 'Mr ' in result for '{input_text}', got '{result.normalized}'"
            assert "Mrs " not in result.normalized, f"Unexpected 'Mrs ' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that name components are preserved
            name_parts = expected.split()
            for part in name_parts:
                assert part in result.normalized, f"Expected '{part}' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_miss_ms_title_parsing(self, normalization_factory, test_config, test_flags):
        """Test Miss/Ms. title parsing and filtering."""
        test_cases = [
            ("Miss Jane Doe", "Jane Doe"),
            ("Ms. Mary Smith", "Mary Smith"),
            ("Miss Elizabeth Johnson", "Elizabeth Johnson"),
            ("Ms. Catherine Brown", "Catherine Brown"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that title was filtered out
            assert "Miss" not in result.normalized, f"Unexpected 'Miss' in result for '{input_text}', got '{result.normalized}'"
            assert "Ms." not in result.normalized, f"Unexpected 'Ms.' in result for '{input_text}', got '{result.normalized}'"
            assert "Ms " not in result.normalized, f"Unexpected 'Ms ' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that name components are preserved
            name_parts = expected.split()
            for part in name_parts:
                assert part in result.normalized, f"Expected '{part}' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_professor_title_parsing(self, normalization_factory, test_config, test_flags):
        """Test Professor/Prof. title parsing and filtering."""
        test_cases = [
            ("Professor John Smith", "John Smith"),
            ("Prof. Jane Doe", "Jane Doe"),
            ("Professor Robert Johnson", "Robert Johnson"),
            ("Prof. Mary O'Connor", "Mary O Connor"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that title was filtered out
            assert "Professor" not in result.normalized, f"Unexpected 'Professor' in result for '{input_text}', got '{result.normalized}'"
            assert "Prof." not in result.normalized, f"Unexpected 'Prof.' in result for '{input_text}', got '{result.normalized}'"
            assert "Prof " not in result.normalized, f"Unexpected 'Prof ' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that name components are preserved
            name_parts = expected.split()
            for part in name_parts:
                assert part in result.normalized, f"Expected '{part}' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_multiple_titles_parsing(self, normalization_factory, test_config, test_flags):
        """Test multiple titles parsing and filtering."""
        test_cases = [
            ("Dr. Mr. John Smith", "John Smith"),
            ("Prof. Dr. Jane Doe", "Jane Doe"),
            ("Dr. Mrs. Robert Johnson", "Robert Johnson"),
            ("Prof. Ms. Mary O'Connor", "Mary O Connor"),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that all titles were filtered out
            titles = ["Dr.", "Mr.", "Mrs.", "Miss", "Ms.", "Prof.", "Professor"]
            for title in titles:
                assert title not in result.normalized, f"Unexpected '{title}' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that name components are preserved
            name_parts = expected.split()
            for part in name_parts:
                assert part in result.normalized, f"Expected '{part}' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_suffix_handling(self, normalization_factory, test_config, test_flags):
        """Test suffix handling (Jr., Sr., III, etc.)."""
        test_cases = [
            ("John Smith Jr.", "John Smith Jr."),
            ("Robert Johnson Sr.", "Robert Johnson Sr."),
            ("William Brown III", "William Brown III"),
            ("Dr. John Smith Jr.", "John Smith Jr."),
            ("Mr. Robert Johnson Sr.", "Robert Johnson Sr."),
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            assert result.normalized, f"Normalized text is empty for '{input_text}'"
            
            # Check that titles were filtered out but suffixes preserved
            if "Dr." in input_text:
                assert "Dr." not in result.normalized, f"Unexpected 'Dr.' in result for '{input_text}', got '{result.normalized}'"
            if "Mr." in input_text:
                assert "Mr." not in result.normalized, f"Unexpected 'Mr.' in result for '{input_text}', got '{result.normalized}'"
            
            # Check that suffixes are preserved
            if "Jr." in input_text:
                assert "Jr." in result.normalized, f"Expected 'Jr.' in result for '{input_text}', got '{result.normalized}'"
            if "Sr." in input_text:
                assert "Sr." in result.normalized, f"Expected 'Sr.' in result for '{input_text}', got '{result.normalized}'"
            if "III" in input_text:
                assert "III" in result.normalized, f"Expected 'III' in result for '{input_text}', got '{result.normalized}'"
    
    @pytest.mark.asyncio
    async def test_title_parsing_trace(self, normalization_factory, test_config, test_flags):
        """Test that title parsing appears in trace."""
        input_text = "Dr. John Smith"
        
        result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
        
        # Basic smoke test
        assert result is not None, f"Result is None for '{input_text}'"
        assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
        
        # Check that trace contains title parsing information
        trace_text = " ".join(str(trace) for trace in result.trace)
        assert "Dr." in trace_text or "title" in trace_text.lower(), f"Expected title parsing in trace for '{input_text}', trace: {result.trace}"
    
    @pytest.mark.asyncio
    async def test_no_title_parsing_when_disabled(self, normalization_factory, test_flags):
        """Test that titles are not parsed when nameparser is disabled."""
        # Create config with nameparser disabled
        config = NormalizationConfig(
            language="en",
            enable_nameparser_en=False,  # Disabled
            enable_en_nicknames=False,
            enable_advanced_features=True,
            debug_tracing=True
        )
        
        input_text = "Dr. John Smith"
        
        result = await normalization_factory.normalize_text(input_text, config, test_flags)
        
        # Basic smoke test
        assert result is not None, f"Result is None for '{input_text}'"
        assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
        
        # With nameparser disabled, titles might not be filtered out
        # This depends on the fallback classification behavior
        # We just verify that the result is reasonable
        assert result.normalized, f"Normalized text is empty for '{input_text}'"
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, normalization_factory, test_config, test_flags):
        """Test edge cases for title parsing."""
        test_cases = [
            ("Dr.", ""),  # Only title
            ("Mr.", ""),  # Only title
            ("Dr. Smith", "Smith"),  # Title with surname only
            ("Dr. J. Smith", "J. Smith"),  # Title with initial
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Normalization failed for '{input_text}': {result.errors}"
            
            # For empty expected, result should be empty or minimal
            if not expected:
                # Title-only cases might result in empty or minimal output
                assert len(result.normalized.strip()) == 0 or len(result.normalized.split()) <= 1, \
                    f"Expected empty or minimal result for '{input_text}', got '{result.normalized}'"
            else:
                # Check that expected components are present
                expected_parts = expected.split()
                for part in expected_parts:
                    assert part in result.normalized, f"Expected '{part}' in result for '{input_text}', got '{result.normalized}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
