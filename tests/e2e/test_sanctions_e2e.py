"""
End-to-end tests for sanctions processing.

This module tests the complete sanctions processing pipeline
from input to output.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


class TestSanctionsE2E:
    """Test sanctions end-to-end processing."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Create test configuration."""
        return NormalizationConfig(
            language="ru",
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True,
            debug_tracing=True
        )
    
    @pytest.fixture(scope="class")
    def test_flags(self):
        """Create test feature flags."""
        return FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
    
    @pytest.fixture(scope="class")
    def sanctions_cases(self):
        """Create sanctions test cases."""
        return [
            # Russian names
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна",
            "А. Б. Сидоров",
            "И. П. Козлов",
            "Мария-Анна Петрова",
            "О'Коннор",
            
            # Ukrainian names
            "Олександр Коваленко",
            "Наталія Шевченко",
            "Михайло Іванович",
            "Оксана Петрівна",
            "А. Б. Коваленко",
            "І. П. Шевченко",
            "Марія-Оксана Коваленко",
            "О'Коннор",
            
            # English names
            "John Smith",
            "Jane Doe",
            "Dr. Robert Johnson",
            "Mary O'Connor",
            "A. B. Smith",
            "J. P. Doe",
            "Mary-Jane Smith",
            "Jean-Pierre Dubois",
            
            # Complex names
            "Jean-Pierre Dubois",
            "Maria José García",
            "Анна-Мария Петрова",
            "John-Paul Smith",
            
            # Edge cases
            "A. B. C.",
            "Dr. Prof. Smith",
            "Mary-Jane O'Connor-Smith",
            "Іван Петрович Сидоренко"
        ]
    
    @pytest.mark.asyncio
    async def test_sanctions_processing_pipeline(self, normalization_factory, test_config, test_flags, sanctions_cases):
        """Test complete sanctions processing pipeline."""
        results = []
        
        for case in sanctions_cases:
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Store result for analysis
            results.append({
                "input": case,
                "result": result,
                "success": result.success if result else False
            })
            
            # Basic E2E test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'success'), f"Result missing success attribute for '{case}'"
            assert hasattr(result, 'normalized'), f"Result missing normalized attribute for '{case}'"
            assert hasattr(result, 'tokens'), f"Result missing tokens attribute for '{case}'"
            
            # Should be successful
            assert result.success, f"Sanctions processing failed for '{case}': {result.errors}"
            
            # Should have normalized text
            assert result.normalized, f"Normalized text is empty for '{case}'"
            
            # Should have tokens
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
        
        # Analyze results
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        success_rate = successful / total if total > 0 else 0.0
        
        # Should have high success rate
        assert success_rate >= 0.95, f"Sanctions processing success rate too low: {success_rate:.1%} < 95%"
    
    @pytest.mark.asyncio
    async def test_sanctions_accuracy(self, normalization_factory, test_config, test_flags, sanctions_cases):
        """Test sanctions processing accuracy."""
        # Test cases with expected outputs
        test_cases = [
            ("Иван Петров", "Иван Петров"),
            ("Анна Сидорова", "Анна Сидорова"),
            ("John Smith", "John Smith"),
            ("Jane Doe", "Jane Doe"),
            ("Олександр Коваленко", "Олександр Коваленко"),
            ("Наталія Шевченко", "Наталія Шевченко")
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(input_text, test_config, test_flags)
            
            # Basic E2E test
            assert result is not None, f"Result is None for '{input_text}'"
            assert result.success, f"Sanctions processing failed for '{input_text}': {result.errors}"
            
            # Should match expected output
            assert result.normalized == expected, \
                f"Sanctions accuracy failed for '{input_text}': got '{result.normalized}', expected '{expected}'"
    
    @pytest.mark.asyncio
    async def test_sanctions_performance(self, normalization_factory, test_config, test_flags, sanctions_cases):
        """Test sanctions processing performance."""
        import time
        
        total_time = 0.0
        successful = 0
        
        for case in sanctions_cases:
            start_time = time.perf_counter()
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            total_time += processing_time
            
            if result and result.success:
                successful += 1
            
            # Individual case should be fast
            assert processing_time < 1.0, f"Sanctions processing too slow for '{case}': {processing_time:.3f}s"
        
        # Overall performance should be good
        avg_time = total_time / len(sanctions_cases)
        assert avg_time < 0.5, f"Average sanctions processing time too slow: {avg_time:.3f}s"
        
        # Should have high success rate
        success_rate = successful / len(sanctions_cases)
        assert success_rate >= 0.95, f"Sanctions processing success rate too low: {success_rate:.1%} < 95%"
    
    @pytest.mark.asyncio
    async def test_sanctions_error_handling(self, normalization_factory, test_config, test_flags):
        """Test sanctions error handling."""
        error_cases = [
            "",  # Empty string
            None,  # None input
            "   ",  # Whitespace only
            "A" * 10000,  # Very long string
            "!@#$%^&*()",  # Special characters only
            "123456789",  # Numbers only
        ]
        
        for case in error_cases:
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Should handle gracefully
            assert result is not None, f"Result is None for error case: {case}"
            assert hasattr(result, 'success'), f"Result missing success attribute for error case: {case}"
            assert hasattr(result, 'errors'), f"Result missing errors attribute for error case: {case}"
            
            # Should not crash
            assert isinstance(result.success, bool), f"Success should be boolean for error case: {case}"
            assert isinstance(result.errors, list), f"Errors should be list for error case: {case}"
    
    @pytest.mark.asyncio
    async def test_sanctions_trace_completeness(self, normalization_factory, test_config, test_flags, sanctions_cases):
        """Test sanctions trace completeness."""
        for case in sanctions_cases[:5]:  # Test first 5 cases
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Basic E2E test
            assert result is not None, f"Result is None for '{case}'"
            assert result.success, f"Sanctions processing failed for '{case}': {result.errors}"
            
            # Should have trace
            assert hasattr(result, 'trace'), f"Result missing trace attribute for '{case}'"
            assert isinstance(result.trace, list), f"Trace should be list for '{case}'"
            
            # Should have comprehensive trace when debug_tracing is enabled
            if test_config.debug_tracing:
                assert len(result.trace) > 0, f"Trace should not be empty for '{case}'"
                
                # Should have various trace elements
                trace_text = str(result.trace)
                assert any(keyword in trace_text.lower() for keyword in [
                    'normalization', 'token', 'role', 'morphology', 'flag'
                ]), f"Trace should contain processing keywords for '{case}'"
    
    @pytest.mark.asyncio
    async def test_sanctions_feature_flags_integration(self, normalization_factory, test_config, test_flags, sanctions_cases):
        """Test sanctions feature flags integration."""
        for case in sanctions_cases[:5]:  # Test first 5 cases
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Basic E2E test
            assert result is not None, f"Result is None for '{case}'"
            assert result.success, f"Sanctions processing failed for '{case}': {result.errors}"
            
            # Should have trace with feature flag information
            if hasattr(result, 'trace') and result.trace:
                trace_text = str(result.trace)
                
                # Should contain feature flag traces
                assert any(keyword in trace_text.lower() for keyword in [
                    'spacy_ner', 'nameparser', 'strict_stopwords', 'fsm_tuned_roles',
                    'enhanced_diminutives', 'enhanced_gender_rules', 'ac_tier0',
                    'vector_fallback', 'ascii_fastpath'
                ]), f"Trace should contain feature flag information for '{case}'"
    
    @pytest.mark.asyncio
    async def test_sanctions_language_handling(self, normalization_factory, test_flags, sanctions_cases):
        """Test sanctions language handling."""
        language_configs = {
            "ru": NormalizationConfig(language="ru", debug_tracing=True),
            "uk": NormalizationConfig(language="uk", debug_tracing=True),
            "en": NormalizationConfig(language="en", debug_tracing=True)
        }
        
        for lang, config in language_configs.items():
            # Test a few cases for each language
            test_cases = sanctions_cases[:3]
            
            for case in test_cases:
                result = await normalization_factory.normalize_text(case, config, test_flags)
                
                # Basic E2E test
                assert result is not None, f"Result is None for '{case}' in {lang}"
                assert result.success, f"Sanctions processing failed for '{case}' in {lang}: {result.errors}"
                
                # Should have correct language
                assert hasattr(result, 'language'), f"Result missing language attribute for '{case}' in {lang}"
                assert result.language == lang, f"Language mismatch for '{case}': got '{result.language}', expected '{lang}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
