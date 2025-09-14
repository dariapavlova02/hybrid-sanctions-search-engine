"""
Integration tests for mixed language handling across all services
"""

import pytest
from unittest.mock import Mock, patch

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
from ai_service.layers.signals.signals_service import SignalsService
from ai_service.layers.language.language_detection_service import LanguageDetectionService
from ai_service.layers.unicode.unicode_service import UnicodeService


class TestMixedLanguageFlow:
    """Test mixed language handling across all services"""

    @pytest.fixture
    def language_service(self):
        """Create LanguageDetectionService instance"""
        return LanguageDetectionService()

    @pytest.fixture
    def unicode_service(self):
        """Create UnicodeService instance"""
        return UnicodeService()

    @pytest.fixture
    def normalization_service(self):
        """Create NormalizationService instance"""
        return NormalizationService()

    @pytest.fixture
    def smart_filter_service(self):
        """Create SmartFilterService instance"""
        return SmartFilterService()

    @pytest.fixture
    def signals_service(self):
        """Create SignalsService instance"""
        return SignalsService()

    def test_mixed_language_detection(self, language_service):
        """
        Test that mixed language is correctly detected
        """
        test_text = "Payment Ivan Petrov від Олени Петренко 12.03.1985"
        
        # Test language detection
        result = language_service.detect_language_config_driven(test_text)
        
        # Should detect as mixed language
        assert result.language == "mixed"
        assert result.confidence >= 0.55  # Lower threshold for mixed language
        
        # Check details contain both scripts
        details = result.details
        assert details.get("cyr_ratio", 0) > 0
        assert details.get("lat_ratio", 0) > 0

    def test_mixed_language_normalization(self, normalization_service, language_service):
        """
        Test normalization of mixed language text
        """
        test_text = "Payment Ivan Petrov від Олени Петренко 12.03.1985"
        
        # Normalize with mixed language
        result = normalization_service.normalize(
            test_text,
            language="mixed",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        
        # Check that normalization succeeded
        assert result.success
        assert result.normalized is not None
        assert len(result.tokens) > 0
        
        # Check that we have both English and Ukrainian names
        normalized_text = result.normalized.lower()
        assert "ivan" in normalized_text or "petrov" in normalized_text
        assert "олена" in normalized_text or "петренко" in normalized_text
        
        # Check that traces contain morph_lang per token
        assert len(result.trace) > 0
        for trace in result.trace:
            assert hasattr(trace, 'morph_lang')
            assert trace.morph_lang in ["en", "ru", "uk", "mixed"]
            
            # English tokens should not have morphology
            if trace.morph_lang == "en":
                assert trace.normal_form is None
            # Slavic tokens should have morphology
            elif trace.morph_lang in ["ru", "uk"]:
                # May or may not have normal_form depending on morphology success
                pass

    def test_mixed_language_smart_filter(self, smart_filter_service):
        """
        Test SmartFilter handling of mixed language
        """
        test_text = "Payment Ivan Petrov від Олени Петренко 12.03.1985"
        
        # Test smart filter
        result = smart_filter_service.should_process_text(test_text)
        
        # Should process mixed language text
        assert result.should_process is True
        assert result.confidence >= 0.0
        
        # Check that mixed language bonus is applied if conditions are met
        signal_details = result.signal_details
        if "mixed_language_bonus" in signal_details:
            bonus_info = signal_details["mixed_language_bonus"]
            assert bonus_info["applied"] is True
            assert bonus_info["bonus"] >= 0.05
            assert bonus_info["bonus"] <= 0.1

    def test_mixed_language_signals(self, signals_service, normalization_service):
        """
        Test Signals extraction from mixed language text
        """
        test_text = "Payment Ivan Petrov від Олени Петренко 12.03.1985"
        
        # First normalize the text
        norm_result = normalization_service.normalize(
            test_text,
            language="mixed",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        
        # Extract signals
        signals_result = signals_service.extract(
            text=test_text,
            normalization_result=norm_result,
            language="mixed"
        )
        
        # Check that signals were extracted
        assert "persons" in signals_result
        assert "organizations" in signals_result
        
        persons = signals_result["persons"]
        assert len(persons) > 0
        
        # Check that we have both English and Ukrainian persons
        person_names = []
        for person in persons:
            if "core" in person:
                person_names.extend(person["core"])
        
        # Should have both English and Ukrainian names
        has_english = any(any(c.isascii() for c in name) for name in person_names)
        has_cyrillic = any(any(ord(c) > 127 for c in name) for name in person_names)
        
        assert has_english, "Should have English names"
        assert has_cyrillic, "Should have Cyrillic names"

    def test_mixed_language_birthdate_proximity(self, signals_service, normalization_service):
        """
        Test that birthdate is correctly linked to nearest person in mixed language
        """
        test_text = "Payment Ivan Petrov від Олени Петренко 12.03.1985"
        
        # First normalize the text
        norm_result = normalization_service.normalize(
            test_text,
            language="mixed",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        
        # Extract signals
        signals_result = signals_service.extract(
            text=test_text,
            normalization_result=norm_result,
            language="mixed"
        )
        
        # Check that birthdate was found and linked
        persons = signals_result["persons"]
        assert len(persons) > 0
        
        # At least one person should have birthdate
        has_birthdate = any(
            person.get("dob") is not None 
            for person in persons
        )
        assert has_birthdate, "Should have found and linked birthdate"

    def test_mixed_language_full_flow(self, language_service, unicode_service, 
                                    normalization_service, smart_filter_service, signals_service):
        """
        Test complete mixed language processing flow
        """
        test_text = "Payment Ivan Petrov від Олени Петренко 12.03.1985"
        
        # Step 1: Unicode normalization
        unicode_result = unicode_service.normalize_text(test_text, aggressive=False)
        normalized_text = unicode_result["normalized"]
        
        # Step 2: Language detection
        lang_result = language_service.detect_language_config_driven(normalized_text)
        assert lang_result.language == "mixed"
        assert lang_result.confidence >= 0.55  # Lower threshold for mixed language
        
        # Step 3: Smart filter
        filter_result = smart_filter_service.should_process_text(normalized_text)
        assert filter_result.should_process is True
        
        # Step 4: Normalization
        norm_result = normalization_service.normalize(
            normalized_text,
            language="mixed",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        assert norm_result.success
        
        # Step 5: Signals extraction
        signals_result = signals_service.extract(
            text=normalized_text,
            normalization_result=norm_result,
            language="mixed"
        )
        
        # Verify final results
        assert "persons" in signals_result
        assert "organizations" in signals_result
        
        persons = signals_result["persons"]
        assert len(persons) > 0
        
        # Check that we have both English and Ukrainian names
        all_names = []
        for person in persons:
            if "core" in person:
                all_names.extend(person["core"])
        
        has_english = any(any(c.isascii() for c in name) for name in all_names)
        has_cyrillic = any(any(ord(c) > 127 for c in name) for name in all_names)
        
        assert has_english, "Should have English names in final result"
        assert has_cyrillic, "Should have Cyrillic names in final result"

    def test_mixed_language_edge_cases(self, language_service, normalization_service):
        """
        Test edge cases for mixed language handling
        """
        test_cases = [
            {
                "text": "Ivan Petrov",
                "expected_lang": "en",
                "description": "English only"
            },
            {
                "text": "Іван Петров",
                "expected_lang": "uk",
                "description": "Ukrainian only"
            },
            {
                "text": "Ivan Петров",
                "expected_lang": "ru",
                "description": "Mixed first/last names (detected as Russian due to Cyrillic dominance)"
            },
            {
                "text": "Payment Ivan Petrov",
                "expected_lang": "en",
                "description": "English only"
            },
            {
                "text": "Payment Ivan Petrov від Олени Петренко",
                "expected_lang": "mixed",
                "description": "English context + Ukrainian names"
            }
        ]
        
        for case in test_cases:
            # Test language detection
            lang_result = language_service.detect_language_config_driven(case["text"])
            
            if case["expected_lang"] == "mixed":
                assert lang_result.language == "mixed"
            else:
                assert lang_result.language in [case["expected_lang"], "mixed"]
            
            # Test normalization
            norm_result = normalization_service.normalize(
                case["text"],
                language=lang_result.language,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            assert norm_result.success
            assert norm_result.normalized is not None

    def test_mixed_language_confidence_scoring(self, smart_filter_service):
        """
        Test that mixed language gets appropriate confidence scoring
        """
        test_cases = [
            {
                "text": "Переказ Ivan Petrov від Олени Петренко",
                "description": "Mixed with both name types"
            },
            {
                "text": "Payment to John Smith",
                "description": "English only"
            },
            {
                "text": "Переказ від Олени Петренко",
                "description": "Ukrainian only"
            }
        ]
        
        for case in test_cases:
            result = smart_filter_service.should_process_text(case["text"])
            
            # All should be processable
            assert result.should_process is True
            assert result.confidence >= 0.0
            assert result.confidence <= 1.0
            
            # Mixed language should have reasonable confidence
            if "Ivan" in case["text"] and "Олени" in case["text"]:
                # This is clearly mixed language
                assert result.confidence >= 0.25  # Should have decent confidence

    def test_mixed_language_token_traces(self, normalization_service):
        """
        Test that token traces correctly show morph_lang per token
        """
        test_text = "Переказ Ivan Petrov від Олени Петренко"
        
        result = normalization_service.normalize(
            test_text,
            language="mixed",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        
        assert result.success
        assert len(result.trace) > 0
        
        # Check that each trace has morph_lang
        for trace in result.trace:
            assert hasattr(trace, 'morph_lang')
            assert trace.morph_lang in ["en", "ru", "uk", "mixed"]
            
            # Check that English tokens don't have morphology
            if trace.morph_lang == "en":
                assert trace.normal_form is None
                assert trace.rule == "english-mixed"
            
            # Check that Slavic tokens have appropriate rules
            elif trace.morph_lang in ["ru", "uk"]:
                assert trace.rule.startswith("slavic-mixed-")
                assert trace.rule.endswith(trace.morph_lang)
