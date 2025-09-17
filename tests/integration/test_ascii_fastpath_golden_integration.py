"""
Integration tests for ASCII fastpath with golden test cases.

This module tests ASCII fastpath against golden test cases to ensure
100% semantic compatibility in shadow mode.
"""

import json
import pytest
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.utils.ascii_utils import is_ascii_name


class TestAsciiFastpathGoldenIntegration:
    """Test ASCII fastpath integration with golden test cases."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def golden_cases(self) -> List[Dict[str, Any]]:
        """Load golden test cases."""
        golden_path = Path(__file__).parent.parent / "golden_cases" / "golden_cases.json"
        return json.loads(golden_path.read_text())
    
    @pytest.fixture(scope="class")
    def ascii_golden_cases(self, golden_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter golden cases to ASCII English cases."""
        ascii_cases = []
        for case in golden_cases:
            if case.get("language") == "en" and is_ascii_name(case.get("input", "")):
                ascii_cases.append(case)
        return ascii_cases
    
    def is_fastpath_eligible(self, case: Dict[str, Any]) -> bool:
        """Check if case is eligible for ASCII fastpath."""
        input_text = case.get("input", "")
        
        # Skip cases with complex processing requirements
        if any(keyword in input_text.lower() for keyword in ["dr.", "jr.", "sr.", "mr.", "mrs.", "ms."]):
            return False
        
        # Skip cases with multiple personas (complex parsing)
        expected_personas = case.get("expected_personas", [])
        if len(expected_personas) > 1:
            return False
        
        return True
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_golden_parity(
        self,
        normalization_factory: NormalizationFactory,
        ascii_golden_cases: List[Dict[str, Any]]
    ):
        """Test ASCII fastpath parity with golden test cases."""
        
        eligible_cases = [case for case in ascii_golden_cases if self.is_fastpath_eligible(case)]
        
        if not eligible_cases:
            pytest.skip("No eligible ASCII cases found for fastpath testing")
        
        print(f"Testing {len(eligible_cases)} eligible ASCII cases...")
        
        for case in eligible_cases:
            case_id = case.get("id", "unknown")
            input_text = case.get("input", "")
            language = case.get("language", "en")
            
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
            
            # Run both paths
            fastpath_result = await normalization_factory.normalize_text(input_text, fastpath_config)
            full_result = await normalization_factory.normalize_text(input_text, full_config)
            
            # Validate both succeeded
            assert fastpath_result.success, f"Fastpath failed for case '{case_id}': {fastpath_result.errors}"
            assert full_result.success, f"Full pipeline failed for case '{case_id}': {full_result.errors}"
            
            # Validate basic equivalence
            assert fastpath_result.normalized.lower() == full_result.normalized.lower(), \
                f"Normalized text mismatch for case '{case_id}': fastpath='{fastpath_result.normalized}', full='{full_result.normalized}'"
            
            assert len(fastpath_result.tokens) == len(full_result.tokens), \
                f"Token count mismatch for case '{case_id}': fastpath={len(fastpath_result.tokens)}, full={len(full_result.tokens)}"
            
            # Validate token equivalence (case-insensitive)
            for i, (fp_token, full_token) in enumerate(zip(fastpath_result.tokens, full_result.tokens)):
                assert fp_token.lower() == full_token.lower(), \
                    f"Token {i} mismatch for case '{case_id}': fastpath='{fp_token}', full='{full_token}'"
            
            # Validate confidence (fastpath should have high confidence)
            assert fastpath_result.confidence >= 0.9, \
                f"Fastpath confidence too low for case '{case_id}': {fastpath_result.confidence}"
            
            print(f"✅ Case '{case_id}' passed parity validation")
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_performance_improvement(
        self,
        normalization_factory: NormalizationFactory,
        ascii_golden_cases: List[Dict[str, Any]]
    ):
        """Test that ASCII fastpath provides performance improvement."""
        import time
        
        eligible_cases = [case for case in ascii_golden_cases if self.is_fastpath_eligible(case)]
        
        if not eligible_cases:
            pytest.skip("No eligible ASCII cases found for performance testing")
        
        # Test with first eligible case
        case = eligible_cases[0]
        input_text = case.get("input", "")
        language = case.get("language", "en")
        
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
            await normalization_factory.normalize_text(input_text, fastpath_config)
            end_time = time.perf_counter()
            fastpath_times.append(end_time - start_time)
        
        # Measure full pipeline performance
        full_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            await normalization_factory.normalize_text(input_text, full_config)
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
        
        print(f"Performance improvement for case '{case.get('id', 'unknown')}': {improvement:.1f}% "
              f"({avg_fastpath_time:.4f}s vs {avg_full_time:.4f}s)")
        
        # Should be at least 20% faster
        assert improvement >= 20.0, f"Performance improvement too low: {improvement:.1f}%"
    
    def test_ascii_golden_cases_detection(self, golden_cases: List[Dict[str, Any]]):
        """Test ASCII detection on golden test cases."""
        ascii_cases = []
        non_ascii_cases = []
        
        for case in golden_cases:
            if case.get("language") == "en":
                input_text = case.get("input", "")
                if is_ascii_name(input_text):
                    ascii_cases.append(case)
                else:
                    non_ascii_cases.append(case)
        
        print(f"Found {len(ascii_cases)} ASCII English cases and {len(non_ascii_cases)} non-ASCII English cases")
        
        # Should have some ASCII cases
        assert len(ascii_cases) > 0, "No ASCII English cases found in golden test cases"
        
        # Log some examples
        print("ASCII cases found:")
        for case in ascii_cases[:5]:  # Show first 5
            print(f"  - {case.get('id', 'unknown')}: '{case.get('input', '')}'")
        
        if len(ascii_cases) > 5:
            print(f"  ... and {len(ascii_cases) - 5} more")
    
    def test_fastpath_eligibility_filtering(self, ascii_golden_cases: List[Dict[str, Any]]):
        """Test fastpath eligibility filtering on ASCII cases."""
        eligible_cases = [case for case in ascii_golden_cases if self.is_fastpath_eligible(case)]
        ineligible_cases = [case for case in ascii_golden_cases if not self.is_fastpath_eligible(case)]
        
        print(f"Found {len(eligible_cases)} eligible and {len(ineligible_cases)} ineligible ASCII cases")
        
        # Log examples of ineligible cases
        if ineligible_cases:
            print("Ineligible cases (complex processing required):")
            for case in ineligible_cases[:3]:  # Show first 3
                print(f"  - {case.get('id', 'unknown')}: '{case.get('input', '')}'")
        
        # Should have some eligible cases
        assert len(eligible_cases) > 0, "No eligible ASCII cases found for fastpath testing"
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_error_handling(
        self,
        normalization_factory: NormalizationFactory
    ):
        """Test ASCII fastpath error handling and fallback."""
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
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_configuration_flags(
        self,
        normalization_factory: NormalizationFactory
    ):
        """Test ASCII fastpath configuration flag behavior."""
        text = "John Smith"
        
        # Test with ascii_fastpath=False (should not use fastpath)
        config_disabled = NormalizationConfig(
            language="en",
            ascii_fastpath=False,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        result_disabled = await normalization_factory.normalize_text(text, config_disabled)
        assert result_disabled.success
        assert "ASCII fastpath" not in str(result_disabled.trace), \
            "Should not use ASCII fastpath when disabled"
        
        # Test with ascii_fastpath=True (should use fastpath)
        config_enabled = NormalizationConfig(
            language="en",
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        result_enabled = await normalization_factory.normalize_text(text, config_enabled)
        assert result_enabled.success
        assert "ASCII fastpath" in str(result_enabled.trace), \
            "Should use ASCII fastpath when enabled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
