"""
Unit tests for DecisionLogic module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ai_service.layers.smart_filter.decision_logic import (
    DecisionLogic, DecisionType, RiskLevel, DecisionResult
)


class TestDecisionLogic(unittest.TestCase):
    """Test cases for DecisionLogic"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock all the detector dependencies
        with patch('ai_service.layers.smart_filter.decision_logic.NameDetector'):
            with patch('ai_service.layers.smart_filter.decision_logic.CompanyDetector'):
                with patch('ai_service.layers.smart_filter.decision_logic.DocumentDetector'):
                    with patch('ai_service.layers.smart_filter.decision_logic.TerrorismDetector'):
                        with patch('ai_service.layers.smart_filter.decision_logic.ConfidenceScorer'):
                            self.decision_logic = DecisionLogic(enable_terrorism_detection=False)
    
    def test_initialization(self):
        """Test decision logic initialization"""
        self.assertIsNotNone(self.decision_logic)
        self.assertIsNotNone(self.decision_logic.name_detector)
        self.assertIsNotNone(self.decision_logic.company_detector)
        self.assertIsNotNone(self.decision_logic.document_detector)
        self.assertIsNone(self.decision_logic.terrorism_detector)
        self.assertIsNotNone(self.decision_logic.confidence_scorer)
    
    def test_initialization_with_terrorism_detection(self):
        """Test initialization with terrorism detection"""
        with patch('ai_service.layers.smart_filter.decision_logic.NameDetector'):
            with patch('ai_service.layers.smart_filter.decision_logic.CompanyDetector'):
                with patch('ai_service.layers.smart_filter.decision_logic.DocumentDetector'):
                    with patch('ai_service.layers.smart_filter.decision_logic.TerrorismDetector'):
                        with patch('ai_service.layers.smart_filter.decision_logic.ConfidenceScorer'):
                            decision_logic = DecisionLogic(enable_terrorism_detection=True)
                            self.assertIsNotNone(decision_logic.terrorism_detector)
    
    def test_make_decision_empty_text(self):
        """Test decision making with empty text"""
        result = self.decision_logic.make_decision("")
        
        self.assertEqual(result.decision, DecisionType.ALLOW)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.risk_level, RiskLevel.VERY_LOW)
        self.assertIn("Пустой текст", result.reasoning)
        self.assertFalse(result.requires_escalation)
        self.assertGreater(result.processing_time, 0)
    
    def test_make_decision_excluded_text(self):
        """Test decision making with excluded text"""
        # Mock exclusion check
        with patch.object(self.decision_logic, '_is_excluded_text', return_value=True):
            result = self.decision_logic.make_decision("12345")
            
            self.assertEqual(result.decision, DecisionType.ALLOW)
            self.assertIn("исключен", result.reasoning)
    
    def test_collect_all_signals(self):
        """Test signal collection from all detectors"""
        # Mock detector responses
        mock_name_signals = {'confidence': 0.7, 'signals': []}
        mock_company_signals = {'confidence': 0.6, 'signals': []}
        mock_document_signals = {'confidence': 0.5, 'signals': []}
        
        self.decision_logic.name_detector.detect_name_signals.return_value = mock_name_signals
        self.decision_logic.company_detector.detect_company_signals.return_value = mock_company_signals
        self.decision_logic.document_detector.detect_document_signals.return_value = mock_document_signals
        
        signals = self.decision_logic._collect_all_signals("test text")
        
        self.assertIn('names', signals)
        self.assertIn('companies', signals)
        self.assertIn('documents', signals)
        self.assertIn('terrorism', signals)
        self.assertEqual(signals['names'], mock_name_signals)
        self.assertEqual(signals['companies'], mock_company_signals)
        self.assertEqual(signals['documents'], mock_document_signals)
    
    def test_analyze_regular_signals_high_confidence(self):
        """Test regular signal analysis with high confidence"""
        mock_signals = {
            'names': {'confidence': 0.8, 'signal_count': 2, 'high_confidence_signals': [{'confidence': 0.8}]},
            'companies': {'confidence': 0.7, 'signal_count': 1, 'high_confidence_signals': []},
            'documents': {'confidence': 0.6, 'signal_count': 1, 'high_confidence_signals': []},
            'terrorism': {'confidence': 0.0, 'risk_level': 'very_low', 'signals': []}
        }
        
        start_time = time.time()
        result = self.decision_logic._analyze_regular_signals(mock_signals, "test text", None, start_time)
        
        self.assertEqual(result.decision, DecisionType.FULL_SEARCH)
        self.assertGreater(result.confidence, 0.6)
        self.assertIn(result.risk_level, [RiskLevel.MEDIUM, RiskLevel.HIGH])
        self.assertIn("FULL_SEARCH", result.reasoning)
        self.assertFalse(result.requires_escalation)
    
    def test_analyze_regular_signals_low_confidence(self):
        """Test regular signal analysis with low confidence"""
        mock_signals = {
            'names': {'confidence': 0.2, 'signal_count': 1, 'high_confidence_signals': []},
            'companies': {'confidence': 0.1, 'signal_count': 0, 'high_confidence_signals': []},
            'documents': {'confidence': 0.0, 'signal_count': 0, 'high_confidence_signals': []},
            'terrorism': {'confidence': 0.0, 'risk_level': 'very_low', 'signals': []}
        }
        
        start_time = time.time()
        result = self.decision_logic._analyze_regular_signals(mock_signals, "test text", None, start_time)
        
        self.assertEqual(result.decision, DecisionType.ALLOW)
        self.assertLess(result.confidence, 0.3)
        self.assertEqual(result.risk_level, RiskLevel.VERY_LOW)
        self.assertIn("Очень низкая уверенность", result.reasoning)
    
    def test_make_regular_decision_thresholds(self):
        """Test decision thresholds for regular signals"""
        # High confidence -> FULL_SEARCH
        decision, reasoning, recommendations = self.decision_logic._make_regular_decision(
            0.8, {}, "test", None
        )
        self.assertEqual(decision, DecisionType.FULL_SEARCH)
        self.assertIn("Высокая уверенность", reasoning)
        
        # Medium confidence -> FULL_SEARCH
        decision, reasoning, recommendations = self.decision_logic._make_regular_decision(
            0.6, {}, "test", None
        )
        self.assertEqual(decision, DecisionType.FULL_SEARCH)
        self.assertIn("Средняя уверенность", reasoning)
        
        # Low confidence -> MANUAL_REVIEW
        decision, reasoning, recommendations = self.decision_logic._make_regular_decision(
            0.4, {}, "test", None
        )
        self.assertEqual(decision, DecisionType.MANUAL_REVIEW)
        self.assertIn("Низкая уверенность", reasoning)
        
        # Very low confidence -> ALLOW
        decision, reasoning, recommendations = self.decision_logic._make_regular_decision(
            0.1, {}, "test", None
        )
        self.assertEqual(decision, DecisionType.ALLOW)
        self.assertIn("Очень низкая уверенность", reasoning)
    
    def test_determine_risk_level(self):
        """Test risk level determination"""
        # High confidence
        risk = self.decision_logic._determine_risk_level(0.9, {'terrorism': {'risk_level': 'very_low'}})
        self.assertEqual(risk, RiskLevel.HIGH)
        
        # Medium confidence
        risk = self.decision_logic._determine_risk_level(0.7, {'terrorism': {'risk_level': 'very_low'}})
        self.assertEqual(risk, RiskLevel.MEDIUM)
        
        # Low confidence
        risk = self.decision_logic._determine_risk_level(0.4, {'terrorism': {'risk_level': 'very_low'}})
        self.assertEqual(risk, RiskLevel.LOW)
        
        # Very low confidence
        risk = self.decision_logic._determine_risk_level(0.1, {'terrorism': {'risk_level': 'very_low'}})
        self.assertEqual(risk, RiskLevel.VERY_LOW)
        
        # Terrorism override
        risk = self.decision_logic._determine_risk_level(0.1, {'terrorism': {'risk_level': 'critical'}})
        self.assertEqual(risk, RiskLevel.CRITICAL)
    
    def test_is_excluded_text(self):
        """Test text exclusion patterns"""
        # Numeric only
        self.assertTrue(self.decision_logic._is_excluded_text("12345"))
        
        # Special characters only
        self.assertTrue(self.decision_logic._is_excluded_text("@#$%"))
        
        # Common terms
        self.assertTrue(self.decision_logic._is_excluded_text("оплата"))
        
        # Valid text
        self.assertFalse(self.decision_logic._is_excluded_text("Иван Петров"))
    
    def test_update_thresholds(self):
        """Test threshold updates"""
        old_threshold = self.decision_logic.decision_thresholds['full_search_high']
        new_threshold = 0.9
        
        self.decision_logic.update_thresholds({'full_search_high': new_threshold})
        
        self.assertEqual(self.decision_logic.decision_thresholds['full_search_high'], new_threshold)
        self.assertNotEqual(old_threshold, new_threshold)
    
    def test_update_thresholds_invalid_key(self):
        """Test threshold update with invalid key"""
        original_thresholds = self.decision_logic.decision_thresholds.copy()
        
        # Try to update with invalid key
        self.decision_logic.update_thresholds({'invalid_key': 0.5})
        
        # Thresholds should remain unchanged
        self.assertEqual(self.decision_logic.decision_thresholds, original_thresholds)
    
    def test_get_decision_statistics_empty(self):
        """Test decision statistics with empty list"""
        stats = self.decision_logic.get_decision_statistics([])
        self.assertEqual(stats, {})
    
    def test_get_decision_statistics(self):
        """Test decision statistics calculation"""
        # Mock decision results
        decisions = [
            DecisionResult(
                decision=DecisionType.ALLOW,
                confidence=0.1,
                risk_level=RiskLevel.VERY_LOW,
                reasoning="Test",
                detected_signals={},
                recommendations=[],
                processing_time=0.001,
                requires_escalation=False,
                metadata={}
            ),
            DecisionResult(
                decision=DecisionType.FULL_SEARCH,
                confidence=0.8,
                risk_level=RiskLevel.HIGH,
                reasoning="Test",
                detected_signals={},
                recommendations=[],
                processing_time=0.002,
                requires_escalation=True,
                metadata={}
            )
        ]
        
        stats = self.decision_logic.get_decision_statistics(decisions)
        
        self.assertEqual(stats['total_decisions'], 2)
        self.assertIn('allow', stats['decision_distribution'])
        self.assertIn('full_search', stats['decision_distribution'])
        self.assertEqual(stats['decision_distribution']['allow'], 0.5)
        self.assertEqual(stats['decision_distribution']['full_search'], 0.5)
        self.assertEqual(stats['escalation_rate'], 0.5)
        self.assertAlmostEqual(stats['average_confidence'], 0.45)
    
    def test_get_detailed_analysis(self):
        """Test detailed analysis"""
        # Mock the make_decision method to return a controlled result
        mock_result = DecisionResult(
            decision=DecisionType.FULL_SEARCH,
            confidence=0.8,
            risk_level=RiskLevel.MEDIUM,
            reasoning="Test analysis",
            detected_signals={'names': {'confidence': 0.8}},
            recommendations=[],
            processing_time=0.001,
            requires_escalation=False,
            metadata={'test': 'data'}
        )
        
        with patch.object(self.decision_logic, 'make_decision', return_value=mock_result):
            analysis = self.decision_logic.get_detailed_analysis("test text")
            
            self.assertIn('input_text', analysis)
            self.assertIn('decision_result', analysis)
            self.assertIn('detected_signals', analysis)
            self.assertIn('thresholds_used', analysis)
            self.assertIn('signal_weights_used', analysis)
            self.assertEqual(analysis['input_text'], "test text")
            self.assertEqual(analysis['decision_result']['decision'], 'full_search')


class TestDecisionResult(unittest.TestCase):
    """Test cases for DecisionResult dataclass"""
    
    def test_decision_result_creation(self):
        """Test DecisionResult creation"""
        result = DecisionResult(
            decision=DecisionType.ALLOW,
            confidence=0.5,
            risk_level=RiskLevel.LOW,
            reasoning="Test reasoning",
            detected_signals={'test': 'data'},
            recommendations=[],
            processing_time=0.001,
            requires_escalation=False,
            metadata={'key': 'value'}
        )
        
        self.assertEqual(result.decision, DecisionType.ALLOW)
        self.assertEqual(result.confidence, 0.5)
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.reasoning, "Test reasoning")
        self.assertEqual(result.detected_signals, {'test': 'data'})
        self.assertEqual(result.processing_time, 0.001)
        self.assertFalse(result.requires_escalation)
        self.assertEqual(result.metadata, {'key': 'value'})


class TestDecisionTypes(unittest.TestCase):
    """Test cases for decision types and risk levels"""
    
    def test_decision_type_values(self):
        """Test DecisionType enum values"""
        self.assertEqual(DecisionType.ALLOW.value, "allow")
        self.assertEqual(DecisionType.BLOCK.value, "block")
        self.assertEqual(DecisionType.FULL_SEARCH.value, "full_search")
        self.assertEqual(DecisionType.MANUAL_REVIEW.value, "manual_review")
        self.assertEqual(DecisionType.PRIORITY_REVIEW.value, "priority_review")
    
    def test_risk_level_values(self):
        """Test RiskLevel enum values"""
        self.assertEqual(RiskLevel.VERY_LOW.value, "very_low")
        self.assertEqual(RiskLevel.LOW.value, "low")
        self.assertEqual(RiskLevel.MEDIUM.value, "medium")
        self.assertEqual(RiskLevel.HIGH.value, "high")
        self.assertEqual(RiskLevel.CRITICAL.value, "critical")


if __name__ == '__main__':
    unittest.main(verbosity=2)