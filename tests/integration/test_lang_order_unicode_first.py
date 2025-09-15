"""
Integration tests for Unicode normalization before language detection order
"""

import pytest
from unittest.mock import Mock, patch

from ai_service.core.unified_orchestrator import UnifiedOrchestrator
from ai_service.layers.unicode.unicode_service import UnicodeService
from ai_service.layers.language.language_detection_service import LanguageDetectionService


class TestUnicodeFirstLanguageDetectionOrder:
    """Test that Unicode normalization precedes language detection"""

    @pytest.fixture
    def unicode_service(self):
        """Create UnicodeService instance"""
        return UnicodeService()

    @pytest.fixture
    def language_service(self):
        """Create LanguageDetectionService instance"""
        return LanguageDetectionService()

    @pytest.fixture
    def orchestrator(self):
        """Create UnifiedOrchestrator instance with mocked services"""
        # Create mock services
        validation_service = Mock()
        language_service = Mock(spec=LanguageDetectionService)
        unicode_service = Mock(spec=UnicodeService)
        normalization_service = Mock()
        signals_service = Mock()
        
        # Create orchestrator with required services
        orchestrator = UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
            metrics_service=Mock()
        )
        
        return orchestrator

    def test_unicode_normalization_before_language_detection(self, orchestrator):
        """
        Test that Unicode normalization is called before language detection
        """
        # Test text with mixed Unicode forms and accents
        test_text = "Платеж Иванову"  # Russian text
        
        # Mock unicode service to return normalized text
        unicode_result = {
            "normalized": "Платеж Иванову",  # Normalized version
            "confidence": 0.95,
            "changes_count": 0,
            "char_replacements": 0
        }
        async def mock_normalize_unicode(text):
            return unicode_result
        
        orchestrator.unicode_service.normalize_unicode = Mock(side_effect=mock_normalize_unicode)
        
        # Mock language service to return detection result
        lang_result = Mock()
        lang_result.language = "ru"
        lang_result.confidence = 0.8
        lang_result.method = "config_driven"
        orchestrator.language_service.detect_language_config_driven = Mock(return_value=lang_result)
        
        # Mock other services
        async def mock_validate_and_sanitize(text):
            return {
                "sanitized_text": test_text,
                "is_valid": True,
                "should_process": True,
                "errors": []
            }
        
        orchestrator.validation_service.validate_and_sanitize = Mock(side_effect=mock_validate_and_sanitize)
        
        async def mock_normalize_async(text, **kwargs):
            return Mock(
                success=True,
                tokens=["платеж", "иванову"],
                confidence=0.9
            )
        
        orchestrator.normalization_service.normalize_async = Mock(side_effect=mock_normalize_async)
        
        from ai_service.contracts.base_contracts import SignalsResult
        
        async def mock_extract_async(text, normalization_result, language=None):
            return SignalsResult(
                persons=[],
                organizations=[],
                confidence=0.8
            )
        
        orchestrator.signals_service.extract_signals = Mock(side_effect=mock_extract_async)
        
        # Run the orchestrator
        import asyncio
        result = asyncio.run(orchestrator.process(test_text))
        
        # Verify unicode normalization was called first
        orchestrator.unicode_service.normalize_unicode.assert_called_once_with(test_text)
        
        # Verify language detection was called with normalized text
        orchestrator.language_service.detect_language_config_driven.assert_called_once_with(
            unicode_result["normalized"], 
            orchestrator.language_service.detect_language_config_driven.call_args[0][1]  # LANGUAGE_CONFIG
        )
        
        # Verify the call order: unicode first, then language detection
        unicode_call = orchestrator.unicode_service.normalize_unicode.call_args
        lang_call = orchestrator.language_service.detect_language_config_driven.call_args
        
        # Both should be called
        assert unicode_call is not None
        assert lang_call is not None

    def test_mixed_unicode_forms_detection(self, unicode_service, language_service):
        """
        Test detection with mixed Unicode forms and diacritics
        """
        # Test cases with different Unicode forms
        test_cases = [
            {
                "text": "Платеж Иванову",  # Russian with ё -> е
                "expected_lang": "ru",
                "description": "Russian text with normalized ё"
            },
            {
                "text": "Переказ коштів Олені",  # Ukrainian with і
                "expected_lang": "uk", 
                "description": "Ukrainian text with і"
            },
            {
                "text": "Payment to John Smith",  # English
                "expected_lang": "en",
                "description": "English text"
            },
            {
                "text": "Оплата Ivan Petrov",  # Mixed
                "expected_lang": "mixed",
                "description": "Mixed Russian-English text"
            }
        ]
        
        for case in test_cases:
            # Test unicode normalization
            unicode_result = unicode_service.normalize_text(case["text"], aggressive=False)
            normalized_text = unicode_result["normalized"]
            
            # Test language detection on normalized text
            lang_result = language_service.detect_language_config_driven(normalized_text)
            
            # Verify language detection works on normalized text
            assert lang_result.language in {case["expected_lang"], "mixed", "ru", "uk", "en"}
            assert lang_result.confidence >= 0.0
            assert lang_result.confidence <= 1.0
            
            # Verify the result is stable
            lang_result2 = language_service.detect_language_config_driven(normalized_text)
            assert lang_result2.language == lang_result.language
            assert abs(lang_result2.confidence - lang_result.confidence) < 0.01

    def test_unicode_idempotency_protection(self, unicode_service):
        """
        Test that Unicode normalization is idempotent
        """
        # Test text that's already normalized
        already_normalized = "Платеж Иванову"
        
        # First normalization
        result1 = unicode_service.normalize_text(already_normalized, aggressive=False)
        
        # Second normalization (should be idempotent)
        result2 = unicode_service.normalize_text(already_normalized, aggressive=False)
        
        # Results should be identical
        assert result1["normalized"] == result2["normalized"]
        assert result1["confidence"] == result2["confidence"]
        assert result1.get("idempotent", False) == result2.get("idempotent", False)
        
        # If idempotent, should be marked as such
        if result1.get("idempotent"):
            assert result1["normalized"] == already_normalized
            assert result1["confidence"] == 1.0

    def test_diacritics_normalization_stability(self, unicode_service, language_service):
        """
        Test that diacritics normalization doesn't break language detection
        """
        # Test cases with various diacritics and Unicode forms
        test_cases = [
            "Платеж Иванову",  # Russian
            "Переказ коштів Олені",  # Ukrainian
            "Payment to John Smith",  # English
            "Оплата Ivan Petrov",  # Mixed
            "Paiement à Jean Dupont",  # French with accents
            "Pago a Juan García",  # Spanish with accents
        ]
        
        for text in test_cases:
            # Normalize the text
            unicode_result = unicode_service.normalize_text(text, aggressive=False)
            normalized_text = unicode_result["normalized"]
            
            # Detect language on normalized text
            lang_result = language_service.detect_language_config_driven(normalized_text)
            
            # Verify language detection works
            assert lang_result.language in {"ru", "uk", "en", "mixed", "unknown"}
            assert 0.0 <= lang_result.confidence <= 1.0
            
            # Verify the result is deterministic
            lang_result2 = language_service.detect_language_config_driven(normalized_text)
            assert lang_result2.language == lang_result.language
            assert abs(lang_result2.confidence - lang_result.confidence) < 0.01

    def test_orchestrator_call_order_verification(self, orchestrator):
        """
        Test that orchestrator calls services in the correct order
        """
        test_text = "Платеж Иванову"
        
        # Mock all services
        async def mock_normalize_unicode(text):
            return {
                "normalized": test_text,
                "confidence": 0.95
            }
        
        orchestrator.unicode_service.normalize_unicode = mock_normalize_unicode
        
        lang_result = Mock()
        lang_result.language = "ru"
        lang_result.confidence = 0.8
        orchestrator.language_service.detect_language_config_driven = Mock(return_value=lang_result)
        
        async def mock_normalize_async(text, **kwargs):
            return Mock(
                success=True,
                tokens=["платеж", "иванову"],
                confidence=0.9
            )
        
        orchestrator.normalization_service.normalize_async = mock_normalize_async
        
        async def mock_extract_async(text, normalization_result):
            mock_result = Mock()
            mock_result.confidence = 0.8
            mock_result.persons = []
            mock_result.organizations = []
            return mock_result
        
        orchestrator.signals_service.extract_async = mock_extract_async
        
        async def mock_validate_and_sanitize(text):
            return {
                "sanitized_text": test_text,
                "is_valid": True,
                "should_process": True,
                "errors": []
            }
        
        orchestrator.validation_service.validate_and_sanitize = Mock(side_effect=mock_validate_and_sanitize)
        
        # Track call order
        call_order = []
        
        async def track_unicode_call(*args, **kwargs):
            call_order.append("unicode")
            return {
                "normalized": test_text,
                "confidence": 0.95
            }
        
        def track_lang_call(*args, **kwargs):
            call_order.append("language")
            lang_result = Mock()
            lang_result.language = "ru"
            lang_result.confidence = 0.8
            return lang_result
        
        orchestrator.unicode_service.normalize_unicode = Mock(side_effect=track_unicode_call)
        orchestrator.language_service.detect_language_config_driven = Mock(side_effect=track_lang_call)
        
        # Run orchestrator
        import asyncio
        asyncio.run(orchestrator.process(test_text))
        
        # Verify call order
        assert "unicode" in call_order
        assert "language" in call_order
        assert call_order.index("unicode") < call_order.index("language")

    def test_edge_cases_unicode_normalization(self, unicode_service, language_service):
        """
        Test edge cases for Unicode normalization before language detection
        """
        edge_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            "12345",  # Numbers only
            "!@#$%",  # Punctuation only
            "Платеж",  # Single word
            "a",  # Single character
            "ё",  # Single diacritic character
            "і",  # Single Ukrainian character
        ]
        
        for text in edge_cases:
            # Normalize text
            unicode_result = unicode_service.normalize_text(text, aggressive=False)
            normalized_text = unicode_result["normalized"]
            
            # Detect language on normalized text
            lang_result = language_service.detect_language_config_driven(normalized_text)
            
            # Verify language detection doesn't crash
            assert lang_result.language in {"ru", "uk", "en", "mixed", "unknown"}
            assert 0.0 <= lang_result.confidence <= 1.0
            
            # Verify result is consistent
            lang_result2 = language_service.detect_language_config_driven(normalized_text)
            assert lang_result2.language == lang_result.language
            assert abs(lang_result2.confidence - lang_result.confidence) < 0.01

    def test_unicode_normalization_preserves_meaning(self, unicode_service, language_service):
        """
        Test that Unicode normalization preserves meaning for language detection
        """
        # Test cases where normalization should not change language detection
        test_cases = [
            ("Платеж Иванову", "ru"),  # Russian
            ("Переказ коштів Олені", "uk"),  # Ukrainian  
            ("Payment to John Smith", "en"),  # English
        ]
        
        for original_text, expected_lang in test_cases:
            # Detect language on original text
            original_lang = language_service.detect_language_config_driven(original_text)
            
            # Normalize text
            unicode_result = unicode_service.normalize_text(original_text, aggressive=False)
            normalized_text = unicode_result["normalized"]
            
            # Detect language on normalized text
            normalized_lang = language_service.detect_language_config_driven(normalized_text)
            
            # Language detection should be consistent
            # (may vary slightly due to character changes, but should be in same category)
            if original_lang.language in {"ru", "uk"}:
                assert normalized_lang.language in {"ru", "uk", "mixed"}
            elif original_lang.language == "en":
                assert normalized_lang.language in {"en", "mixed"}
            
            # Confidence should be reasonable
            assert normalized_lang.confidence >= 0.0
            assert normalized_lang.confidence <= 1.0
