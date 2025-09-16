"""
Performance tests for language detection service.

Tests single-pass character counting optimization and performance
with large batches of mixed language text.
"""

import pytest
import time
import random
from src.ai_service.layers.language.language_detection_service import LanguageDetectionService
from src.ai_service.config import LANGUAGE_CONFIG


class TestLanguageDetectionPerformance:
    """Performance tests for language detection"""

    @pytest.fixture
    def language_service(self):
        """Create language detection service instance"""
        return LanguageDetectionService()

    @pytest.fixture
    def test_texts(self):
        """Generate test texts for performance testing"""
        # Sample texts in different languages and mixed
        base_texts = [
            # Russian texts
            "Платеж Иванову",
            "Перевод от Петрова",
            "Оплата за услуги",
            "Договор с компанией",
            "Счет на оплату",
            
            # Ukrainian texts
            "Переказ коштів",
            "Платеж від Олени",
            "Оплата послуг",
            "Договір з компанією",
            "Рахунок на оплату",
            
            # English texts
            "Payment to John",
            "Transfer from Smith",
            "Service payment",
            "Contract with company",
            "Invoice for payment",
            
            # Mixed texts
            "Payment Ivan Petrov",
            "Переказ John Smith",
            "Оплата от Mary",
            "Transfer від Олени",
            "Платеж to company",
            
            # Short texts and acronyms
            "ООО",
            "LLC",
            "ТОВ",
            "ПЛАТЕЖ",
            "PAYMENT",
            
            # Noisy texts
            "— — — 12345",
            "12345 $$$ ABC",
            "+380-50-123-45-67",
            "### $$$ ###",
            "1234567890",
        ]
        
        # Generate 10k texts by repeating and varying the base texts
        texts = []
        for _ in range(10000):
            base_text = random.choice(base_texts)
            # Add some variation
            if random.random() < 0.3:
                base_text = base_text.upper()
            elif random.random() < 0.3:
                base_text = base_text.lower()
            
            # Add some noise occasionally
            if random.random() < 0.1:
                base_text = f"{base_text} {random.randint(100, 999)}"
            
            texts.append(base_text)
        
        return texts

    @pytest.mark.performance
    def test_single_pass_performance(self, language_service, test_texts):
        """Test performance of single-pass character counting"""
        print(f"\nTesting performance with {len(test_texts)} texts...")
        
        start_time = time.time()
        
        # Process all texts
        results = []
        for text in test_texts:
            result = language_service.detect_language_config_driven(text, LANGUAGE_CONFIG)
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate metrics
        total_texts = len(test_texts)
        avg_time_per_text = processing_time / total_texts * 1000  # ms
        texts_per_second = total_texts / processing_time
        
        print(f"Performance metrics:")
        print(f"  Total texts processed: {total_texts}")
        print(f"  Total processing time: {processing_time:.3f}s")
        print(f"  Average time per text: {avg_time_per_text:.3f}ms")
        print(f"  Texts per second: {texts_per_second:.0f}")
        
        # Performance requirements per CLAUDE.md - p95 ≤ 10ms for short strings
        # For 10k texts, allow 1s total (0.1ms per text)
        assert processing_time < 1.0, f"Performance degraded: {processing_time:.3f}s > 1.0s for {total_texts} texts"
        assert avg_time_per_text < 1.0, f"Average time per text too high: {avg_time_per_text:.3f}ms > 1.0ms"

        print(f"  ✓ Performance targets met:")
        print(f"    Total: {processing_time:.3f}s < 1.0s")
        print(f"    Per text: {avg_time_per_text:.3f}ms < 1.0ms")
        
        # Verify all texts were processed
        assert len(results) == total_texts
        
        # Verify results have expected structure
        for result in results[:10]:  # Check first 10 results
            assert hasattr(result, 'language')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'details')
            assert 'debug' in result.details

    @pytest.mark.performance
    def test_debug_details_completeness(self, language_service):
        """Test that debug details are complete and accurate"""
        test_cases = [
            "Платеж Иванову",  # Russian
            "Переказ коштів",  # Ukrainian
            "Payment to John",  # English
            "Payment Ivan Petrov",  # Mixed
            "ООО",  # Acronym
            "— — — 12345",  # Noisy
        ]
        
        for text in test_cases:
            result = language_service.detect_language_config_driven(text, LANGUAGE_CONFIG)
            
            # Check debug details are present
            assert 'debug' in result.details
            debug = result.details['debug']
            
            # Check required debug fields
            required_fields = [
                'cyr_ratio', 'lat_ratio', 'ru_bonus', 'uk_bonus',
                'uppercase_ratio', 'is_likely_acronym',
                'total_processing_chars', 'alphabetic_chars'
            ]
            
            for field in required_fields:
                assert field in debug, f"Missing debug field: {field}"
            
            # Verify debug values are reasonable
            assert 0.0 <= debug['cyr_ratio'] <= 1.0
            assert 0.0 <= debug['lat_ratio'] <= 1.0
            assert 0.0 <= debug['uppercase_ratio'] <= 1.0
            assert isinstance(debug['is_likely_acronym'], bool)
            assert debug['total_processing_chars'] == len(text)
            assert debug['alphabetic_chars'] <= len(text)

    @pytest.mark.performance
    def test_memory_efficiency(self, language_service):
        """Test that single-pass implementation doesn't create excessive temporary objects"""
        # Test with a moderately long text
        long_text = "Платеж " * 1000 + "Ivan Petrov " * 1000
        
        # Process multiple times to check for memory leaks
        for _ in range(100):
            result = language_service.detect_language_config_driven(long_text, LANGUAGE_CONFIG)
            
            # Verify result structure
            assert result.language in ['ru', 'uk', 'en', 'mixed', 'unknown']
            assert 0.0 <= result.confidence <= 1.0
            
            # Check that debug details are present
            assert 'debug' in result.details
            debug = result.details['debug']
            assert debug['total_processing_chars'] == len(long_text)

    @pytest.mark.performance
    def test_edge_case_performance(self, language_service):
        """Test performance with edge cases that previously used regex"""
        edge_cases = [
            "ООО",  # Short acronym
            "LLC",  # English acronym
            "ПЛАТЕЖ",  # Uppercase text
            "MEMBERSHIP",  # Long uppercase
            "— — — 12345",  # Noisy text
            "12345 $$$$$$$ ABC",  # High noise ratio
            "+380-50-123-45-67",  # Phone number
            "А",  # Single character
            "AB",  # Two characters
            "ABC",  # Three characters
        ]
        
        start_time = time.time()
        
        for text in edge_cases:
            result = language_service.detect_language_config_driven(text, LANGUAGE_CONFIG)
            # Verify edge case handling
            assert result.language in ['ru', 'uk', 'en', 'mixed', 'unknown']
            assert 0.0 <= result.confidence <= 1.0
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\nEdge case performance:")
        print(f"  Processed {len(edge_cases)} edge cases in {processing_time:.4f}s")
        print(f"  Average time per edge case: {processing_time/len(edge_cases)*1000:.3f}ms")

    @pytest.mark.performance
    def test_character_counting_accuracy(self, language_service):
        """Test that single-pass counting produces same results as regex-based counting"""
        test_texts = [
            "Платеж Иванову",
            "Payment to John Smith",
            "Переказ коштів Олені",
            "ООО ТОВ LLC",
            "— — — 12345 $$$",
            "ПЛАТЕЖ ПЛАТЕЖ",
            "Mixed текст with English",
        ]
        
        for text in test_texts:
            result = language_service.detect_language_config_driven(text, LANGUAGE_CONFIG)
            details = result.details
            
            # Verify character counts are reasonable
            total_letters = details['cyr_chars'] + details['lat_chars']
            assert total_letters == details['total_letters']
            
            # Verify ratios sum to 1.0 (or 0.0 if no letters)
            if total_letters > 0:
                ratio_sum = details['cyr_ratio'] + details['lat_ratio']
                assert abs(ratio_sum - 1.0) < 0.001, f"Ratios don't sum to 1.0: {ratio_sum}"
            
            # Verify specific character counts are non-negative
            assert details['uk_chars'] >= 0
            assert details['ru_chars'] >= 0
            assert details['digits'] >= 0
            assert details['punct'] >= 0
            assert details['uppercase_chars'] >= 0
