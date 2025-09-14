"""
Test suite for ValidationService.

Tests the validation and sanitization service that forms Layer 1 of the
unified architecture.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_service.layers.validation.validation_service import ValidationService
from ai_service.utils.input_validation import ValidationResult


class TestValidationService:
    """Test ValidationService functionality"""

    def test_initialization(self):
        """Test ValidationService can be instantiated"""
        service = ValidationService()
        assert service is not None
        assert service._validator is None

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization of ValidationService"""
        service = ValidationService()

        with patch('ai_service.layers.validation.validation_service.InputValidator') as mock_validator:
            await service.initialize()

            assert service._validator is not None
            mock_validator.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test initialization failure handling"""
        service = ValidationService()

        with patch('ai_service.layers.validation.validation_service.InputValidator',
                   side_effect=Exception("Init failed")):
            with pytest.raises(Exception) as exc_info:
                await service.initialize()

            assert "Init failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_not_initialized(self):
        """Test validation when service not initialized"""
        service = ValidationService()

        with pytest.raises(RuntimeError) as exc_info:
            await service.validate_and_sanitize("test text")

        assert "ValidationService not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_success(self):
        """Test successful validation and sanitization"""
        service = ValidationService()

        # Mock validation result
        mock_result = ValidationResult(
            sanitized_text="cleaned text",
            is_valid=True,
            warnings=["minor warning"],
            blocked_patterns=[],
            risk_level="low"
        )

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.return_value = mock_result
        service._validator = mock_validator

        result = await service.validate_and_sanitize("  test text  ")

        assert result["sanitized_text"] == "cleaned text"
        assert result["should_process"] is True
        assert result["is_valid"] is True
        assert result["warnings"] == ["minor warning"]
        assert result["blocked_patterns"] == []
        assert result["risk_level"] == "low"

        mock_validator.validate_and_sanitize.assert_called_once_with("  test text  ")

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_invalid_input(self):
        """Test validation with invalid input"""
        service = ValidationService()

        mock_result = ValidationResult(
            sanitized_text="",
            is_valid=False,
            warnings=["Input contains malicious content"],
            blocked_patterns=["<script>"],
            risk_level="high"
        )

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.return_value = mock_result
        service._validator = mock_validator

        result = await service.validate_and_sanitize("<script>alert('xss')</script>")

        assert result["sanitized_text"] == ""
        assert result["should_process"] is False
        assert result["is_valid"] is False
        assert result["warnings"] == ["Input contains malicious content"]
        assert result["blocked_patterns"] == ["<script>"]
        assert result["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_exception_handling(self):
        """Test exception handling during validation"""
        service = ValidationService()

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.side_effect = Exception("Validation error")
        service._validator = mock_validator

        result = await service.validate_and_sanitize("test text")

        # Should provide safe fallback
        assert result["sanitized_text"] == "test text"
        assert result["should_process"] is True
        assert result["is_valid"] is True
        assert "Validation error" in result["warnings"][0]
        assert result["blocked_patterns"] == []
        assert result["risk_level"] == "unknown"

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_empty_text(self):
        """Test validation with empty text"""
        service = ValidationService()

        mock_result = ValidationResult(
            sanitized_text="",
            is_valid=False,
            warnings=["Empty input"],
            blocked_patterns=[],
            risk_level="low"
        )

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.return_value = mock_result
        service._validator = mock_validator

        result = await service.validate_and_sanitize("")

        assert result["sanitized_text"] == ""
        assert result["should_process"] is False
        assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_long_text(self):
        """Test validation with very long text"""
        service = ValidationService()

        long_text = "a" * 2000
        expected_truncated = "a" * 1000

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.side_effect = Exception("Text too long")
        service._validator = mock_validator

        result = await service.validate_and_sanitize(long_text)

        # Should truncate in fallback
        assert result["sanitized_text"] == expected_truncated
        assert result["should_process"] is True
        assert len(result["warnings"]) == 1

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_none_input(self):
        """Test validation with None input"""
        service = ValidationService()

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.side_effect = Exception("None input")
        service._validator = mock_validator

        result = await service.validate_and_sanitize(None)

        # Should handle None gracefully in fallback
        assert result["sanitized_text"] == ""
        assert result["should_process"] is False
        assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_with_risk_levels(self):
        """Test validation with different risk levels"""
        service = ValidationService()

        risk_cases = [
            ("low", "normal text"),
            ("medium", "suspicious text"),
            ("high", "dangerous text")
        ]

        for risk_level, text in risk_cases:
            mock_result = ValidationResult(
                sanitized_text=text,
                is_valid=risk_level != "high",
                warnings=[f"Risk level: {risk_level}"],
                blocked_patterns=[],
                risk_level=risk_level
            )

            mock_validator = Mock()
            mock_validator.validate_and_sanitize.return_value = mock_result
            service._validator = mock_validator

            result = await service.validate_and_sanitize(text)

            assert result["risk_level"] == risk_level
            assert result["should_process"] == (risk_level != "high")

    @pytest.mark.asyncio
    async def test_validate_with_blocked_patterns(self):
        """Test validation with blocked content patterns"""
        service = ValidationService()

        blocked_patterns = ["<script>", "javascript:", "data:"]
        mock_result = ValidationResult(
            sanitized_text="cleaned content",
            is_valid=False,
            warnings=["Blocked patterns detected"],
            blocked_patterns=blocked_patterns,
            risk_level="high"
        )

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.return_value = mock_result
        service._validator = mock_validator

        result = await service.validate_and_sanitize("<script>malicious</script>")

        assert result["blocked_patterns"] == blocked_patterns
        assert result["should_process"] is False
        assert result["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_validate_with_warnings(self):
        """Test validation with multiple warnings"""
        service = ValidationService()

        warnings = [
            "Text contains special characters",
            "Text is longer than recommended",
            "Text contains mixed scripts"
        ]

        mock_result = ValidationResult(
            sanitized_text="sanitized text",
            is_valid=True,
            warnings=warnings,
            blocked_patterns=[],
            risk_level="medium"
        )

        mock_validator = Mock()
        mock_validator.validate_and_sanitize.return_value = mock_result
        service._validator = mock_validator

        result = await service.validate_and_sanitize("complex mixed text")

        assert result["warnings"] == warnings
        assert len(result["warnings"]) == 3
        assert result["should_process"] is True

    @pytest.mark.asyncio
    async def test_interface_compliance(self):
        """Test that ValidationService properly implements the interface"""
        service = ValidationService()

        # Test that it has the required interface methods
        assert hasattr(service, 'validate_and_sanitize')
        assert callable(getattr(service, 'validate_and_sanitize'))

        # Test that validate_and_sanitize is async
        await service.initialize()
        mock_result = ValidationResult("clean", True, [], [], "low")
        service._validator = Mock()
        service._validator.validate_and_sanitize.return_value = mock_result

        result = await service.validate_and_sanitize("test")
        assert isinstance(result, dict)

        # Required fields should be present
        required_fields = [
            "sanitized_text", "should_process", "warnings",
            "blocked_patterns", "risk_level", "is_valid"
        ]
        for field in required_fields:
            assert field in result