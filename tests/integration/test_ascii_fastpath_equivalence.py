"""
Golden tests for ASCII fastpath equivalence validation.

These tests run both ASCII fastpath and full normalization pipeline
in shadow mode to prove equivalence for ASCII names.
"""

import pytest
import asyncio
from typing import List, Tuple, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.utils.ascii_utils import (
    is_ascii_name, 
    ascii_fastpath_normalize,
    validate_ascii_fastpath_equivalence
)


class TestAsciiFastpathEquivalence:
    """Test ASCII fastpath equivalence with full normalization pipeline."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def ascii_test_cases(self) -> List[Dict[str, Any]]:
        """ASCII test cases for equivalence validation."""
        return [
            {
                "text": "John Smith",
                "language": "en",
                "expected_tokens": ["John", "Smith"],
                "expected_roles": ["given", "surname"],
                "description": "Simple English name"
            },
            {
                "text": "Mary-Jane Watson",
                "language": "en", 
                "expected_tokens": ["Mary-Jane", "Watson"],
                "expected_roles": ["given", "surname"],
                "description": "Hyphenated first name"
            },
            {
                "text": "J. R. R. Tolkien",
                "language": "en",
                "expected_tokens": ["J.", "R.", "R.", "Tolkien"],
                "expected_roles": ["initial", "initial", "initial", "surname"],
                "description": "Name with initials"
            },
            {
                "text": "O'Connor",
                "language": "en",
                "expected_tokens": ["O'Connor"],
                "expected_roles": ["surname"],
                "description": "Name with apostrophe"
            },
            {
                "text": "Elizabeth Taylor",
                "language": "en",
                "expected_tokens": ["Elizabeth", "Taylor"],
                "expected_roles": ["given", "surname"],
                "description": "Common English name"
            },
            {
                "text": "Michael O'Brien",
                "language": "en",
                "expected_tokens": ["Michael", "O'Brien"],
                "expected_roles": ["given", "surname"],
                "description": "Name with Irish surname"
            },
            {
                "text": "Dr. Sarah Johnson",
                "language": "en",
                "expected_tokens": ["Dr.", "Sarah", "Johnson"],
                "expected_roles": ["initial", "given", "surname"],
                "description": "Name with title"
            },
            {
                "text": "Robert Smith Jr.",
                "language": "en",
                "expected_tokens": ["Robert", "Smith", "Jr."],
                "expected_roles": ["given", "surname", "initial"],
                "description": "Name with suffix"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_equivalence_shadow_mode(
        self, 
        normalization_factory: NormalizationFactory,
        ascii_test_cases: List[Dict[str, Any]]
    ):
        """Test ASCII fastpath equivalence in shadow mode."""
        
        for test_case in ascii_test_cases:
            text = test_case["text"]
            language = test_case["language"]
            
            # Skip if not ASCII
            if not is_ascii_name(text):
                pytest.skip(f"Text '{text}' is not ASCII")
            
            # Create configs for both paths
            fastpath_config = NormalizationConfig(
                language=language,
                ascii_fastpath=True,
                enable_advanced_features=False,
                enable_morphology=False
            )
            
            full_config = NormalizationConfig(
                language=language,
                ascii_fastpath=False,
                enable_advanced_features=True,
                enable_morphology=True
            )
            
            # Run both paths
            fastpath_result = await normalization_factory.normalize_text(text, fastpath_config)
            full_result = await normalization_factory.normalize_text(text, full_config)
            
            # Validate equivalence
            assert fastpath_result.success, f"Fastpath failed for '{text}': {fastpath_result.errors}"
            assert full_result.success, f"Full pipeline failed for '{text}': {full_result.errors}"
            
            # Check basic equivalence
            assert fastpath_result.normalized.lower() == full_result.normalized.lower(), \
                f"Normalized text mismatch for '{text}': fastpath='{fastpath_result.normalized}', full='{full_result.normalized}'"
            
            assert len(fastpath_result.tokens) == len(full_result.tokens), \
                f"Token count mismatch for '{text}': fastpath={len(fastpath_result.tokens)}, full={len(full_result.tokens)}"
            
            # Check token equivalence (case-insensitive)
            for i, (fp_token, full_token) in enumerate(zip(fastpath_result.tokens, full_result.tokens)):
                assert fp_token.lower() == full_token.lower(), \
                    f"Token {i} mismatch for '{text}': fastpath='{fp_token}', full='{full_token}'"
            
            # Check confidence (fastpath should have high confidence)
            assert fastpath_result.confidence >= 0.9, \
                f"Fastpath confidence too low for '{text}': {fastpath_result.confidence}"
            
            # Log equivalence success
            print(f"✓ ASCII fastpath equivalence validated for '{text}'")
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_performance_improvement(
        self,
        normalization_factory: NormalizationFactory
    ):
        """Test that ASCII fastpath is faster than full pipeline."""
        import time
        
        text = "John Michael Smith"
        language = "en"
        
        # Create configs
        fastpath_config = NormalizationConfig(
            language=language,
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        full_config = NormalizationConfig(
            language=language,
            ascii_fastpath=False,
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        # Measure fastpath performance
        fastpath_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            await normalization_factory.normalize_text(text, fastpath_config)
            end_time = time.perf_counter()
            fastpath_times.append(end_time - start_time)
        
        # Measure full pipeline performance
        full_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            await normalization_factory.normalize_text(text, full_config)
            end_time = time.perf_counter()
            full_times.append(end_time - start_time)
        
        # Calculate averages
        avg_fastpath_time = sum(fastpath_times) / len(fastpath_times)
        avg_full_time = sum(full_times) / len(full_times)
        
        # Fastpath should be faster
        assert avg_fastpath_time < avg_full_time, \
            f"Fastpath not faster: {avg_fastpath_time:.4f}s vs {avg_full_time:.4f}s"
        
        # Calculate improvement percentage
        improvement = (avg_full_time - avg_fastpath_time) / avg_full_time * 100
        
        print(f"ASCII fastpath performance improvement: {improvement:.1f}% "
              f"({avg_fastpath_time:.4f}s vs {avg_full_time:.4f}s)")
        
        # Should be at least 20% faster
        assert improvement >= 20.0, f"Performance improvement too low: {improvement:.1f}%"
    
    def test_ascii_detection_accuracy(self):
        """Test ASCII name detection accuracy."""
        # Valid ASCII names
        valid_ascii_names = [
            "John Smith",
            "Mary-Jane Watson",
            "J. R. R. Tolkien",
            "O'Connor",
            "Dr. Sarah Johnson",
            "Robert Smith Jr.",
            "Michael O'Brien",
            "Elizabeth Taylor"
        ]
        
        for name in valid_ascii_names:
            assert is_ascii_name(name), f"Should detect '{name}' as ASCII name"
        
        # Invalid ASCII names
        invalid_ascii_names = [
            "Иван Петров",  # Cyrillic
            "玛丽",  # Chinese
            "José García",  # Non-ASCII characters
            "123456",  # Numbers only
            "A",  # Too short
            "A" * 101,  # Too long
            "John@Smith",  # Invalid characters
            "",  # Empty
            "   ",  # Whitespace only
        ]
        
        for name in invalid_ascii_names:
            assert not is_ascii_name(name), f"Should not detect '{name}' as ASCII name"
    
    def test_ascii_fastpath_normalize_basic(self):
        """Test basic ASCII fastpath normalization."""
        test_cases = [
            ("John Smith", "en", ["John", "Smith"], ["given", "surname"]),
            ("MARY JANE", "en", ["Mary", "Jane"], ["given", "given"]),
            ("j. r. r. tolkien", "en", ["J.", "R.", "R.", "Tolkien"], ["initial", "initial", "initial", "surname"]),
        ]
        
        for text, language, expected_tokens, expected_roles in test_cases:
            tokens, roles, normalized = ascii_fastpath_normalize(text, language)
            
            assert tokens == expected_tokens, f"Token mismatch for '{text}': {tokens} vs {expected_tokens}"
            assert roles == expected_roles, f"Role mismatch for '{text}': {roles} vs {expected_roles}"
            assert normalized == " ".join(expected_tokens), f"Normalized mismatch for '{text}': {normalized}"
    
    def test_ascii_fastpath_validation(self):
        """Test ASCII fastpath validation function."""
        # Test equivalent results
        text = "John Smith"
        fastpath_result = (["John", "Smith"], ["given", "surname"], "John Smith")
        full_result = (["John", "Smith"], ["given", "surname"], "John Smith")
        
        assert validate_ascii_fastpath_equivalence(text, fastpath_result, full_result), \
            "Should validate equivalent results"
        
        # Test non-equivalent results
        different_result = (["John", "Smith"], ["surname", "given"], "John Smith")
        
        assert not validate_ascii_fastpath_equivalence(text, fastpath_result, different_result), \
            "Should not validate different results"
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_fallback(self, normalization_factory: NormalizationFactory):
        """Test ASCII fastpath fallback to full pipeline on error."""
        # Test with non-ASCII text (should fallback)
        text = "Иван Петров"  # Cyrillic text
        
        config = NormalizationConfig(
            language="ru",
            ascii_fastpath=True,
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await normalization_factory.normalize_text(text, config)
        
        # Should succeed with fallback
        assert result.success, f"Fallback should succeed for '{text}': {result.errors}"
        
        # Should not use ASCII fastpath
        assert "ASCII fastpath" not in str(result.trace), \
            "Should not use ASCII fastpath for non-ASCII text"
    
    def test_ascii_fastpath_configuration(self, normalization_factory: NormalizationFactory):
        """Test ASCII fastpath configuration options."""
        # Test with ascii_fastpath=False (should not use fastpath)
        config = NormalizationConfig(
            language="en",
            ascii_fastpath=False,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        # Should not be eligible for fastpath
        assert not normalization_factory._is_ascii_fastpath_eligible("John Smith", config), \
            "Should not be eligible when ascii_fastpath=False"
        
        # Test with ascii_fastpath=True (should use fastpath)
        config.ascii_fastpath = True
        
        assert normalization_factory._is_ascii_fastpath_eligible("John Smith", config), \
            "Should be eligible when ascii_fastpath=True"
        
        # Test with non-English language (should not use fastpath)
        config.language = "ru"
        
        assert not normalization_factory._is_ascii_fastpath_eligible("John Smith", config), \
            "Should not be eligible for non-English language"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
