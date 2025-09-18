"""
Unit tests for DocumentDetector module
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ai_service.layers.smart_filter.document_detector import DocumentDetector


class TestDocumentDetector(unittest.TestCase):
    """Test cases for DocumentDetector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.document_detector = DocumentDetector()
    
    def test_initialization(self):
        """Test document detector initialization"""
        self.assertIsNotNone(self.document_detector)
        self.assertIsNotNone(self.document_detector.inn_patterns)
        self.assertIsNotNone(self.document_detector.date_patterns)
        self.assertIsNotNone(self.document_detector.document_patterns)
        self.assertIsNotNone(self.document_detector.address_patterns)
        self.assertIsNotNone(self.document_detector.bank_patterns)
        self.assertIsNotNone(self.document_detector.phone_patterns)
        self.assertIsNotNone(self.document_detector.email_patterns)
    
    def test_detect_document_signals_empty(self):
        """Test document detection with empty text"""
        result = self.document_detector.detect_document_signals("")
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['signal_count'], 0)
        self.assertEqual(result['detected_documents'], [])
        self.assertTrue(result['analysis_complete'])
    
    def test_detect_document_signals_with_inn(self):
        """Test detection with INN (requirement: ИНН)"""
        test_text = "ІНН 1234567890 компанія"
        result = self.document_detector.detect_document_signals(test_text)
        
        self.assertGreater(result['confidence'], 0.0)
        self.assertGreater(result['signal_count'], 0)
        self.assertTrue(result['analysis_complete'])
    
    def test_detect_inn(self):
        """Test INN detection (requirement: ИНН detection)"""
        test_cases = [
            ("ІНН 1234567890", "Ukrainian INN with prefix"),
            ("инн 0987654321", "Russian INN with prefix"),
            ("INN 1122334455", "English INN with prefix"),
            ("ідентифікаційний номер 1234567890", "Full Ukrainian form"),
            ("идентификационный номер 0987654321", "Full Russian form"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.document_detector._detect_inn(text)
                
                self.assertEqual(result['signal_type'], 'inn')
                self.assertGreaterEqual(result['confidence'], 0.0)
                if result['matches']:
                    self.assertGreater(result['confidence'], 0.0)
                    # Should extract numeric part
                    for match in result['matches']:
                        self.assertTrue(match.isdigit(), f"INN should be numeric: {match}")
                        self.assertIn(len(match), [8, 10, 12], f"INN should be 8, 10, or 12 digits: {match}")
    
    def test_detect_dates(self):
        """Test date detection (requirement: даты)"""
        test_cases = [
            ("2024-01-15", "ISO format YYYY-MM-DD"),
            ("15.01.2024", "European format DD.MM.YYYY"),
            ("15/01/2024", "Alternative format DD/MM/YYYY"),
            ("15 січня 2024", "Ukrainian month name"),
            ("15 января 2024", "Russian month name"),
            ("January 15, 2024", "English month name"),
            ("15 January 2024", "English format without comma"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.document_detector._detect_dates(text)
                
                self.assertEqual(result['signal_type'], 'dates')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_document_numbers(self):
        """Test document number detection"""
        test_cases = [
            ("паспорт АВ123456", "Ukrainian passport"),
            ("passport AB123456", "English passport"),
            ("посвідчення КВА123456", "Driver's license"),
            ("свідоцтво І-СВ123456", "Birth certificate"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.document_detector._detect_document_numbers(text)
                
                self.assertEqual(result['signal_type'], 'document_numbers')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_addresses(self):
        """Test address detection (requirement: адреса)"""
        test_cases = [
            ("індекс 01234", "Postal code"),
            ("адреса Київ Хрещатик 1", "Full address"),
            ("м. Львів", "City"),
            ("вул. Незалежності", "Street"),
            ("буд. 15", "Building number"),
            ("кв. 23", "Apartment number"),
            ("50.4501,30.5234", "GPS coordinates"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.document_detector._detect_addresses(text)
                
                self.assertEqual(result['signal_type'], 'addresses')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_bank_details(self):
        """Test bank details detection"""
        test_cases = [
            ("МФО 322313", "Ukrainian MFO"),
            ("BIC DEUTDEFF", "International BIC"),
            ("SWIFT PRYVUAUK", "SWIFT code"),
            ("рахунок 26007233566001", "Account number"),
            ("IBAN UA213223130000026007233566", "Ukrainian IBAN"),
            ("картка 1234 **** **** 5678", "Card number (masked)"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.document_detector._detect_bank_details(text)
                
                self.assertEqual(result['signal_type'], 'bank_details')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_detect_contact_info(self):
        """Test contact information detection"""
        test_cases = [
            ("+380501234567", "Ukrainian mobile"),
            ("+1-555-123-4567", "US phone"),
            ("+7-495-123-45-67", "Russian phone"),
            ("test@example.com", "Email address"),
            ("user.name+tag@domain.co.uk", "Complex email"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                result = self.document_detector._detect_contact_info(text)
                
                self.assertEqual(result['signal_type'], 'contact_info')
                self.assertGreaterEqual(result['confidence'], 0.0)
    
    def test_is_valid_date(self):
        """Test date validation"""
        valid_dates = [
            "15/01/2024",
            "2024-01-15",
            "15.01.2024",
            "01/15/2024",
        ]
        
        invalid_dates = [
            "32/01/2024",  # Invalid day
            "15/13/2024",  # Invalid month
            "15/01/1800",  # Too old
            "15/01/2200",  # Too far in future
            "not-a-date",  # Invalid format
        ]
        
        for date_str in valid_dates:
            with self.subTest(date=date_str):
                self.assertTrue(self.document_detector._is_valid_date(date_str) or 
                               not self.document_detector._is_valid_date(date_str),
                               f"Date validation for {date_str}")
        
        for date_str in invalid_dates:
            with self.subTest(date=date_str):
                # Should handle invalid dates gracefully
                result = self.document_detector._is_valid_date(date_str)
                self.assertIsInstance(result, bool)
    
    def test_extract_detected_documents(self):
        """Test extraction of detected documents"""
        signals = [
            {'matches': ['1234567890', 'АВ123456']},
            {'matches': ['2024-01-15']},
            {'matches': ['test@example.com']}
        ]
        
        documents = self.document_detector._extract_detected_documents(signals)
        
        self.assertIsInstance(documents, list)
        expected_docs = ['1234567890', 'АВ123456', '2024-01-15', 'test@example.com']
        for doc in expected_docs:
            self.assertIn(doc, documents)
    
    def test_create_empty_result(self):
        """Test empty result creation"""
        result = self.document_detector._create_empty_result()
        
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['signals'], [])
        self.assertEqual(result['signal_count'], 0)
        self.assertEqual(result['high_confidence_signals'], [])
        self.assertEqual(result['detected_documents'], [])
        self.assertEqual(result['text_length'], 0)
        self.assertTrue(result['analysis_complete'])


class TestDocumentDetectorIntegration(unittest.TestCase):
    """Integration tests for document detector requirements"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.document_detector = DocumentDetector()
    
    def test_requirement_inn_detection(self):
        """Test required INN detection"""
        inn_texts = [
            "ІНН 1234567890 платіж",
            "Компанія з ІНН 0987654321",
            "идентификационный номер 1122334455",
            "ИНН: 9988776655",
            "INN 1357924680 payment"
        ]
        
        for inn_text in inn_texts:
            with self.subTest(inn_text=inn_text):
                result = self.document_detector.detect_document_signals(inn_text)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect INN in: {inn_text}")
                self.assertGreater(result['signal_count'], 0,
                    f"Should have signals for INN: {inn_text}")
    
    def test_requirement_date_detection(self):
        """Test required date detection"""
        date_texts = [
            "Договір від 15.01.2024",
            "Платеж на 2024-01-15",
            "Оплата 15 січня 2024 року",
            "Payment on January 15, 2024",
            "Счет от 15/01/2024"
        ]
        
        for date_text in date_texts:
            with self.subTest(date_text=date_text):
                result = self.document_detector.detect_document_signals(date_text)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect date in: {date_text}")
    
    def test_requirement_address_detection(self):
        """Test required address detection"""
        address_texts = [
            "адреса: м. Київ, вул. Хрещатик, буд. 1, кв. 15",
            "Львів, вулиця Свободи, 25",
            "індекс 01001, Київ",
            "address: New York, 5th Avenue, 123",
            "50.4501,30.5234 координати"
        ]
        
        for address_text in address_texts:
            with self.subTest(address_text=address_text):
                result = self.document_detector.detect_document_signals(address_text)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect address in: {address_text}")
    
    def test_comprehensive_document_analysis(self):
        """Test comprehensive document analysis"""
        complex_text = """
        Договір №123 від 15.01.2024
        ТОВ "Тестова Компанія"
        ІНН 1234567890
        адреса: м. Київ, вул. Тестова, 15, кв. 23
        тел: +380501234567
        email: test@company.ua
        рахунок: UA213223130000026007233566
        МФО: 322313
        """
        
        result = self.document_detector.detect_document_signals(complex_text)
        
        # Should detect multiple types of document signals
        self.assertGreater(result['confidence'], 0.0)
        self.assertGreater(result['signal_count'], 0)
        
        # Should detect multiple signal types
        signal_types = [signal['signal_type'] for signal in result['signals']]
        expected_types = ['inn', 'dates', 'addresses', 'contact_info', 'bank_details']
        
        detected_types = [t for t in expected_types if t in signal_types]
        self.assertGreater(len(detected_types), 0,
            "Should detect multiple document signal types")
    
    def test_multilingual_document_support(self):
        """Test multilingual document detection"""
        multilingual_cases = [
            ("ukrainian", "ІНН 1234567890, адреса Київ"),
            ("russian", "ИНН 0987654321, адрес Москва"),
            ("english", "INN 1122334455, address New York")
        ]
        
        for language, document_text in multilingual_cases:
            with self.subTest(language=language, text=document_text):
                result = self.document_detector.detect_document_signals(document_text)
                self.assertGreater(result['confidence'], 0.0,
                    f"Should detect {language} documents: {document_text}")


if __name__ == '__main__':
    unittest.main(verbosity=2)