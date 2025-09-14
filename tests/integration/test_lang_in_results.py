"""
Integration tests for language and confidence exposure in results.

Tests that language detection results are properly exposed in both
NormalizationResult and ProcessingResult (UnifiedProcessingResult).
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.layers.language.language_detection_service import LanguageDetectionService
from src.ai_service.layers.unicode.unicode_service import UnicodeService
from src.ai_service.layers.signals.signals_service import SignalsService
from src.ai_service.layers.validation.validation_service import ValidationService
from src.ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
from src.ai_service.config import LANGUAGE_CONFIG
from src.ai_service.utils.types import LanguageDetectionResult


class TestLanguageInResults:
    """Test language and confidence exposure in results"""

    @pytest.fixture
    def language_service(self):
        """Mock language detection service"""
        service = Mock(spec=LanguageDetectionService)
        service.detect_language_config_driven = Mock(return_value=LanguageDetectionResult(
            language="ru",
            confidence=0.85,
            details={"cyr_ratio": 0.8, "lat_ratio": 0.1}
        ))
        return service

    @pytest.fixture
    def unicode_service(self):
        """Mock unicode service"""
        service = Mock(spec=UnicodeService)
        service.normalize_unicode = AsyncMock(return_value={
            "normalized": "test text",
            "confidence": 1.0,
            "changes_made": 0,
            "idempotent": True
        })
        return service

    @pytest.fixture
    def normalization_service(self):
        """Mock normalization service"""
        service = Mock(spec=NormalizationService)
        return service

    @pytest.fixture
    def signals_service(self):
        """Mock signals service"""
        service = Mock(spec=SignalsService)
        service.extract_async = AsyncMock(return_value={
            "persons": [],
            "organizations": [],
            "extras": {"dates": [], "amounts": []},
            "confidence": 0.0
        })
        return service

    @pytest.fixture
    def validation_service(self):
        """Mock validation service"""
        service = Mock(spec=ValidationService)
        service.validate_and_sanitize = AsyncMock(return_value={
            "sanitized_text": "test text",
            "is_valid": True,
            "should_process": True,
            "errors": []
        })
        return service

    @pytest.fixture
    def smart_filter_service(self):
        """Mock smart filter service"""
        service = Mock(spec=SmartFilterService)
        service.should_process_text = Mock(return_value=Mock(
            should_process=True,
            confidence=0.8,
            detected_signals=['name'],
            signal_details={},
            processing_recommendation="Process",
            estimated_complexity="low"
        ))
        return service

    @pytest.fixture
    def orchestrator(self, language_service, unicode_service, normalization_service, 
                    signals_service, validation_service, smart_filter_service):
        """Create orchestrator with mocked services"""
        return UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
            smart_filter_service=smart_filter_service,
            enable_smart_filter=True
        )

    @pytest.mark.asyncio
    async def test_russian_language_in_results(self, orchestrator, language_service, normalization_service):
        """Test Russian language detection in results"""
        text = "Платеж Иванову"
        
        # Mock language detection result
        lang_result = LanguageDetectionResult(
            language="ru",
            confidence=0.85,
            details={"method": "config_driven", "reason": "cyrillic_russian"}
        )
        language_service.detect_language_config_driven.return_value = lang_result
        
        # Mock normalization result
        from src.ai_service.utils.trace import NormalizationResult, TokenTrace
        norm_result = NormalizationResult(
            normalized="Иванову",
            tokens=["Иванову"],
            trace=[TokenTrace(
                token="Иванову",
                role="surname",
                rule="russian",
                output="Иванову"
            )],
            errors=[],
            language="ru",
            confidence=0.85,
            original_length=len(text),
            normalized_length=7,
            token_count=1,
            processing_time=0.01,
            success=True
        )
        normalization_service.normalize_async = AsyncMock(return_value=norm_result)
        
        # Process text
        result = await orchestrator.process(text)
        
        # Verify language and confidence in processing result
        assert result.language == "ru"
        assert result.language_confidence == 0.85
        assert 0.0 <= result.language_confidence <= 1.0
        
        # Verify normalization result was called with correct language
        normalization_service.normalize_async.assert_called_once()
        call_args = normalization_service.normalize_async.call_args
        assert call_args[1]["language"] == "ru"

    @pytest.mark.asyncio
    async def test_ukrainian_language_in_results(self, orchestrator, language_service, normalization_service):
        """Test Ukrainian language detection in results"""
        text = "Переказ коштів Олені"
        
        # Mock language detection result
        lang_result = LanguageDetectionResult(
            language="uk",
            confidence=0.92,
            details={"method": "config_driven", "reason": "cyrillic_ukrainian"}
        )
        language_service.detect_language_config_driven.return_value = lang_result
        
        # Mock normalization result
        from src.ai_service.utils.trace import NormalizationResult, TokenTrace
        norm_result = NormalizationResult(
            normalized="Олені",
            tokens=["Олені"],
            trace=[TokenTrace(
                token="Олені",
                role="surname",
                rule="ukrainian",
                output="Олені"
            )],
            errors=[],
            language="uk",
            confidence=0.92,
            original_length=len(text),
            normalized_length=5,
            token_count=1,
            processing_time=0.01,
            success=True
        )
        normalization_service.normalize_async = AsyncMock(return_value=norm_result)
        
        # Process text
        result = await orchestrator.process(text)
        
        # Verify language and confidence in processing result
        assert result.language == "uk"
        assert result.language_confidence == 0.92
        assert 0.0 <= result.language_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_english_language_in_results(self, orchestrator, language_service, normalization_service):
        """Test English language detection in results"""
        text = "Payment to John Smith"
        
        # Mock language detection result
        lang_result = LanguageDetectionResult(
            language="en",
            confidence=0.78,
            details={"method": "config_driven", "reason": "latin"}
        )
        language_service.detect_language_config_driven.return_value = lang_result
        
        # Mock normalization result
        from src.ai_service.utils.trace import NormalizationResult, TokenTrace
        norm_result = NormalizationResult(
            normalized="John Smith",
            tokens=["John", "Smith"],
            trace=[
                TokenTrace(token="John", role="given", rule="english", output="John"),
                TokenTrace(token="Smith", role="surname", rule="english", output="Smith")
            ],
            errors=[],
            language="en",
            confidence=0.78,
            original_length=len(text),
            normalized_length=10,
            token_count=2,
            processing_time=0.01,
            success=True
        )
        normalization_service.normalize_async = AsyncMock(return_value=norm_result)
        
        # Process text
        result = await orchestrator.process(text)
        
        # Verify language and confidence in processing result
        assert result.language == "en"
        assert result.language_confidence == 0.78
        assert 0.0 <= result.language_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_mixed_language_in_results(self, orchestrator, language_service, normalization_service):
        """Test mixed language detection in results"""
        text = "Payment Ivan Petrov від Олени Петренко"
        
        # Mock language detection result
        lang_result = LanguageDetectionResult(
            language="mixed",
            confidence=0.65,
            details={"method": "config_driven", "reason": "mixed_language"}
        )
        language_service.detect_language_config_driven.return_value = lang_result
        
        # Mock normalization result
        from src.ai_service.utils.trace import NormalizationResult, TokenTrace
        norm_result = NormalizationResult(
            normalized="Ivan Petrov Олени Петренко",
            tokens=["Ivan", "Petrov", "Олени", "Петренко"],
            trace=[
                TokenTrace(token="Ivan", role="given", rule="english-mixed", morph_lang="en", output="Ivan"),
                TokenTrace(token="Petrov", role="surname", rule="english-mixed", morph_lang="en", output="Petrov"),
                TokenTrace(token="Олени", role="surname", rule="slavic-mixed-uk", morph_lang="uk", output="Олени"),
                TokenTrace(token="Петренко", role="surname", rule="slavic-mixed-uk", morph_lang="uk", output="Петренко")
            ],
            errors=[],
            language="mixed",
            confidence=0.65,
            original_length=len(text),
            normalized_length=26,
            token_count=4,
            processing_time=0.01,
            success=True
        )
        normalization_service.normalize_async = AsyncMock(return_value=norm_result)
        
        # Process text
        result = await orchestrator.process(text)
        
        # Verify language and confidence in processing result
        assert result.language == "mixed"
        assert result.language_confidence == 0.65
        assert 0.0 <= result.language_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_unknown_language_in_results(self, orchestrator, language_service, normalization_service):
        """Test unknown language detection in results"""
        text = "12345 --- $$$"
        
        # Mock language detection result
        lang_result = LanguageDetectionResult(
            language="unknown",
            confidence=0.0,
            details={"method": "config_driven", "reason": "insufficient_letters"}
        )
        language_service.detect_language_config_driven.return_value = lang_result
        
        # Mock normalization result
        from src.ai_service.utils.trace import NormalizationResult, TokenTrace
        norm_result = NormalizationResult(
            normalized="",
            tokens=[],
            trace=[],
            errors=["No valid names found"],
            language="unknown",
            confidence=0.0,
            original_length=len(text),
            normalized_length=0,
            token_count=0,
            processing_time=0.01,
            success=False
        )
        normalization_service.normalize_async = AsyncMock(return_value=norm_result)
        
        # Process text
        result = await orchestrator.process(text)
        
        # Verify language and confidence in processing result
        assert result.language == "unknown"
        assert result.language_confidence == 0.0
        assert 0.0 <= result.language_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_range_validation(self, orchestrator, language_service, normalization_service):
        """Test that confidence values are always in [0, 1] range"""
        test_cases = [
            ("ru", 0.0),
            ("uk", 0.5),
            ("en", 1.0),
            ("mixed", 0.3),
            ("unknown", 0.0)
        ]
        
        for lang, conf in test_cases:
            text = f"Test text for {lang}"
            
            # Mock language detection result
            lang_result = LanguageDetectionResult(
                language=lang,
                confidence=conf,
                details={"method": "config_driven", "reason": "test"}
            )
            language_service.detect_language_config_driven.return_value = lang_result
            
            # Mock normalization result
            from src.ai_service.utils.trace import NormalizationResult
            norm_result = NormalizationResult(
                normalized="Test",
                tokens=["Test"],
                trace=[],
                errors=[],
                language=lang,
                confidence=conf,
                original_length=len(text),
                normalized_length=4,
                token_count=1,
                processing_time=0.01,
                success=True
            )
            normalization_service.normalize_async = AsyncMock(return_value=norm_result)
            
            # Process text
            result = await orchestrator.process(text)
            
            # Verify confidence is in valid range
            assert 0.0 <= result.language_confidence <= 1.0, f"Confidence {result.language_confidence} not in [0, 1] for language {lang}"
            assert result.language == lang

    def test_normalization_result_language_fields(self):
        """Test that NormalizationResult has required language fields"""
        from src.ai_service.utils.trace import NormalizationResult
        
        # Test that fields exist and can be set
        result = NormalizationResult(
            normalized="test",
            tokens=["test"],
            trace=[],
            language="en",
            confidence=0.8
        )
        
        assert hasattr(result, 'language')
        assert hasattr(result, 'confidence')
        assert result.language == "en"
        assert result.confidence == 0.8

    def test_processing_result_language_fields(self):
        """Test that UnifiedProcessingResult has required language fields"""
        from src.ai_service.contracts.base_contracts import UnifiedProcessingResult
        from src.ai_service.contracts.decision_contracts import SignalsResult
        
        # Test that fields exist and can be set
        result = UnifiedProcessingResult(
            original_text="test",
            language="en",
            language_confidence=0.8,
            normalized_text="test",
            tokens=["test"],
            trace=[],
            signals=SignalsResult(persons=[], organizations=[], extras={}, confidence=0.0)
        )
        
        assert hasattr(result, 'language')
        assert hasattr(result, 'language_confidence')
        assert result.language == "en"
        assert result.language_confidence == 0.8
