"""
Unit tests for defensive feature flags handling.

Tests that verify the system handles invalid, missing, or malformed
feature flags gracefully without crashing.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.config.feature_flags import FeatureFlags
from src.ai_service.contracts.base_contracts import (
    ValidationServiceInterface,
    LanguageDetectionInterface,
    UnicodeServiceInterface,
    NormalizationServiceInterface,
    SignalsServiceInterface
)


class TestDefensiveFlagsHandling:
    """Test defensive handling of feature flags."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator for testing."""
        # Create mock services
        validation_service = MagicMock(spec=ValidationServiceInterface)
        language_service = MagicMock(spec=LanguageDetectionInterface)
        unicode_service = MagicMock(spec=UnicodeServiceInterface)
        normalization_service = MagicMock(spec=NormalizationServiceInterface)
        signals_service = MagicMock(spec=SignalsServiceInterface)
        
        # Create orchestrator with mock services
        orchestrator = UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
            default_feature_flags=FeatureFlags()
        )
        
        return orchestrator

    def test_none_flags_uses_defaults(self, mock_orchestrator):
        """Test that None flags are handled by using defaults."""
        result = mock_orchestrator._validate_and_normalize_flags(None)
        
        assert result is not None
        assert isinstance(result, FeatureFlags)
        assert result == mock_orchestrator.default_feature_flags

    def test_invalid_type_flags_uses_defaults(self, mock_orchestrator):
        """Test that invalid type flags are handled by using defaults."""
        invalid_flags = {"use_factory_normalizer": True}  # Dict instead of FeatureFlags
        
        with patch('src.ai_service.core.unified_orchestrator.logger') as mock_logger:
            result = mock_orchestrator._validate_and_normalize_flags(invalid_flags)
            
            # Should log warning
            mock_logger.warning.assert_called_once()
            assert "Invalid feature_flags type" in str(mock_logger.warning.call_args)
            
            # Should return defaults
            assert result == mock_orchestrator.default_feature_flags

    def test_invalid_boolean_values_handled(self, mock_orchestrator):
        """Test that invalid boolean values are handled gracefully."""
        # Create flags with invalid boolean values
        invalid_flags = FeatureFlags()
        invalid_flags.use_factory_normalizer = "invalid_boolean"  # String instead of bool
        invalid_flags.fix_initials_double_dot = None  # None instead of bool
        invalid_flags.strict_stopwords = 123  # Int instead of bool
        
        with patch('src.ai_service.core.unified_orchestrator.logger') as mock_logger:
            result = mock_orchestrator._validate_and_normalize_flags(invalid_flags)
            
            # Should log warnings for invalid values
            assert mock_logger.warning.call_count >= 3
            
            # Should return the flags object (with corrected values)
            assert result is invalid_flags
            
            # Invalid values should be reset to defaults
            assert isinstance(result.use_factory_normalizer, bool)
            assert isinstance(result.fix_initials_double_dot, bool)
            assert isinstance(result.strict_stopwords, bool)

    def test_valid_flags_passed_through(self, mock_orchestrator):
        """Test that valid flags are passed through unchanged."""
        valid_flags = FeatureFlags(
            use_factory_normalizer=True,
            fix_initials_double_dot=True,
            preserve_hyphenated_case=False,
            strict_stopwords=True,
            enable_ac_tier0=False,
            enable_vector_fallback=False
        )
        
        result = mock_orchestrator._validate_and_normalize_flags(valid_flags)
        
        # Should return the same object
        assert result is valid_flags
        
        # Values should be unchanged
        assert result.use_factory_normalizer == True
        assert result.fix_initials_double_dot == True
        assert result.preserve_hyphenated_case == False
        assert result.strict_stopwords == True
        assert result.enable_ac_tier0 == False
        assert result.enable_vector_fallback == False

    def test_exception_during_validation_uses_defaults(self, mock_orchestrator):
        """Test that exceptions during validation are handled by using defaults."""
        # Create a flags object that will cause an exception in to_dict()
        class BrokenFlags:
            def to_dict(self):
                raise Exception("Simulated error")
        
        broken_flags = BrokenFlags()
        
        with patch('src.ai_service.core.unified_orchestrator.logger') as mock_logger:
            result = mock_orchestrator._validate_and_normalize_flags(broken_flags)
            
            # Should log warning about error
            mock_logger.warning.assert_called_once()
            assert "Error validating feature flags" in str(mock_logger.warning.call_args)
            
            # Should return defaults
            assert result == mock_orchestrator.default_feature_flags

    def test_mixed_valid_invalid_flags(self, mock_orchestrator):
        """Test handling of flags with some valid and some invalid values."""
        mixed_flags = FeatureFlags()
        mixed_flags.use_factory_normalizer = True  # Valid
        mixed_flags.fix_initials_double_dot = "invalid"  # Invalid
        mixed_flags.preserve_hyphenated_case = False  # Valid
        mixed_flags.strict_stopwords = None  # Invalid
        
        with patch('src.ai_service.core.unified_orchestrator.logger') as mock_logger:
            result = mock_orchestrator._validate_and_normalize_flags(mixed_flags)
            
            # Should log warnings for invalid values only
            assert mock_logger.warning.call_count == 2
            
            # Should return the flags object
            assert result is mixed_flags
            
            # Valid values should remain unchanged
            assert result.use_factory_normalizer == True
            assert result.preserve_hyphenated_case == False
            
            # Invalid values should be reset to defaults
            assert isinstance(result.fix_initials_double_dot, bool)
            assert isinstance(result.strict_stopwords, bool)

    def test_flags_with_unknown_attributes(self, mock_orchestrator):
        """Test handling of flags with unknown attributes."""
        # Create a flags object with extra attributes
        class ExtendedFlags(FeatureFlags):
            def __init__(self):
                super().__init__()
                self.unknown_flag = "some_value"
                self.another_unknown = 123
        
        extended_flags = ExtendedFlags()
        
        # Should not cause an error
        result = mock_orchestrator._validate_and_normalize_flags(extended_flags)
        
        # Should return the flags object
        assert result is extended_flags
        
        # Unknown attributes should be preserved
        assert hasattr(result, 'unknown_flag')
        assert hasattr(result, 'another_unknown')

    def test_empty_feature_flags_object(self, mock_orchestrator):
        """Test handling of empty feature flags object."""
        empty_flags = FeatureFlags()
        
        result = mock_orchestrator._validate_and_normalize_flags(empty_flags)
        
        # Should return the same object
        assert result is empty_flags
        
        # Should have all default values
        assert result.use_factory_normalizer == False
        assert result.fix_initials_double_dot == False
        assert result.preserve_hyphenated_case == False
        assert result.strict_stopwords == False
        assert result.enable_ac_tier0 == False
        assert result.enable_vector_fallback == False

    def test_flags_validation_in_process_method(self, mock_orchestrator):
        """Test that flags validation is called in the process method."""
        # Mock the normalization service
        mock_result = MagicMock()
        mock_result.normalized_text = "test"
        mock_result.tokens = ["test"]
        mock_result.trace = []
        mock_result.language = "en"
        mock_result.success = True
        mock_result.errors = []
        mock_result.processing_time = 0.1
        mock_result.signals = None
        mock_result.decision = None
        mock_result.embeddings = None
        
        mock_orchestrator.normalization_service.normalize_async.return_value = mock_result
        
        # Create invalid flags
        invalid_flags = {"invalid": "flags"}
        
        with patch.object(mock_orchestrator, '_validate_and_normalize_flags') as mock_validate:
            mock_validate.return_value = FeatureFlags()
            
            # This should not raise an exception
            result = mock_orchestrator.process(
                text="test",
                feature_flags=invalid_flags
            )
            
            # Should have called validation
            mock_validate.assert_called_once_with(invalid_flags)
            
            # Should return a result
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
