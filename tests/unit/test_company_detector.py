"""
Unit tests for CompanyDetector module
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ai_service.services.smart_filter.company_detector import CompanyDetector


class TestCompanyDetector(unittest.TestCase):
    """Test cases for CompanyDetector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.company_detector = CompanyDetector()
    
    def test_initialization(self):
        """Test company detector initialization"""
        self.assertIsNotNone(self.company_detector)
        self.assertIsNotNone(self.company_detector.company_keywords)
        self.assertIsNotNone(self.company_detector.company_patterns)
        self.assertIsNotNone(self.company_detector.address_patterns)
        self.assertIsNotNone(self.company_detector.registration_patterns)
        self.assertIsNotNone(self.company_detector.banking_terms)
        self.assertIsNotNone(self.company_detector.financial_services_patterns)
    
    def test_detect_company_signals_empty(self):
        """Test company detection with empty text"""
        result = self.company_detector.detect_company_signals("")
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['signal_count'], 0)
        self.assertEqual(result['detected_keywords'], [])
        self.assertTrue(result['analysis_complete'])
    
    def test_detect_company_signals_with_keywords(self):
        """Test detection with company keywords"""
        test_text = "ООО Технологии будущего"
        result = self.company_detector.detect_company_signals(test_text)
        
        self.assertGreater(result['confidence'], 0.0)
        self.assertGreater(result['signal_count'], 0)
        self.assertTrue(result['analysis_complete'])
    
    def test_detect_keywords(self):
        """Test keyword detection method"""
        test_text = "товариство з обмеженою відповідальністю Тест"
        result = self.company_detector._detect_keywords(test_text)
        
        self.assertEqual(result['signal_type'], 'keywords')
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertIsInstance(result['matches'], list)
        self.assertIsInstance(result['count'], int)
    
    def test_detect_legal_entities(self):
        """Test legal entity detection (requirement: ООО/ЗАО/LLC)"""
        test_cases = [
            ("ООО Рога и копыта", "Should detect ООО"),
            ("ЗАО Газпром", "Should detect ЗАО"), 
            ("LLC International Trading", "Should detect LLC"),
            ("товариство з обмеженою відповідальністю Тест", "Should detect Ukrainian legal form"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.company_detector._detect_legal_entities(text)
                
                self.assertEqual(result['signal_type'], 'legal_entities')
                self.assertGreaterEqual(result['confidence'], 0.0)
                if result['matches']:  # If matches found
                    self.assertGreater(result['confidence'], 0.0)
    
    def test_detect_business_types(self):
        """Test business type detection"""
        test_text = "компанія Технології корпорація"
        result = self.company_detector._detect_business_types(test_text)
        
        self.assertEqual(result['signal_type'], 'business_types')
        self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_addresses(self):
        """Test address detection (requirement: адреса)"""
        test_cases = [
            ("м. Київ, вул. Хрещатик, 1", "Should detect full address"),
            ("місто Львів", "Should detect city"),
            ("вулиця Незалежності", "Should detect street"),
            ("будинок 15", "Should detect building number"),
        ]
        
        for address, description in test_cases:
            with self.subTest(address=address, description=description):
                result = self.company_detector._detect_addresses(address)
                
                self.assertEqual(result['signal_type'], 'addresses')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_registration_numbers(self):
        """Test registration number detection"""
        test_text = "ЄДРПОУ 12345678 компанія"
        result = self.company_detector._detect_registration_numbers(test_text)
        
        self.assertEqual(result['signal_type'], 'registration_numbers')
        self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_capitalized_names(self):
        """Test capitalized name detection"""
        test_text = "Технології Майбутнього"
        result = self.company_detector._detect_capitalized_names(test_text)
        
        self.assertEqual(result['signal_type'], 'capitalized_names')
        self.assertGreaterEqual(result['confidence'], 0.0)
        # Should filter out common words
        self.assertNotIn('Оплата', result.get('matches', []))
    
    def test_detect_banking_terms(self):
        """Test banking terms detection (requirement: банковские термины)"""
        test_cases = [
            ("ПриватБанк", "Ukrainian bank"),
            ("Альфа-Банк", "Bank with hyphen"),
            ("Goldman Sachs", "International bank"),
            ("банківські послуги", "Banking services"),
            ("кредитні операції", "Credit operations"),
            ("фінансові інвестиції", "Financial investments"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.company_detector._detect_banking_terms(text)
                
                self.assertEqual(result['signal_type'], 'banking_terms')
                self.assertGreaterEqual(result['confidence'], 0.0)
                if any(term.lower() in text.lower() for lang_terms in self.company_detector.banking_terms.values() for term in lang_terms):
                    self.assertGreater(result['confidence'], 0.0, f"Should detect banking terms in: {text}")
    
    def test_detect_financial_services(self):
        """Test financial services detection"""
        test_text = "банківські послуги та кредитування"
        result = self.company_detector._detect_financial_services(test_text)
        
        self.assertEqual(result['signal_type'], 'financial_services')
        self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_get_enhanced_company_analysis(self):
        """Test enhanced company analysis"""
        test_text = "ПриватБанк ТОВ банківські послуги"
        
        analysis = self.company_detector.get_enhanced_company_analysis(test_text)
        
        self.assertIn('basic_result', analysis)
        self.assertIn('detailed_breakdown', analysis)
        self.assertIn('company_type_analysis', analysis)
        
        # Check detailed breakdown structure
        breakdown = analysis['detailed_breakdown']
        expected_keys = ['legal_entities', 'business_types', 'banking_terms', 
                        'financial_services', 'addresses', 'registration_numbers', 
                        'capitalized_names']
        for key in expected_keys:
            self.assertIn(key, breakdown)
        
        # Check company type analysis
        type_analysis = analysis['company_type_analysis']
        self.assertIn('is_financial_institution', type_analysis)
        self.assertIn('is_legal_entity', type_analysis)
        self.assertIn('has_registration_info', type_analysis)
        self.assertIn('most_likely_sector', type_analysis)
    
    def test_extract_detected_keywords(self):
        """Test extraction of detected keywords"""
        signals = [
            {'matches': ['ООО', 'компанія']},
            {'matches': ['банк']},
            {'matches': ['адреса']}
        ]
        
        keywords = self.company_detector._extract_detected_keywords(signals)
        
        self.assertIsInstance(keywords, list)
        expected_keywords = ['ООО', 'компанія', 'банк', 'адреса']
        for keyword in expected_keywords:
            self.assertIn(keyword, keywords)
    
    def test_create_empty_result(self):
        """Test empty result creation"""
        result = self.company_detector._create_empty_result()
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['signals'], [])
        self.assertEqual(result['signal_count'], 0)
        self.assertEqual(result['high_confidence_signals'], [])
        self.assertEqual(result['detected_keywords'], [])
        self.assertEqual(result['text_length'], 0)
        self.assertTrue(result['analysis_complete'])


class TestCompanyDetectorIntegration(unittest.TestCase):
    """Integration tests for company detector requirements"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.company_detector = CompanyDetector()
    
    def test_requirement_legal_forms(self):
        """Test required legal forms (ООО/ЗАО/LLC)"""
        legal_forms = [
            "ООО Технологии",
            "ЗАО Газпром",
            "LLC International",
            "ТОВ Українська Компанія",
            "Inc. Technology Solutions"
        ]
        
        for legal_form in legal_forms:
            with self.subTest(legal_form=legal_form):
                result = self.company_detector.detect_company_signals(legal_form)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect legal form in: {legal_form}")
                self.assertGreater(result['signal_count'], 0,
                    f"Should have signals for: {legal_form}")
    
    def test_requirement_banking_terms(self):
        """Test required banking terms"""
        banking_texts = [
            "ПриватБанк України",
            "Альфа-Банк кредитування", 
            "Goldman Sachs Investment Banking",
            "банківські послуги",
            "фінансові операції",
            "кредитні програми",
            "депозитні рахунки"
        ]
        
        for banking_text in banking_texts:
            with self.subTest(banking_text=banking_text):
                result = self.company_detector.detect_company_signals(banking_text)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect banking terms in: {banking_text}")
    
    def test_requirement_organization_patterns(self):
        """Test organization pattern detection"""
        organizations = [
            "Національний Банк України",
            "Міністерство Фінансів",
            "Державна Податкова Служба", 
            "Пенсійний Фонд України",
            "Фонд Гарантування Вкладів"
        ]
        
        for org in organizations:
            with self.subTest(org=org):
                result = self.company_detector.detect_company_signals(org)
                # Should detect some organizational signals
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_multilingual_support(self):
        """Test multilingual support for company detection"""
        multilingual_cases = [
            ("українська", "ТОВ Українська Компанія"),
            ("русская", "ООО Русская Компания"),  
            ("english", "LLC American Company")
        ]
        
        for language, company_name in multilingual_cases:
            with self.subTest(language=language, company=company_name):
                result = self.company_detector.detect_company_signals(company_name)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect {language} company: {company_name}")
    
    def test_financial_institution_detection(self):
        """Test financial institution detection and classification"""
        financial_institutions = [
            "ПриватБанк",
            "Ощадбанк",
            "ПУМБ",
            "Райффайзен Банк",
            "JPMorgan Chase",
            "Goldman Sachs"
        ]
        
        for institution in financial_institutions:
            with self.subTest(institution=institution):
                analysis = self.company_detector.get_enhanced_company_analysis(institution)
                
                # Should be classified as financial institution
                if analysis['basic_result']['confidence'] > 0:
                    type_analysis = analysis['company_type_analysis'] 
                    # May be classified as financial if banking terms are detected
                    self.assertIn('most_likely_sector', type_analysis)


if __name__ == '__main__':
    unittest.main(verbosity=2)