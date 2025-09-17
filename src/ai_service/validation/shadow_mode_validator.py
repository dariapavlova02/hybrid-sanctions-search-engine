"""
Shadow mode validator for feature-gated functional improvements.

This module provides validation capabilities for testing feature improvements
in shadow mode without affecting production behavior.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..config.feature_flags import FeatureFlags
from ..layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of shadow mode validation."""
    flag_name: str
    accuracy_improvement: float
    confidence_improvement: float
    performance_impact_ms: float
    error_rate_reduction: float
    coverage_improvement: float
    success: bool
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class ShadowModeResult:
    """Result of shadow mode processing."""
    text: str
    result_with_flags: Any
    result_without_flags: Any
    processing_time_with: float
    processing_time_without: float
    success: bool
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ShadowModeValidator:
    """Validates feature improvements in shadow mode."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.normalization_factory = NormalizationFactory()
        
        # Test cases for validation
        self.test_cases = [
            # English names
            "John Smith",
            "Dr. Jane Doe",
            "Mary O'Connor",
            "Robert Johnson Jr.",
            "Elizabeth Williams",
            
            # Russian names
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна",
            
            # Ukrainian names
            "Олександр Коваленко",
            "Наталія Шевченко",
            "Михайло Іванович",
            "Оксана Петрівна",
            
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
    
    async def validate_ner_improvements(self, text: str) -> ValidationResult:
        """Validate NER improvements."""
        try:
            # Process with NER flag enabled
            flags_with = FeatureFlags(enable_spacy_ner=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without NER flag
            flags_without = FeatureFlags(enable_spacy_ner=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="enable_spacy_ner",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"NER validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="enable_spacy_ner",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_nameparser_improvements(self, text: str) -> ValidationResult:
        """Validate nameparser improvements."""
        try:
            # Process with nameparser flag enabled
            flags_with = FeatureFlags(enable_nameparser_en=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without nameparser flag
            flags_without = FeatureFlags(enable_nameparser_en=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="enable_nameparser_en",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Nameparser validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="enable_nameparser_en",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_strict_stopwords_improvements(self, text: str) -> ValidationResult:
        """Validate strict stopwords improvements."""
        try:
            # Process with strict stopwords flag enabled
            flags_with = FeatureFlags(strict_stopwords=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without strict stopwords flag
            flags_without = FeatureFlags(strict_stopwords=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="strict_stopwords",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Strict stopwords validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="strict_stopwords",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_fsm_tuned_roles_improvements(self, text: str) -> ValidationResult:
        """Validate FSM tuned roles improvements."""
        try:
            # Process with FSM tuned roles flag enabled
            flags_with = FeatureFlags(fsm_tuned_roles=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without FSM tuned roles flag
            flags_without = FeatureFlags(fsm_tuned_roles=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="fsm_tuned_roles",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"FSM tuned roles validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="fsm_tuned_roles",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_enhanced_diminutives_improvements(self, text: str) -> ValidationResult:
        """Validate enhanced diminutives improvements."""
        try:
            # Process with enhanced diminutives flag enabled
            flags_with = FeatureFlags(enhanced_diminutives=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without enhanced diminutives flag
            flags_without = FeatureFlags(enhanced_diminutives=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="enhanced_diminutives",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Enhanced diminutives validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="enhanced_diminutives",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_enhanced_gender_rules_improvements(self, text: str) -> ValidationResult:
        """Validate enhanced gender rules improvements."""
        try:
            # Process with enhanced gender rules flag enabled
            flags_with = FeatureFlags(enhanced_gender_rules=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without enhanced gender rules flag
            flags_without = FeatureFlags(enhanced_gender_rules=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="enhanced_gender_rules",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Enhanced gender rules validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="enhanced_gender_rules",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_ac_tier0_improvements(self, text: str) -> ValidationResult:
        """Validate AC tier 0 improvements."""
        try:
            # Process with AC tier 0 flag enabled
            flags_with = FeatureFlags(enable_ac_tier0=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without AC tier 0 flag
            flags_without = FeatureFlags(enable_ac_tier0=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="enable_ac_tier0",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"AC tier 0 validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="enable_ac_tier0",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_vector_fallback_improvements(self, text: str) -> ValidationResult:
        """Validate vector fallback improvements."""
        try:
            # Process with vector fallback flag enabled
            flags_with = FeatureFlags(enable_vector_fallback=True)
            config_with = NormalizationConfig(debug_tracing=True)
            result_with = await self.normalization_factory.normalize_text(
                text, config_with, flags_with
            )
            
            # Process without vector fallback flag
            flags_without = FeatureFlags(enable_vector_fallback=False)
            config_without = NormalizationConfig(debug_tracing=True)
            result_without = await self.normalization_factory.normalize_text(
                text, config_without, flags_without
            )
            
            # Calculate improvements
            accuracy_improvement = self._calculate_accuracy_improvement(
                result_with, result_without
            )
            confidence_improvement = self._calculate_confidence_improvement(
                result_with, result_without
            )
            performance_impact = result_with.processing_time - result_without.processing_time
            error_rate_reduction = self._calculate_error_rate_reduction(
                result_with, result_without
            )
            coverage_improvement = self._calculate_coverage_improvement(
                result_with, result_without
            )
            
            return ValidationResult(
                flag_name="enable_vector_fallback",
                accuracy_improvement=accuracy_improvement,
                confidence_improvement=confidence_improvement,
                performance_impact_ms=performance_impact * 1000,
                error_rate_reduction=error_rate_reduction,
                coverage_improvement=coverage_improvement,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Vector fallback validation failed for '{text}': {e}")
            return ValidationResult(
                flag_name="enable_vector_fallback",
                accuracy_improvement=0.0,
                confidence_improvement=0.0,
                performance_impact_ms=0.0,
                error_rate_reduction=0.0,
                coverage_improvement=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def validate_all_improvements(self, text: str) -> List[ValidationResult]:
        """Validate all improvements for a given text."""
        results = []
        
        # Validate each improvement
        validators = [
            self.validate_ner_improvements,
            self.validate_nameparser_improvements,
            self.validate_strict_stopwords_improvements,
            self.validate_fsm_tuned_roles_improvements,
            self.validate_enhanced_diminutives_improvements,
            self.validate_enhanced_gender_rules_improvements,
            self.validate_ac_tier0_improvements,
            self.validate_vector_fallback_improvements
        ]
        
        for validator in validators:
            try:
                result = await validator(text)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Validation failed: {e}")
                results.append(ValidationResult(
                    flag_name="unknown",
                    accuracy_improvement=0.0,
                    confidence_improvement=0.0,
                    performance_impact_ms=0.0,
                    error_rate_reduction=0.0,
                    coverage_improvement=0.0,
                    success=False,
                    errors=[str(e)]
                ))
        
        return results
    
    async def validate_test_cases(self) -> Dict[str, List[ValidationResult]]:
        """Validate all test cases."""
        results = {}
        
        for test_case in self.test_cases:
            self.logger.info(f"Validating test case: '{test_case}'")
            case_results = await self.validate_all_improvements(test_case)
            results[test_case] = case_results
        
        return results
    
    def _calculate_accuracy_improvement(self, result_with: Any, result_without: Any) -> float:
        """Calculate accuracy improvement percentage."""
        # Simple heuristic: compare normalized text quality
        if not hasattr(result_with, 'normalized') or not hasattr(result_without, 'normalized'):
            return 0.0
        
        # Compare normalized text length (longer might be better for names)
        len_with = len(result_with.normalized)
        len_without = len(result_without.normalized)
        
        if len_without == 0:
            return 100.0 if len_with > 0 else 0.0
        
        improvement = ((len_with - len_without) / len_without) * 100
        return max(0.0, improvement)
    
    def _calculate_confidence_improvement(self, result_with: Any, result_without: Any) -> float:
        """Calculate confidence improvement percentage."""
        if not hasattr(result_with, 'confidence') or not hasattr(result_without, 'confidence'):
            return 0.0
        
        conf_with = result_with.confidence or 0.0
        conf_without = result_without.confidence or 0.0
        
        if conf_without == 0.0:
            return 100.0 if conf_with > 0.0 else 0.0
        
        improvement = ((conf_with - conf_without) / conf_without) * 100
        return max(0.0, improvement)
    
    def _calculate_error_rate_reduction(self, result_with: Any, result_without: Any) -> float:
        """Calculate error rate reduction percentage."""
        errors_with = len(result_with.errors) if hasattr(result_with, 'errors') and result_with.errors else 0
        errors_without = len(result_without.errors) if hasattr(result_without, 'errors') and result_without.errors else 0
        
        if errors_without == 0:
            return 100.0 if errors_with == 0 else 0.0
        
        reduction = ((errors_without - errors_with) / errors_without) * 100
        return max(0.0, reduction)
    
    def _calculate_coverage_improvement(self, result_with: Any, result_without: Any) -> float:
        """Calculate coverage improvement percentage."""
        # Compare token count (more tokens might indicate better coverage)
        tokens_with = len(result_with.tokens) if hasattr(result_with, 'tokens') and result_with.tokens else 0
        tokens_without = len(result_without.tokens) if hasattr(result_without, 'tokens') and result_without.tokens else 0
        
        if tokens_without == 0:
            return 100.0 if tokens_with > 0 else 0.0
        
        improvement = ((tokens_with - tokens_without) / tokens_without) * 100
        return max(0.0, improvement)


# Global validator instance
shadow_mode_validator = ShadowModeValidator()


async def validate_feature_improvements(text: str) -> List[ValidationResult]:
    """Validate all feature improvements for given text."""
    return await shadow_mode_validator.validate_all_improvements(text)


async def validate_all_test_cases() -> Dict[str, List[ValidationResult]]:
    """Validate all test cases."""
    return await shadow_mode_validator.validate_test_cases()
