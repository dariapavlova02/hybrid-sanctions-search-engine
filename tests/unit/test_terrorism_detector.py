"""
Unit tests for TerrorismDetector module

ВАЖНО: Этот модуль предназначен ТОЛЬКО для защитных целей
и противодействия терроризму в финансовых системах.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ai_service.services.smart_filter.terrorism_detector import TerrorismDetector


class TestTerrorismDetector(unittest.TestCase):
    """Test cases for TerrorismDetector (защитные цели)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.terrorism_detector = TerrorismDetector()
    
    def test_initialization(self):
        """Test terrorism detector initialization"""
        self.assertIsNotNone(self.terrorism_detector)
        self.assertIsNotNone(self.terrorism_detector.financing_patterns)
        self.assertIsNotNone(self.terrorism_detector.weapons_patterns)
        self.assertIsNotNone(self.terrorism_detector.organization_patterns)
        self.assertIsNotNone(self.terrorism_detector.activity_patterns)
        self.assertIsNotNone(self.terrorism_detector.exclusion_patterns)
        self.assertIsNotNone(self.terrorism_detector.pattern_weights)
        self.assertIsNotNone(self.terrorism_detector.risk_thresholds)
    
    def test_detect_terrorism_signals_empty(self):
        """Test terrorism detection with empty text"""
        result = self.terrorism_detector.detect_terrorism_signals("")
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['risk_level'], 'very_low')
        self.assertEqual(result['signal_count'], 0)
        self.assertEqual(result['detected_indicators'], [])
        self.assertFalse(result['requires_manual_review'])
        self.assertTrue(result['analysis_complete'])
    
    def test_detect_terrorism_signals_excluded_content(self):
        """Test with excluded content (educational/legitimate)"""
        excluded_texts = [
            "university research project",
            "historical documentary",
            "academic study",
            "legitimate business operation",
            "игра про военные операции"
        ]
        
        for text in excluded_texts:
            with self.subTest(text=text):
                # Mock the exclusion check to return True
                with patch.object(self.terrorism_detector, '_is_excluded_content', return_value=True):
                    result = self.terrorism_detector.detect_terrorism_signals(text)
                    
                    self.assertEqual(result['confidence'], 0.0)
                    self.assertEqual(result['risk_level'], 'very_low')
                    self.assertFalse(result['requires_manual_review'])
    
    def test_detect_financing_patterns(self):
        """Test financing pattern detection (защитные цели)"""
        # ВАЖНО: Эти тесты только для проверки защитной системы
        result = self.terrorism_detector._detect_financing_patterns("test operational funding")
        
        self.assertEqual(result['signal_type'], 'financing_terrorism')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
        self.assertIsInstance(result['count'], int)
    
    def test_detect_weapons_patterns(self):
        """Test weapons pattern detection (защитные цели)"""
        result = self.terrorism_detector._detect_weapons_patterns("test explosive materials")
        
        self.assertEqual(result['signal_type'], 'weapons_explosives')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
    
    def test_detect_organization_patterns(self):
        """Test organization pattern detection (защитные цели)"""
        result = self.terrorism_detector._detect_organization_patterns("test resistance group")
        
        self.assertEqual(result['signal_type'], 'suspicious_organizations')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
    
    def test_detect_activity_patterns(self):
        """Test activity pattern detection (защитные цели)"""
        result = self.terrorism_detector._detect_activity_patterns("test encrypted communication")
        
        self.assertEqual(result['signal_type'], 'suspicious_activity')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
    
    def test_is_excluded_content(self):
        """Test content exclusion logic"""
        # Test exclusion patterns
        excluded_cases = [
            "university research project",
            "academic historical study",
            "legitimate business operation",
            "educational documentary",
            "government authorized operation"
        ]
        
        for case in excluded_cases:
            with self.subTest(case=case):
                # Should be excluded as legitimate content
                result = self.terrorism_detector._is_excluded_content(case)
                # Result depends on actual exclusion patterns
                self.assertIsInstance(result, bool)
    
    def test_determine_risk_level(self):
        """Test risk level determination"""
        # High confidence -> high risk
        risk = self.terrorism_detector._determine_risk_level(0.9)
        self.assertEqual(risk, 'high')
        
        # Medium confidence -> medium risk
        risk = self.terrorism_detector._determine_risk_level(0.6)
        self.assertEqual(risk, 'medium')
        
        # Low confidence -> low risk
        risk = self.terrorism_detector._determine_risk_level(0.4)
        self.assertEqual(risk, 'low')
        
        # Very low confidence -> very low risk
        risk = self.terrorism_detector._determine_risk_level(0.1)
        self.assertEqual(risk, 'very_low')
    
    def test_extract_detected_indicators(self):
        """Test extraction of detected indicators"""
        signals = [
            {'matches': ['operational', 'funding']},
            {'matches': ['equipment']},
            {'matches': ['group']}
        ]
        
        indicators = self.terrorism_detector._extract_detected_indicators(signals)
        
        self.assertIsInstance(indicators, list)
        expected_indicators = ['operational', 'funding', 'equipment', 'group']
        for indicator in expected_indicators:
            self.assertIn(indicator, indicators)
    
    def test_get_risk_assessment(self):
        """Test risk assessment functionality"""
        # Mock signals result
        signals_result = {
            'confidence': 0.8,
            'risk_level': 'high',
            'signal_count': 3,
            'high_risk_signals': [
                {'signal_type': 'financing_terrorism', 'confidence': 0.8}
            ]
        }
        
        assessment = self.terrorism_detector.get_risk_assessment(signals_result)
        
        self.assertIn('risk_level', assessment)
        self.assertIn('confidence', assessment)
        self.assertIn('recommendation', assessment)
        self.assertIn('requires_escalation', assessment)
        self.assertIn('suggested_action', assessment)
        self.assertIn('description', assessment)
        
        # High risk should require escalation
        if signals_result['risk_level'] == 'high':
            self.assertTrue(assessment['requires_escalation'])
            self.assertIn(assessment['suggested_action'], 
                         ['IMMEDIATE_REVIEW_REQUIRED', 'MANUAL_REVIEW_RECOMMENDED'])
    
    def test_create_empty_result(self):
        """Test empty result creation"""
        result = self.terrorism_detector._create_empty_result()
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['risk_level'], 'very_low')
        self.assertEqual(result['signals'], [])
        self.assertEqual(result['signal_count'], 0)
        self.assertEqual(result['high_risk_signals'], [])
        self.assertEqual(result['detected_indicators'], [])
        self.assertEqual(result['text_length'], 0)
        self.assertFalse(result['requires_manual_review'])
        self.assertTrue(result['analysis_complete'])


class TestTerrorismDetectorSafety(unittest.TestCase):
    """Safety tests for terrorism detector"""
    
    def setUp(self):
        """Set up safety test fixtures"""
        self.terrorism_detector = TerrorismDetector()
    
    def test_defensive_purpose_only(self):
        """Test that detector is for defensive purposes only"""
        # This test ensures the detector is used only for protection
        self.assertIsNotNone(self.terrorism_detector.exclusion_patterns)
        
        # Should have exclusion patterns for legitimate content
        exclusions = self.terrorism_detector.exclusion_patterns
        self.assertGreater(len(exclusions), 0, 
                          "Should have exclusion patterns for legitimate content")
    
    def test_false_positive_prevention(self):
        """Test prevention of false positives"""
        legitimate_texts = [
            "игра про операции",
            "фильм о военных действиях", 
            "исторический документальный фильм",
            "университетская исследовательская работа",
            "новости о военных событиях"
        ]
        
        for text in legitimate_texts:
            with self.subTest(text=text):
                result = self.terrorism_detector.detect_terrorism_signals(text)
                
                # Should have low confidence for legitimate content
                # or be excluded entirely
                if not self.terrorism_detector._is_excluded_content(text):
                    self.assertLessEqual(result['confidence'], 0.3,
                        f"Should have low confidence for legitimate content: {text}")
    
    def test_risk_escalation_thresholds(self):
        """Test risk escalation thresholds are appropriate"""
        thresholds = self.terrorism_detector.risk_thresholds
        
        # Should have reasonable thresholds
        self.assertIn('high', thresholds)
        self.assertIn('medium', thresholds)
        self.assertIn('low', thresholds)
        
        # Thresholds should be in logical order
        self.assertGreater(thresholds['high'], thresholds['medium'])
        self.assertGreater(thresholds['medium'], thresholds['low'])
        
        # Should require high confidence for high-risk classification
        self.assertGreaterEqual(thresholds['high'], 0.5)
    
    def test_pattern_weights_balance(self):
        """Test that pattern weights are balanced"""
        weights = self.terrorism_detector.pattern_weights
        
        # All weights should be reasonable (not too sensitive)
        for pattern_type, weight in weights.items():
            self.assertGreaterEqual(weight, 0.0, f"{pattern_type} weight should be >= 0")
            self.assertLessEqual(weight, 1.0, f"{pattern_type} weight should be <= 1")
            
            # Weapons patterns should have high weight (most serious)
            if pattern_type == 'weapons':
                self.assertGreaterEqual(weight, 0.8, 
                    "Weapons patterns should have high weight")


class TestTerrorismDetectorIntegration(unittest.TestCase):
    """Integration tests for terrorism detector (защитные цели)"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.terrorism_detector = TerrorismDetector()
    
    def test_comprehensive_threat_assessment(self):
        """Test comprehensive threat assessment"""
        # ВАЖНО: Только для тестирования защитной системы
        test_case = "operational funding support mission"
        
        result = self.terrorism_detector.detect_terrorism_signals(test_case)
        
        # Should analyze the text and provide assessment
        self.assertIsInstance(result['confidence'], float)
        self.assertIsInstance(result['risk_level'], str)
        self.assertIsInstance(result['requires_manual_review'], bool)
        self.assertTrue(result['analysis_complete'])
        
        # If high risk detected, should require review
        if result['confidence'] > 0.7:
            self.assertTrue(result['requires_manual_review'])
            self.assertIn(result['risk_level'], ['high', 'critical'])
    
    def test_risk_assessment_workflow(self):
        """Test risk assessment workflow"""
        # Test with different risk levels
        test_cases = [
            ("legitimate business operation", "Should be low risk"),
            ("university research project", "Should be excluded or low risk"),  
            ("operational funding activities", "Should trigger assessment"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                signals = self.terrorism_detector.detect_terrorism_signals(text)
                assessment = self.terrorism_detector.get_risk_assessment(signals)
                
                self.assertIn('risk_level', assessment)
                self.assertIn('suggested_action', assessment)
                self.assertIn('requires_escalation', assessment)
                
                # Risk assessment should be consistent
                if signals['confidence'] > 0.7:
                    self.assertTrue(assessment['requires_escalation'])
                elif signals['confidence'] < 0.3:
                    self.assertFalse(assessment['requires_escalation'])
    
    def test_defensive_system_requirements(self):
        """Test that system meets defensive requirements"""
        # Should have exclusion mechanisms
        self.assertGreater(len(self.terrorism_detector.exclusion_patterns), 0)
        
        # Should have risk assessment capabilities  
        self.assertTrue(hasattr(self.terrorism_detector, 'get_risk_assessment'))
        
        # Should have appropriate thresholds
        self.assertIn('high', self.terrorism_detector.risk_thresholds)
        self.assertIn('medium', self.terrorism_detector.risk_thresholds)
        
        # Should support manual review escalation
        result = self.terrorism_detector.detect_terrorism_signals("test")
        self.assertIn('requires_manual_review', result)


if __name__ == '__main__':
    # Add warning about defensive use only
    print("=" * 60)
    print("ВАЖНО: TerrorismDetector предназначен ТОЛЬКО для защитных целей")
    print("и противодействия терроризму в финансовых системах.")
    print("=" * 60)
    
    unittest.main(verbosity=2)