"""
Unit tests for SmartFilterService
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
from ai_service.layers.smart_filter.decision_logic import DecisionType, RiskLevel


class TestSmartFilterService(unittest.TestCase):
    """Test cases for SmartFilterService"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock the dependencies to avoid import issues
        with patch('ai_service.services.smart_filter.smart_filter_service.SignalService'):
            with patch('ai_service.services.smart_filter.smart_filter_service.DecisionLogic'):
                self.smart_filter = SmartFilterService(enable_terrorism_detection=False)

    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.smart_filter)
        self.assertIsNotNone(self.smart_filter.company_detector)
        self.assertIsNotNone(self.smart_filter.name_detector)
        self.assertIsNotNone(self.smart_filter.document_detector)
        self.assertIsNone(self.smart_filter.terrorism_detector)  # Disabled

    def test_initialization_with_terrorism_detection(self):
        """Test service initialization with terrorism detection enabled"""
        with patch('ai_service.services.smart_filter.smart_filter_service.SignalService'):
            with patch('ai_service.services.smart_filter.smart_filter_service.DecisionLogic'):
                with patch('ai_service.services.smart_filter.smart_filter_service.TerrorismDetector'):
                    smart_filter = SmartFilterService(enable_terrorism_detection=True)
                    self.assertIsNotNone(smart_filter.terrorism_detector)

    def test_should_process_text_empty(self):
        """Test processing empty text"""
        result = self.smart_filter.should_process_text("")

        self.assertFalse(result.should_process)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.detected_signals, [])
        self.assertEqual(result.estimated_complexity, "none")

    def test_should_process_text_excluded(self):
        """Test processing excluded text"""
        # Mock the exclusion check
        with patch.object(self.smart_filter, '_is_excluded_text', return_value=True):
            result = self.smart_filter.should_process_text("оплата")

            self.assertFalse(result.should_process)
            self.assertIn("excluded", result.processing_recommendation)

    def test_should_process_text_with_signals(self):
        """Test processing text with signals"""
        # Mock the detectors to return signals
        mock_company_signals = {
            'confidence': 0.7,
            'signals': [{'signal_type': 'legal_entities', 'confidence': 0.7}]
        }
        mock_name_signals = {
            'confidence': 0.8,
            'signals': [{'signal_type': 'full_names', 'confidence': 0.8}]
        }

        with patch.object(self.smart_filter.company_detector, 'detect_company_signals', return_value=mock_company_signals):
            with patch.object(self.smart_filter.name_detector, 'detect_name_signals', return_value=mock_name_signals):
                with patch.object(self.smart_filter.confidence_scorer, 'calculate_confidence', return_value=0.8):
                    result = self.smart_filter.should_process_text("ООО Тест Иван Иванов")

                    self.assertTrue(result.should_process)
                    self.assertGreater(result.confidence, 0.0)
                    self.assertIn('company', result.detected_signals)
                    self.assertIn('name', result.detected_signals)

    @patch('ai_service.services.smart_filter.smart_filter_service.DecisionLogic')
    def test_make_smart_decision(self, mock_decision_logic):
        """Test smart decision making"""
        # Mock decision result
        mock_decision_result = MagicMock()
        mock_decision_result.decision = DecisionType.FULL_SEARCH
        mock_decision_result.confidence = 0.8
        mock_decision_result.risk_level = RiskLevel.MEDIUM
        mock_decision_result.reasoning = "Test reasoning"
        mock_decision_result.recommendations = ["Test recommendation"]
        mock_decision_result.requires_escalation = False
        mock_decision_result.processing_time = 0.001
        mock_decision_result.detected_signals = {}
        mock_decision_result.metadata = {}

        mock_decision_logic.return_value.make_decision.return_value = mock_decision_result

        with patch('ai_service.services.smart_filter.smart_filter_service.SignalService'):
            smart_filter = SmartFilterService()
            result = smart_filter.make_smart_decision("test text")

            self.assertEqual(result['decision_type'], 'full_search')
            self.assertEqual(result['confidence'], 0.8)
            self.assertEqual(result['risk_level'], 'medium')
            self.assertTrue(result['should_process'])
            self.assertFalse(result['blocked'])

    def test_analyze_payment_description(self):
        """Test payment description analysis"""
        # Mock dependencies
        with patch.object(self.smart_filter, 'should_process_text') as mock_should_process:
            mock_should_process.return_value = MagicMock(
                should_process=True,
                confidence=0.7,
                detected_signals=['name'],
                processing_recommendation="Test",
                estimated_complexity="medium"
            )

            with patch.object(self.smart_filter, '_analyze_language_composition') as mock_lang_analysis:
                mock_lang_analysis.return_value = {
                    'cyrillic_ratio': 0.8,
                    'latin_ratio': 0.2,
                    'is_mixed_language': True
                }

                result = self.smart_filter.analyze_payment_description("Тест payment")

                self.assertIn('filter_result', result)
                self.assertIn('text_statistics', result)
                self.assertIn('language_analysis', result)
                self.assertEqual(result['text_statistics']['word_count'], 2)

    def test_language_detection(self):
        """Test language detection"""
        # Test Ukrainian text
        ukrainian_text = "Оплата за послуги"
        detected_lang = self.smart_filter._detect_language(ukrainian_text)
        self.assertEqual(detected_lang, 'ukrainian')

        # Test English text
        english_text = "Payment for services"
        detected_lang = self.smart_filter._detect_language(english_text)
        self.assertEqual(detected_lang, 'english')

    def test_text_normalization(self):
        """Test text normalization"""
        input_text = "  Тест   с   лишними   пробелами  "
        normalized = self.smart_filter._normalize_text(input_text)

        self.assertEqual(normalized, "Тест с лишними пробелами")

    def test_exclusion_patterns(self):
        """Test exclusion patterns"""
        # Test numeric only
        self.assertTrue(self.smart_filter._is_excluded_text("12345"))

        # Test common terms
        self.assertTrue(self.smart_filter._is_excluded_text("оплата"))

        # Test valid text
        self.assertFalse(self.smart_filter._is_excluded_text("Иван Петров"))

    def test_date_only_text(self):
        """Test date-only text detection"""
        # Test date formats
        self.assertTrue(self.smart_filter._is_date_only_text("2024-01-15"))
        self.assertTrue(self.smart_filter._is_date_only_text("15.01.2024"))
        self.assertTrue(self.smart_filter._is_date_only_text("сьогодні"))

        # Test non-date text
        self.assertFalse(self.smart_filter._is_date_only_text("Иван Петров"))
        self.assertFalse(self.smart_filter._is_date_only_text("ООО Тест"))

    def test_language_composition_analysis(self):
        """Test language composition analysis"""
        mixed_text = "Hello Привет"
        analysis = self.smart_filter._analyze_language_composition(mixed_text)

        self.assertIn('cyrillic_ratio', analysis)
        self.assertIn('latin_ratio', analysis)
        self.assertIn('is_mixed_language', analysis)
        self.assertTrue(analysis['is_mixed_language'])
        self.assertGreater(analysis['cyrillic_ratio'], 0)
        self.assertGreater(analysis['latin_ratio'], 0)

    def test_service_words_cleaning(self):
        """Test service words cleaning"""
        text_with_service_words = "оплата за консультацію Петров Іван"
        cleaned = self.smart_filter._clean_service_words(text_with_service_words)

        # Should remove "оплата за" from the beginning
        self.assertNotEqual(cleaned, text_with_service_words)
        self.assertIn("Петров", cleaned)


class TestSmartFilterIntegration(unittest.TestCase):
    """Integration tests for smart filter system"""

    def setUp(self):
        """Set up integration test fixtures"""
        # Only run integration tests if we can import dependencies
        try:
            self.smart_filter = SmartFilterService(enable_terrorism_detection=False)
            self.integration_available = True
        except ImportError:
            self.integration_available = False
            self.skipTest("Dependencies not available for integration tests")

    def test_person_name_detection(self):
        """Test detection of person names"""
        if not self.integration_available:
            self.skipTest("Integration dependencies not available")

        test_cases = [
            "Оплата для Коваленко Іван Петрович",
            "Платеж от Сидоренко",
            "Перевод на имя Петров Александр Сергеевич"
        ]

        for test_case in test_cases:
            with self.subTest(text=test_case):
                result = self.smart_filter.should_process_text(test_case)
                # Should detect name signals
                self.assertGreater(result.confidence, 0.0)

    def test_company_detection(self):
        """Test detection of companies"""
        if not self.integration_available:
            self.skipTest("Integration dependencies not available")

        test_cases = [
            'ТОВ "Адамз Грейн"',
            "ПриватБанк послуги",
            "ООО Технологии"
        ]

        for test_case in test_cases:
            with self.subTest(text=test_case):
                result = self.smart_filter.should_process_text(test_case)
                # Should detect company signals
                self.assertGreater(result.confidence, 0.0)

    def test_safe_content_handling(self):
        """Test handling of safe content"""
        if not self.integration_available:
            self.skipTest("Integration dependencies not available")

        safe_texts = [
            "Оплата за товар",
            "1000 грн",
            "консультація"
        ]

        for safe_text in safe_texts:
            with self.subTest(text=safe_text):
                result = self.smart_filter.should_process_text(safe_text)
                # Should have low confidence for safe content
                self.assertLessEqual(result.confidence, 0.3)


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)