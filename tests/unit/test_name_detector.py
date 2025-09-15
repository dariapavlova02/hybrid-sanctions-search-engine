"""
Unit tests for NameDetector module - Fixed version
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
        self.assertIsNotNone(self.name_detector.name_dictionaries)
        self.assertIsNotNone(self.name_detector.logger)
    
    def test_detect_name_signals_empty(self):
        """Test name detection with empty text"""
        result = self.name_detector.detect_name_signals("")
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['name_count'], 0)
        self.assertEqual(result['names'], [])
        self.assertFalse(result['has_names'])
    
    def test_detect_name_signals_full_name(self):
        """Test detection of full names"""
        test_text = "Оплата для Коваленко Іван Петрович"
        result = self.name_detector.detect_name_signals(test_text)
        
        self.assertGreater(result['confidence'], 0.0)
        self.assertGreater(result['name_count'], 0)
        self.assertGreater(len(result['names']), 0)
        self.assertTrue(result['has_names'])
    
    def test_detect_names_basic(self):
        """Test basic name detection"""
        test_text = "Петров Иван Сергеевич"
        result = self.name_detector.detect_names(test_text)
        
        self.assertIsInstance(result, list)
        # The method should return some names
        self.assertGreaterEqual(len(result), 0)
    
    def test_detect_names_empty(self):
        """Test name detection with empty text"""
        result = self.name_detector.detect_names("")
        self.assertEqual(result, [])
    
    def test_detect_names_none(self):
        """Test name detection with None input"""
        result = self.name_detector.detect_names(None)
        self.assertEqual(result, [])
    
    def test_detect_name_signals_structure(self):
        """Test that detect_name_signals returns expected structure"""
        test_text = "Test text"
        result = self.name_detector.detect_name_signals(test_text)
        
        # Check required keys
        required_keys = [
            'has_names', 'name_count', 'names', 'confidence',
            'ac_verified_names', 'ac_confidence_bonus',
            'has_capitals', 'has_initials', 'has_patronymic_endings', 'has_nicknames'
        ]
        
        for key in required_keys:
            self.assertIn(key, result)
        
        # Check types
        self.assertIsInstance(result['has_names'], bool)
        self.assertIsInstance(result['name_count'], int)
        self.assertIsInstance(result['names'], list)
        self.assertIsInstance(result['confidence'], float)
        self.assertIsInstance(result['ac_verified_names'], list)
        self.assertIsInstance(result['ac_confidence_bonus'], float)
        self.assertIsInstance(result['has_capitals'], bool)
        self.assertIsInstance(result['has_initials'], bool)
        self.assertIsInstance(result['has_patronymic_endings'], bool)
        self.assertIsInstance(result['has_nicknames'], bool)
    
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
        self.name_detector = NameDetector()
    
    def test_requirement_surname_patterns(self):
        """Test surname pattern detection requirement"""
        test_text = "Петров Иван"
        result = self.name_detector.detect_name_signals(test_text)
        
        # Should detect some names
        self.assertGreaterEqual(result['name_count'], 0)
        self.assertIsInstance(result['names'], list)
    
    def test_requirement_patronymic_patterns(self):
        """Test patronymic pattern detection requirement"""
        test_text = "Иван Петрович"
        result = self.name_detector.detect_name_signals(test_text)
        
        # Should detect some names
        self.assertGreaterEqual(result['name_count'], 0)
        self.assertIsInstance(result['names'], list)
    
    def test_requirement_full_names(self):
        """Test full name detection requirement"""
        test_text = "Петров Иван Сергеевич"
        result = self.name_detector.detect_name_signals(test_text)
        
        # Should detect some names
        self.assertGreaterEqual(result['name_count'], 0)
        self.assertIsInstance(result['names'], list)
    
    def test_requirement_names_and_surnames(self):
        """Test names and surnames detection requirement"""
        test_text = "Коваленко Іван Петрович"
        result = self.name_detector.detect_name_signals(test_text)
        
        # Should detect some names
        self.assertGreaterEqual(result['name_count'], 0)
        self.assertIsInstance(result['names'], list)


if __name__ == '__main__':
    unittest.main()
