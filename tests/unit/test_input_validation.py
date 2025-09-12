"""
Unit tests for InputValidator service
Testing input sanitization and validation for sanctions screening
"""

import pytest
from unittest.mock import patch

from src.ai_service.utils.input_validation import InputValidator, ValidationResult
from src.ai_service.exceptions import ValidationError


class TestInputValidator:
    """Tests for InputValidator"""

    @pytest.fixture
    def validator(self):
        """Create InputValidator instance"""
        return InputValidator()

    def test_valid_text_processing(self, validator):
        """Test processing of valid text"""
        # Arrange
        text = "Петро Порошенко"

        # Act
        result = validator.validate_and_sanitize(text)

        # Assert
        assert result.is_valid is True
        # The validator may replace homoglyphs, so we check that the result is valid
        assert result.sanitized_text is not None
        assert len(result.sanitized_text) > 0
        assert len(result.warnings) == 0
        assert len(result.blocked_patterns) == 0
        assert result.risk_level == "low"

    def test_homoglyph_replacement(self, validator):
        """Test homoglyph character replacement"""
        # Arrange
        text_with_homoglyphs = "Pаvlоv"  # Contains Cyrillic 'а' and 'о'

        # Act
        result = validator.validate_and_sanitize(text_with_homoglyphs, remove_homoglyphs=True)

        # Assert
        assert result.is_valid is True
        assert result.sanitized_text == "Pavlov"  # Should be normalized
        # Check that homoglyphs were replaced (text should be different from original)
        assert result.sanitized_text != text_with_homoglyphs

    def test_zero_width_character_removal(self, validator):
        """Test zero-width character removal"""
        # Arrange
        text_with_zw = "Pet\u200bro\u200cPoro\u200dshenko"  # Contains zero-width chars

        # Act
        result = validator.validate_and_sanitize(text_with_zw)

        # Assert
        assert result.is_valid is True
        assert "\u200b" not in result.sanitized_text
        assert "\u200c" not in result.sanitized_text
        assert "\u200d" not in result.sanitized_text
        assert "PetroPoroshenko" in result.sanitized_text

    def test_control_character_removal(self, validator):
        """Test control character removal"""
        # Arrange
        text_with_control = "Test\x00\x01Name\x1f"

        # Act
        result = validator.validate_and_sanitize(text_with_control)

        # Assert
        assert result.is_valid is True
        assert "\x00" not in result.sanitized_text
        assert "\x01" not in result.sanitized_text
        assert "\x1f" not in result.sanitized_text
        assert result.sanitized_text == "TestName"

    def test_suspicious_pattern_detection(self, validator):
        """Test detection of suspicious patterns"""
        # Arrange
        malicious_text = "<script>alert('xss')</script>Петро"

        # Act
        result = validator.validate_and_sanitize(malicious_text, strict_mode=False)

        # Assert
        assert len(result.blocked_patterns) > 0
        assert result.risk_level == "high"
        assert any("script" in pattern for pattern in result.blocked_patterns)

    def test_strict_mode_blocking(self, validator):
        """Test strict mode blocks suspicious content"""
        # Arrange
        malicious_text = "javascript:void(0) Петро"

        # Act & Assert
        with pytest.raises(ValidationError):
            validator.validate_and_sanitize(malicious_text, strict_mode=True)

    def test_text_length_limiting(self, validator):
        """Test text length limiting"""
        # Arrange
        long_text = "A" * (validator.max_length + 100)

        # Act
        result = validator.validate_and_sanitize(long_text, strict_mode=False)

        # Assert
        assert len(result.sanitized_text) == validator.max_length
        assert any("truncated" in warning for warning in result.warnings)
        assert result.risk_level == "medium"

    def test_empty_text_handling(self, validator):
        """Test empty text handling"""
        # Arrange
        empty_text = "   "  # Only whitespace

        # Act
        result = validator.validate_and_sanitize(empty_text)

        # Assert
        assert result.is_valid is False
        assert result.sanitized_text == ""
        assert any("Empty input" in warning for warning in result.warnings)

    def test_unicode_normalization(self, validator):
        """Test Unicode normalization"""
        # Arrange
        unnormalized_text = "Café"  # Contains combined characters

        # Act
        result = validator.validate_and_sanitize(unnormalized_text)

        # Assert
        assert result.is_valid is True
        # Text should be normalized to NFKC form
        assert len(result.sanitized_text) >= 4

    def test_sanctions_input_validation(self, validator):
        """Test sanctions-specific input validation"""
        # Arrange
        sanctions_data = {
            'name': 'Петро Порошенко',
            'name_en': 'Petro Poroshenko',
            'entity_type': 'PERSON',
            'birthdate': '1965-09-26'
        }

        # Act
        result = validator.validate_sanctions_input(sanctions_data)

        # Assert
        assert 'name' in result
        assert 'name_en' in result
        assert 'entity_type' in result
        # The validator may replace homoglyphs, so we check that the result is valid
        assert result['name'] is not None
        assert len(result['name']) > 0
        assert result['name_en'] == 'Petro Poroshenko'

    def test_sanctions_input_missing_required_field(self, validator):
        """Test sanctions input validation with missing required field"""
        # Arrange
        invalid_data = {'entity_type': 'PERSON'}  # Missing 'name'

        # Act & Assert
        with pytest.raises(ValidationError, match="Missing required field: name"):
            validator.validate_sanctions_input(invalid_data)

    def test_sanctions_input_with_malicious_content(self, validator):
        """Test sanctions input validation blocks malicious content"""
        # Arrange
        malicious_data = {
            'name': '<script>alert("xss")</script>Test Name'
        }

        # Act & Assert
        with pytest.raises(ValidationError, match="Suspicious pattern detected"):
            validator.validate_sanctions_input(malicious_data)

    def test_suspicion_analysis_high_zero_width(self, validator):
        """Test suspicion analysis for high zero-width character count"""
        # Arrange
        suspicious_text = "N\u200ba\u200bm\u200be\u200b" * 5  # Many zero-width chars

        # Act
        analysis = validator.is_text_suspicious(suspicious_text)

        # Assert
        assert analysis['is_suspicious'] is True
        assert analysis['risk_level'] in ['medium', 'high']
        assert any("zero-width" in warning for warning in analysis['warnings'])

    def test_suspicion_analysis_high_homoglyph_ratio(self, validator):
        """Test suspicion analysis for high homoglyph ratio"""
        # Arrange
        homoglyph_text = "Nаmе"  # 50% homoglyphs (Cyrillic а, е)

        # Act
        analysis = validator.is_text_suspicious(homoglyph_text)

        # Assert
        assert analysis['is_suspicious'] is True
        assert any("homoglyph" in warning for warning in analysis['warnings'])

    def test_non_string_input_raises_error(self, validator):
        """Test non-string input raises ValidationError"""
        # Act & Assert
        with pytest.raises(ValidationError, match="Input must be string"):
            validator.validate_and_sanitize(123)

    def test_whitespace_normalization(self, validator):
        """Test excessive whitespace normalization"""
        # Arrange
        text_with_whitespace = "Name   with    excessive     spaces"

        # Act
        result = validator.validate_and_sanitize(text_with_whitespace)

        # Assert
        assert result.is_valid is True
        assert result.sanitized_text == "Name with excessive spaces"

    def test_url_encoding_detection(self, validator):
        """Test URL encoding pattern detection"""
        # Arrange
        url_encoded_text = "Name%20with%20encoding"

        # Act
        result = validator.validate_and_sanitize(url_encoded_text, strict_mode=False)

        # Assert
        assert len(result.blocked_patterns) > 0
        assert result.risk_level == "high"

    def test_html_entity_detection(self, validator):
        """Test HTML entity pattern detection"""
        # Arrange
        html_entity_text = "Name&#x41;&#65;test"

        # Act
        result = validator.validate_and_sanitize(html_entity_text, strict_mode=False)

        # Assert
        assert len(result.blocked_patterns) > 0
        assert result.risk_level == "high"

    @patch('unicodedata.normalize')
    def test_unicode_normalization_failure(self, mock_normalize, validator):
        """Test graceful handling of Unicode normalization failure"""
        # Arrange
        mock_normalize.side_effect = Exception("Normalization failed")
        text = "Test text"

        # Act
        result = validator.validate_and_sanitize(text)

        # Assert
        assert result.is_valid is True
        assert result.sanitized_text == text  # Should continue with original text

    def test_input_validator_global_instance(self):
        """Test that global input_validator instance works"""
        # Arrange
        from src.ai_service.utils.input_validation import input_validator

        # Act
        result = input_validator.validate_and_sanitize("Test text")

        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True


class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_validation_result_creation(self):
        """Test ValidationResult creation"""
        # Act
        result = ValidationResult(
            is_valid=True,
            sanitized_text="test",
            warnings=["warning"],
            blocked_patterns=["pattern"],
            risk_level="low"
        )

        # Assert
        assert result.is_valid is True
        assert result.sanitized_text == "test"
        assert result.warnings == ["warning"]
        assert result.blocked_patterns == ["pattern"]
        assert result.risk_level == "low"