"""
Integration tests for shadow mode validation.

This module tests the shadow mode validation system for feature-gated
functional improvements.
"""

import pytest
import asyncio
from typing import Dict, List

from src.ai_service.validation.shadow_mode_validator import (
    ShadowModeValidator,
    ValidationResult,
    validate_feature_improvements,
    validate_all_test_cases
)


class TestShadowModeValidation:
    """Test shadow mode validation system."""
    
    @pytest.fixture(scope="class")
    def validator(self):
        """Create shadow mode validator for testing."""
        return ShadowModeValidator()
    
    @pytest.mark.asyncio
    async def test_ner_improvements_validation(self, validator: ShadowModeValidator):
        """Test NER improvements validation."""
        text = "John Smith"
        result = await validator.validate_ner_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "enable_spacy_ner"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_nameparser_improvements_validation(self, validator: ShadowModeValidator):
        """Test nameparser improvements validation."""
        text = "Dr. Jane Doe"
        result = await validator.validate_nameparser_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "enable_nameparser_en"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_strict_stopwords_improvements_validation(self, validator: ShadowModeValidator):
        """Test strict stopwords improvements validation."""
        text = "Mary O'Connor"
        result = await validator.validate_strict_stopwords_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "strict_stopwords"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_fsm_tuned_roles_improvements_validation(self, validator: ShadowModeValidator):
        """Test FSM tuned roles improvements validation."""
        text = "Robert Johnson Jr."
        result = await validator.validate_fsm_tuned_roles_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "fsm_tuned_roles"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_enhanced_diminutives_improvements_validation(self, validator: ShadowModeValidator):
        """Test enhanced diminutives improvements validation."""
        text = "Иван Петров"
        result = await validator.validate_enhanced_diminutives_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "enhanced_diminutives"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_enhanced_gender_rules_improvements_validation(self, validator: ShadowModeValidator):
        """Test enhanced gender rules improvements validation."""
        text = "Анна Сидорова"
        result = await validator.validate_enhanced_gender_rules_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "enhanced_gender_rules"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_ac_tier0_improvements_validation(self, validator: ShadowModeValidator):
        """Test AC tier 0 improvements validation."""
        text = "Elizabeth Williams"
        result = await validator.validate_ac_tier0_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "enable_ac_tier0"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_vector_fallback_improvements_validation(self, validator: ShadowModeValidator):
        """Test vector fallback improvements validation."""
        text = "Jean-Pierre Dubois"
        result = await validator.validate_vector_fallback_improvements(text)
        
        assert isinstance(result, ValidationResult)
        assert result.flag_name == "enable_vector_fallback"
        assert isinstance(result.accuracy_improvement, float)
        assert isinstance(result.confidence_improvement, float)
        assert isinstance(result.performance_impact_ms, float)
        assert isinstance(result.error_rate_reduction, float)
        assert isinstance(result.coverage_improvement, float)
        assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_all_improvements_validation(self, validator: ShadowModeValidator):
        """Test validation of all improvements."""
        text = "John Smith"
        results = await validator.validate_all_improvements(text)
        
        assert isinstance(results, list)
        assert len(results) == 8  # 8 different improvements
        
        # Check that all results are ValidationResult objects
        for result in results:
            assert isinstance(result, ValidationResult)
            assert isinstance(result.flag_name, str)
            assert isinstance(result.accuracy_improvement, float)
            assert isinstance(result.confidence_improvement, float)
            assert isinstance(result.performance_impact_ms, float)
            assert isinstance(result.error_rate_reduction, float)
            assert isinstance(result.coverage_improvement, float)
            assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_test_cases_validation(self, validator: ShadowModeValidator):
        """Test validation of all test cases."""
        results = await validator.validate_test_cases()
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Check that all test cases have results
        for test_case, case_results in results.items():
            assert isinstance(test_case, str)
            assert isinstance(case_results, list)
            assert len(case_results) == 8  # 8 different improvements
            
            # Check that all results are ValidationResult objects
            for result in case_results:
                assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_validation_with_empty_text(self, validator: ShadowModeValidator):
        """Test validation with empty text."""
        text = ""
        results = await validator.validate_all_improvements(text)
        
        assert isinstance(results, list)
        assert len(results) == 8
        
        # All results should be ValidationResult objects
        for result in results:
            assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_validation_with_complex_text(self, validator: ShadowModeValidator):
        """Test validation with complex text."""
        text = "Dr. Prof. Mary-Jane O'Connor-Smith Jr."
        results = await validator.validate_all_improvements(text)
        
        assert isinstance(results, list)
        assert len(results) == 8
        
        # All results should be ValidationResult objects
        for result in results:
            assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_validation_with_cyrillic_text(self, validator: ShadowModeValidator):
        """Test validation with Cyrillic text."""
        text = "Анна-Мария Петрова"
        results = await validator.validate_all_improvements(text)
        
        assert isinstance(results, list)
        assert len(results) == 8
        
        # All results should be ValidationResult objects
        for result in results:
            assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_validation_with_ukrainian_text(self, validator: ShadowModeValidator):
        """Test validation with Ukrainian text."""
        text = "Олександр Коваленко"
        results = await validator.validate_all_improvements(text)
        
        assert isinstance(results, list)
        assert len(results) == 8
        
        # All results should be ValidationResult objects
        for result in results:
            assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_validation_with_edge_cases(self, validator: ShadowModeValidator):
        """Test validation with edge cases."""
        edge_cases = [
            "A. B. C.",
            "Dr. Prof. Smith",
            "Mary-Jane O'Connor-Smith",
            "Іван Петрович Сидоренко"
        ]
        
        for text in edge_cases:
            results = await validator.validate_all_improvements(text)
            
            assert isinstance(results, list)
            assert len(results) == 8
            
            # All results should be ValidationResult objects
            for result in results:
                assert isinstance(result, ValidationResult)
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            flag_name="test_flag",
            accuracy_improvement=15.3,
            confidence_improvement=12.7,
            performance_impact_ms=8.2,
            error_rate_reduction=23.1,
            coverage_improvement=18.4,
            success=True
        )
        
        assert result.flag_name == "test_flag"
        assert result.accuracy_improvement == 15.3
        assert result.confidence_improvement == 12.7
        assert result.performance_impact_ms == 8.2
        assert result.error_rate_reduction == 23.1
        assert result.coverage_improvement == 18.4
        assert result.success is True
        assert result.errors == []
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult creation with errors."""
        result = ValidationResult(
            flag_name="test_flag",
            accuracy_improvement=0.0,
            confidence_improvement=0.0,
            performance_impact_ms=0.0,
            error_rate_reduction=0.0,
            coverage_improvement=0.0,
            success=False,
            errors=["Test error 1", "Test error 2"]
        )
        
        assert result.flag_name == "test_flag"
        assert result.accuracy_improvement == 0.0
        assert result.confidence_improvement == 0.0
        assert result.performance_impact_ms == 0.0
        assert result.error_rate_reduction == 0.0
        assert result.coverage_improvement == 0.0
        assert result.success is False
        assert result.errors == ["Test error 1", "Test error 2"]
    
    @pytest.mark.asyncio
    async def test_global_validation_functions(self):
        """Test global validation functions."""
        text = "John Smith"
        
        # Test validate_feature_improvements
        results = await validate_feature_improvements(text)
        assert isinstance(results, list)
        assert len(results) == 8
        
        # Test validate_all_test_cases
        all_results = await validate_all_test_cases()
        assert isinstance(all_results, dict)
        assert len(all_results) > 0
    
    @pytest.mark.asyncio
    async def test_validation_performance(self, validator: ShadowModeValidator):
        """Test validation performance."""
        import time
        
        text = "John Smith"
        start_time = time.time()
        
        results = await validator.validate_all_improvements(text)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert isinstance(results, list)
        assert len(results) == 8
        assert processing_time < 10.0  # Should complete within 10 seconds
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, validator: ShadowModeValidator):
        """Test validation error handling."""
        # Test with None text (should handle gracefully)
        results = await validator.validate_all_improvements(None)
        
        assert isinstance(results, list)
        assert len(results) == 8
        
        # All results should be ValidationResult objects
        for result in results:
            assert isinstance(result, ValidationResult)
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = ShadowModeValidator()
        
        assert validator is not None
        assert hasattr(validator, 'test_cases')
        assert isinstance(validator.test_cases, list)
        assert len(validator.test_cases) > 0
        
        # Check that test cases are strings
        for test_case in validator.test_cases:
            assert isinstance(test_case, str)
    
    def test_validator_test_cases(self, validator: ShadowModeValidator):
        """Test validator test cases."""
        test_cases = validator.test_cases
        
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # Check that test cases include various types of names
        has_english = any("John" in case or "Mary" in case for case in test_cases)
        has_russian = any("Иван" in case or "Анна" in case for case in test_cases)
        has_ukrainian = any("Олександр" in case or "Наталія" in case for case in test_cases)
        has_complex = any("-" in case or "Dr." in case for case in test_cases)
        
        assert has_english, "Should include English names"
        assert has_russian, "Should include Russian names"
        assert has_ukrainian, "Should include Ukrainian names"
        assert has_complex, "Should include complex names"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
