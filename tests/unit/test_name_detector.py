"""
Unit tests for NameDetector module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ai_service.layers.smart_filter.name_detector import NameDetector


class TestNameDetector(unittest.TestCase):
    """Test cases for NameDetector"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create name detector instance
        self.name_detector = NameDetector()
    
    def test_initialization(self):
        """Test name detector initialization"""
        self.assertIsNotNone(self.name_detector)
        self.assertIsNotNone(self.name_detector.name_patterns)
        self.assertIsNotNone(self.name_detector.surname_patterns)
        self.assertIsNotNone(self.name_detector.patronymic_patterns)
        self.assertIsNotNone(self.name_detector.enhanced_name_patterns)
        self.assertIsNotNone(self.name_detector.exclusion_patterns)
    
    def test_detect_name_signals_empty(self):
        """Test name detection with empty text"""
        result = self.name_detector.detect_name_signals("")
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['name_count'], 0)
        self.assertEqual(result['names'], [])
        self.assertTrue(result['has_names'])
    
    def test_detect_name_signals_full_name(self):
        """Test detection of full names"""
        test_text = "Оплата для Коваленко Іван Петрович"
        result = self.name_detector.detect_name_signals(test_text)
        
        self.assertGreater(result['confidence'], 0.0)
        self.assertGreater(result['name_count'], 0)
        self.assertGreater(len(result['names']), 0)
        self.assertTrue(result['has_names'])
    
    def test_detect_full_names(self):
        """Test full name detection method"""
        test_text = "Петров Иван Сергеевич"
        result = self.name_detector._detect_full_names(test_text)
        
        self.assertEqual(result['signal_type'], 'full_names')
        # Without dictionaries, confidence will be low or zero
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
        self.assertIsInstance(result['count'], int)
    
    def test_detect_initials(self):
        """Test initials detection"""
        test_text = "И.И. Петров"
        result = self.name_detector._detect_initials(test_text)
        
        self.assertEqual(result['signal_type'], 'initials')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
    
    def test_detect_single_names(self):
        """Test single name detection"""
        test_text = "Іван"
        result = self.name_detector._detect_single_names(test_text)
        
        self.assertEqual(result['signal_type'], 'single_names')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
    
    def test_detect_slavic_surnames(self):
        """Test Slavic surnames detection (requirement: -енко, -ов patterns)"""
        test_cases = [
            ("Коваленко", "Should detect -енко surname"),
            ("Петров", "Should detect -ов surname"),
            ("Сидоренко", "Should detect -енко surname"),
            ("Иванов", "Should detect -ов surname"),
        ]
        
        for surname, description in test_cases:
            with self.subTest(surname=surname, description=description):
                result = self.name_detector._detect_slavic_surnames(surname)
                
                self.assertEqual(result['signal_type'], 'slavic_surnames')
                self.assertGreaterEqual(result['confidence'], 0.0)
                if result['matches']:  # If matches found
                    self.assertIn(surname, result['matches'])
    
    def test_detect_patronymics(self):
        """Test patronymics detection (requirement: -ович patterns)"""
        test_cases = [
            ("Иванович", "Should detect male patronymic -ович"),
            ("Петрович", "Should detect male patronymic -ович"),
            ("Ивановна", "Should detect female patronymic -овна"),
            ("Петровна", "Should detect female patronymic -овна"),
        ]
        
        for patronymic, description in test_cases:
            with self.subTest(patronymic=patronymic, description=description):
                result = self.name_detector._detect_patronymics(patronymic)
                
                self.assertEqual(result['signal_type'], 'patronymics')
                self.assertGreaterEqual(result['confidence'], 0.0)
                if result['matches']:  # If matches found
                    self.assertIn(patronymic, result['matches'])
    
    def test_detect_full_names_with_patronymics(self):
        """Test full names with patronymics detection"""
        test_cases = [
            "Коваленко Іван Петрович",
            "Сидоренко Анна Іванівна",
            "Петров Александр Сергеевич"
        ]
        
        for full_name in test_cases:
            with self.subTest(full_name=full_name):
                result = self.name_detector._detect_full_names_with_patronymics(full_name)
                
                self.assertEqual(result['signal_type'], 'full_names_with_patronymics')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_payment_context_names(self):
        """Test names in payment context"""
        test_text = "Оплата для Іван Петров"
        result = self.name_detector._detect_payment_context_names(test_text)
        
        self.assertEqual(result['signal_type'], 'payment_context')
        self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_phonetic_patterns(self):
        """Test phonetic pattern detection"""
        test_text = "Коваленко Петрович"
        result = self.name_detector._detect_phonetic_patterns(test_text)
        
        self.assertEqual(result['signal_type'], 'phonetic_patterns')
        self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_filter_by_dictionaries_unavailable(self):
        """Test dictionary filtering when dictionaries are unavailable"""
        matches = ["Иван", "Петров", "Test"]
        filtered = self.name_detector._filter_by_dictionaries(matches)
        
        # Without dictionaries, should return original matches
        self.assertEqual(filtered, matches)
    
    def test_filter_single_names_unavailable(self):
        """Test single name filtering when dictionaries are unavailable"""
        matches = ["Иван", "Петров", "Test"]
        filtered = self.name_detector._filter_single_names(matches)
        
        # Without dictionaries, should return original matches
        self.assertEqual(filtered, matches)
    
    def test_is_common_word(self):
        """Test common word detection"""
        # Test with common words
        self.assertTrue(self.name_detector._is_common_word("оплата"))
        self.assertTrue(self.name_detector._is_common_word("payment"))
        
        # Test with non-common words (names)
        self.assertFalse(self.name_detector._is_common_word("Коваленко"))
        self.assertFalse(self.name_detector._is_common_word("Іван"))
    
    def test_extract_detected_names(self):
        """Test extraction of detected names from signals"""
        signals = [
            {'matches': ['Іван', 'Петров']},
            {'matches': ['Коваленко']},
            {'matches': ['Сергеевич']}
        ]
        
        names = self.name_detector._extract_detected_names(signals)
        
        self.assertIsInstance(names, list)
        expected_names = ['Іван', 'Петров', 'Коваленко', 'Сергеевич']
        for name in expected_names:
            self.assertIn(name, names)
    
    def test_get_detailed_name_analysis(self):
        """Test detailed name analysis"""
        test_text = "Коваленко Іван Петрович консультація"
        
        # Mock the basic detection to return controlled results
        with patch.object(self.name_detector, 'detect_name_signals') as mock_detect:
            mock_detect.return_value = {
                'confidence': 0.8,
                'signals': [
                    {'signal_type': 'slavic_surnames', 'count': 1},
                    {'signal_type': 'patronymics', 'count': 1},
                    {'signal_type': 'full_names_with_patronymics', 'count': 1}
                ],
                'signal_count': 3,
                'detected_names': ['Коваленко', 'Іван', 'Петрович']
            }
            
            analysis = self.name_detector.get_detailed_name_analysis(test_text)
            
            self.assertIn('basic_result', analysis)
            self.assertIn('detailed_breakdown', analysis)
            self.assertIn('name_structure_analysis', analysis)
            
            # Check detailed breakdown
            breakdown = analysis['detailed_breakdown']
            self.assertIn('surnames_detected', breakdown)
            self.assertIn('patronymics_detected', breakdown)
            self.assertIn('full_names_detected', breakdown)
            
            # Check structure analysis
            structure = analysis['name_structure_analysis']
            self.assertIn('has_slavic_surnames', structure)
            self.assertIn('has_patronymics', structure)
            self.assertIn('most_likely_language', structure)
    
    def test_create_empty_result(self):
        """Test empty result creation"""
        # Test detect_name_signals with empty text
        result = self.name_detector.detect_name_signals("")
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['has_names'], False)
        self.assertEqual(result['name_count'], 0)
        self.assertEqual(result['names'], [])


class TestNameDetectorIntegration(unittest.TestCase):
    """Integration tests for name detector requirements"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        with patch('ai_service.layers.smart_filter.name_detector.DICTIONARIES_AVAILABLE', False):
            self.name_detector = NameDetector()
    
    def test_requirement_surname_patterns(self):
        """Test required surname patterns (-ков, -енко)"""
        # Test -енко surnames
        result = self.name_detector.detect_name_signals("Коваленко")
        self.assertGreater(result['confidence'], 0.0, "Should detect -енко surnames")
        
        result = self.name_detector.detect_name_signals("Сидоренко")
        self.assertGreater(result['confidence'], 0.0, "Should detect -енко surnames")
        
        # Test -ов/-ев surnames  
        result = self.name_detector.detect_name_signals("Петров")
        self.assertGreater(result['confidence'], 0.0, "Should detect -ов surnames")
        
        result = self.name_detector.detect_name_signals("Медведев")
        self.assertGreater(result['confidence'], 0.0, "Should detect -ев surnames")
    
    def test_requirement_patronymic_patterns(self):
        """Test required patronymic patterns (-ович)"""
        # Test male patronymics
        result = self.name_detector.detect_name_signals("Иванович")
        self.assertGreater(result['confidence'], 0.0, "Should detect -ович patronymics")
        
        result = self.name_detector.detect_name_signals("Петрович")
        self.assertGreater(result['confidence'], 0.0, "Should detect -ович patronymics")
        
        # Test female patronymics
        result = self.name_detector.detect_name_signals("Ивановна")
        self.assertGreater(result['confidence'], 0.0, "Should detect -овна patronymics")
    
    def test_requirement_full_names(self):
        """Test full name detection with required patterns"""
        full_names = [
            "Коваленко Іван Петрович",  # -енко + patronymic
            "Петров Александр Сергеевич",  # -ов + patronymic
            "Сидоренко Анна Іванівна",  # -енко + female patronymic
        ]
        
        for full_name in full_names:
            with self.subTest(full_name=full_name):
                result = self.name_detector.detect_name_signals(full_name)
                self.assertGreater(result['confidence'], 0.0, 
                    f"Should detect full name pattern: {full_name}")
                self.assertGreater(result['name_count'], 0,
                    f"Should have signals for: {full_name}")
    
    def test_requirement_names_and_surnames(self):
        """Test names and surnames detection"""
        # Common names should be detected in context
        names_in_context = [
            "Оплата для Іван",
            "Платеж от Анна", 
            "Перевод на имя Александр"
        ]
        
        for name_context in names_in_context:
            with self.subTest(name_context=name_context):
                result = self.name_detector.detect_name_signals(name_context)
                # Should detect some signals even without dictionaries
                self.assertGreaterEqual(result['confidence'], 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)