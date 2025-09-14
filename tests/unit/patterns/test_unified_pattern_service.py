"""
Unit tests for UnifiedPatternService
"""

import pytest
from unittest.mock import Mock, patch

from ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService, UnifiedPattern


class TestUnifiedPatternService:
    """Tests for UnifiedPatternService"""

    @pytest.fixture
    def pattern_service(self):
        """Create UnifiedPatternService instance"""
        return UnifiedPatternService()

    def test_unified_pattern_creation(self, pattern_service):
        """Test UnifiedPattern creation"""
        pattern = UnifiedPattern(
            pattern="John Doe",
            pattern_type="full_name",
            language="en",
            confidence=0.95,
            source="test"
        )

        assert pattern.pattern == "John Doe"
        assert pattern.pattern_type == "full_name"
        assert pattern.confidence == 0.95
        assert pattern.source == "test"
        assert pattern.context_required is False
        assert pattern.boost_score == 1.0
        assert pattern.min_match_length == 8  # len("John Doe")

    def test_generate_patterns_basic(self, pattern_service):
        """Test basic pattern generation"""
        patterns = pattern_service.generate_patterns("John Doe", "en")

        assert isinstance(patterns, list)
        assert len(patterns) > 0

        for pattern in patterns:
            assert isinstance(pattern, UnifiedPattern)
            assert isinstance(pattern.pattern, str)
            assert len(pattern.pattern) > 0
            assert isinstance(pattern.confidence, (int, float))
            assert 0.0 <= pattern.confidence <= 1.0

    def test_generate_patterns_empty_text(self, pattern_service):
        """Test pattern generation for empty text"""
        patterns = pattern_service.generate_patterns("", "en")

        assert isinstance(patterns, list)
        assert len(patterns) == 0

    def test_document_pattern_extraction(self, pattern_service):
        """Test document pattern extraction"""
        text = "Паспорт АА123456 та ІПН 1234567890"
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should find document patterns
        doc_patterns = [p for p in patterns if p.pattern_type.startswith("document_")]
        assert len(doc_patterns) >= 1

        # Should have high confidence
        for pattern in doc_patterns:
            assert pattern.confidence >= 0.9
            assert pattern.boost_score >= 1.5

    def test_contextual_pattern_extraction(self, pattern_service):
        """Test contextual pattern extraction"""
        text = "Платіж від Іван Петренко для послуг"
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should find contextual patterns
        contextual_patterns = [p for p in patterns if p.pattern_type in ["contextual_full_name", "payment_context"]]
        assert len(contextual_patterns) >= 1

        # Check that we have the expected name
        name_patterns = [p for p in contextual_patterns if "іван" in p.pattern.lower() or "петренко" in p.pattern.lower()]
        assert len(name_patterns) >= 1

    def test_structured_name_extraction(self, pattern_service):
        """Test structured name extraction"""
        text = "Відправник: Петренко І. В."
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should find structured patterns
        structured_patterns = [p for p in patterns if p.pattern_type == "structured_name"]
        assert len(structured_patterns) >= 1

        # Check pattern properties
        for pattern in structured_patterns:
            assert "." in pattern.pattern  # Should contain initials
            assert pattern.context_required is True

    def test_company_pattern_extraction(self, pattern_service):
        """Test company pattern extraction"""
        text = 'Контракт з ТОВ "Компанія Тест" на послуги'
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should find company patterns
        company_patterns = [p for p in patterns if p.pattern_type == "company_legal"]
        assert len(company_patterns) >= 1

        # Check that pattern includes legal form
        for pattern in company_patterns:
            assert "тов" in pattern.pattern.lower() or "компанія" in pattern.pattern.lower()

    def test_dob_pattern_extraction(self, pattern_service):
        """Test DOB-enhanced pattern extraction"""
        text = "Народився Олександр Сидоров 15.03.1985"
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should find patterns near DOB
        dob_patterns = [p for p in patterns if "dob_nearby" in p.metadata]
        assert len(dob_patterns) >= 1

        # Check high confidence due to DOB proximity
        for pattern in dob_patterns:
            assert pattern.boost_score >= 1.5
            assert pattern.confidence >= 0.85

    def test_dictionary_pattern_extraction(self, pattern_service):
        """Test dictionary-based pattern extraction"""
        text = "Клієнт Іван відвідав офіс"
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should find dictionary patterns
        dict_patterns = [p for p in patterns if p.pattern_type in ["dictionary_name", "dictionary_surname"]]
        assert len(dict_patterns) >= 1

        # Check that "Іван" is found
        ivan_patterns = [p for p in dict_patterns if p.pattern.lower() == "іван"]
        assert len(ivan_patterns) >= 1

    def test_language_detection(self, pattern_service):
        """Test language detection"""
        # Test Cyrillic (Ukrainian)
        assert pattern_service._detect_language("Іван Петренко") == "uk"

        # Test Cyrillic (Russian)
        assert pattern_service._detect_language("Иван Петров") == "ru"

        # Test Latin
        assert pattern_service._detect_language("John Smith") == "en"

        # Test mixed (should default to primary)
        assert pattern_service._detect_language("Іван Smith") == "uk"

    def test_pattern_optimization(self, pattern_service):
        """Test pattern optimization and deduplication"""
        # Create duplicate patterns
        patterns = [
            UnifiedPattern(pattern="John", pattern_type="name", language="en", confidence=0.8),
            UnifiedPattern(pattern="john", pattern_type="name", language="en", confidence=0.9),  # Same but different case
            UnifiedPattern(pattern="John", pattern_type="name", language="en", confidence=0.7),  # Exact duplicate
        ]

        optimized = pattern_service._optimize_patterns(patterns)

        # Should remove duplicates and keep highest confidence
        john_patterns = [p for p in optimized if p.pattern.lower() == "john"]
        assert len(john_patterns) == 1
        assert john_patterns[0].confidence == 0.9

    def test_stop_words_filtering(self, pattern_service):
        """Test stop words filtering"""
        text = "для або його цей один"  # All stop words in Ukrainian
        patterns = pattern_service.generate_patterns(text, "uk")

        # Should not generate patterns for stop words
        stop_word_patterns = [p for p in patterns if p.pattern.lower() in ["для", "або", "його", "цей", "один"]]
        assert len(stop_word_patterns) == 0

    def test_multilingual_support(self, pattern_service):
        """Test multilingual pattern generation"""
        test_cases = [
            ("John Smith", "en"),
            ("Jean Dupont", "fr"),
            ("María García", "es"),
            ("Сергей Иванов", "ru"),
            ("Сергій Іванов", "uk"),
        ]

        for name, language in test_cases:
            patterns = pattern_service.generate_patterns(name, language)
            assert isinstance(patterns, list)

            if len(patterns) > 0:
                # Check that patterns have correct language
                lang_patterns = [p for p in patterns if p.language == language]
                assert len(lang_patterns) > 0

    def test_export_for_aho_corasick(self, pattern_service):
        """Test Aho-Corasick export functionality"""
        patterns = [
            UnifiedPattern(pattern="AA123456", pattern_type="document_passport", boost_score=2.0, confidence=0.98),
            UnifiedPattern(pattern="John Doe", pattern_type="contextual_full_name", boost_score=1.8, confidence=0.92),
            UnifiedPattern(pattern="Smith J. D.", pattern_type="structured_name", boost_score=1.5, confidence=0.85),
            UnifiedPattern(pattern="Test", pattern_type="basic_name", boost_score=1.0, confidence=0.7),
        ]

        result = pattern_service.export_for_aho_corasick(patterns)

        # Check tier structure
        assert "tier_0_exact" in result
        assert "tier_1_high_confidence" in result
        assert "tier_2_medium_confidence" in result
        assert "tier_3_low_confidence" in result

        # Check pattern distribution
        assert "AA123456" in result["tier_0_exact"]
        assert "John Doe" in result["tier_1_high_confidence"]
        assert "Smith J. D." in result["tier_2_medium_confidence"]
        assert "Test" in result["tier_3_low_confidence"]

    def test_pattern_statistics(self, pattern_service):
        """Test pattern statistics generation"""
        patterns = [
            UnifiedPattern(pattern="John", pattern_type="name", language="en", confidence=0.9, source="basic"),
            UnifiedPattern(pattern="Smith", pattern_type="surname", language="en", confidence=0.8, source="dict"),
            UnifiedPattern(pattern="AA123456", pattern_type="document", language="universal", confidence=0.98, source="doc"),
        ]

        stats = pattern_service.get_pattern_statistics(patterns)

        # Check statistics structure
        assert stats["total_patterns"] == 3
        assert "by_type" in stats
        assert "by_language" in stats
        assert "by_source" in stats
        assert "by_confidence" in stats

        # Check specific counts
        assert stats["by_language"]["en"] == 2
        assert stats["by_language"]["universal"] == 1
        assert stats["by_confidence"]["high"] >= 1  # The document pattern

        # Check averages
        assert 0.0 < stats["average_confidence"] <= 1.0
        assert stats["average_boost"] >= 1.0

    def test_high_quality_name_validation(self, pattern_service):
        """Test high quality name validation"""
        # Valid names
        assert pattern_service._is_high_quality_name("John Smith", "en")
        assert pattern_service._is_high_quality_name("Іван Петренко", "uk")
        assert pattern_service._is_high_quality_name("María José García", "es")

        # Invalid names
        assert not pattern_service._is_high_quality_name("john", "en")  # Too short
        assert not pattern_service._is_high_quality_name("JOHN SMITH", "en")  # All caps
        assert not pattern_service._is_high_quality_name("для або", "uk")  # Stop words
        assert not pattern_service._is_high_quality_name("", "en")  # Empty

    def test_structured_name_validation(self, pattern_service):
        """Test structured name validation"""
        # Valid structured names
        assert pattern_service._is_valid_structured_name("Smith J. D.", "en")
        assert pattern_service._is_valid_structured_name("Петренко І. В.", "uk")
        assert pattern_service._is_valid_structured_name("J. D. Smith", "en")

        # Invalid structured names
        assert not pattern_service._is_valid_structured_name("John Smith", "en")  # No initials
        assert not pattern_service._is_valid_structured_name("J. D. K. Smith", "en")  # Too many initials
        assert not pattern_service._is_valid_structured_name("Smith", "en")  # No initials

    def test_company_name_validation(self, pattern_service):
        """Test company name validation"""
        # Valid company names
        assert pattern_service._is_valid_company_name("Test Company", "en")
        assert pattern_service._is_valid_company_name('"Компанія Тест"', "uk")
        assert pattern_service._is_valid_company_name("ABC Corp", "en")

        # Invalid company names
        assert not pattern_service._is_valid_company_name("для", "uk")  # Stop word
        assert not pattern_service._is_valid_company_name("AB", "en")  # Too short
        assert not pattern_service._is_valid_company_name("", "en")  # Empty

    def test_performance_with_complex_text(self, pattern_service):
        """Test performance with complex, realistic text"""
        complex_text = """
        Договір № 123 від 15.03.2024
        Замовник: ТОВ "Тестова Компанія"
        ЄДРПОУ 12345678, ІПН 1234567890
        Представник: Петренко Іван Володимирович
        Дата народження: 15.03.1985
        Паспорт: АА123456
        Адреса: м. Київ, вул. Тестова, 123

        Виконавець: ФОП Сидоров Олександр Петрович
        ІПН 9876543210, паспорт ВВ654321

        Предмет договору: надання консультаційних послуг
        Вартість: 10000 грн
        Термін: до 31.12.2024

        Підписи:
        Замовник: Петренко І. В. _______
        Виконавець: Сидоров О. П. _______
        """

        import time
        start_time = time.time()
        patterns = pattern_service.generate_patterns(complex_text, "uk")
        end_time = time.time()

        processing_time = end_time - start_time

        # Should process complex text reasonably quickly
        assert processing_time < 5.0, f"Processing took too long: {processing_time:.3f}s"

        # Should find multiple types of patterns
        assert len(patterns) >= 10

        # Should find different pattern types
        pattern_types = set(p.pattern_type for p in patterns)
        assert len(pattern_types) >= 3

        # Should find high-confidence patterns
        high_conf_patterns = [p for p in patterns if p.confidence >= 0.9]
        assert len(high_conf_patterns) >= 2

    def test_legacy_compatibility(self, pattern_service):
        """Test legacy method compatibility"""
        # Test legacy method exists and works
        patterns = pattern_service.generate_high_precision_patterns("John Smith", "en")
        assert isinstance(patterns, list)
        assert len(patterns) > 0

        # Test deduplication compatibility
        test_patterns = [
            UnifiedPattern(pattern="John", pattern_type="name", language="en", confidence=0.8),
            UnifiedPattern(pattern="john", pattern_type="name", language="en", confidence=0.9),
        ]

        deduplicated = pattern_service._remove_duplicate_patterns(test_patterns)
        assert len(deduplicated) == 1
        assert deduplicated[0].confidence == 0.9

    def test_case_sensitivity_handling(self, pattern_service):
        """Test case sensitivity handling"""
        # Use proper case name for testing
        patterns = pattern_service.generate_patterns("John Smith", "en")

        # Should generate patterns in different cases
        pattern_texts = [p.pattern for p in patterns]

        # Should have at least the original pattern
        assert len(pattern_texts) > 0

        # Test that all-caps names are rejected by quality filter
        all_caps_patterns = pattern_service.generate_patterns("JOHN SMITH", "en")
        # All-caps should be filtered out in high-quality name validation
        assert len([p for p in all_caps_patterns if p.pattern == "JOHN SMITH"]) == 0

    def test_special_characters_handling(self, pattern_service):
        """Test special characters in names"""
        test_names = [
            ("O'Connor", "en"),
            ("Jean-Baptiste", "fr"),
            ("José María", "es"),
            ("Д'Артаньян", "uk"),
        ]

        for name, language in test_names:
            patterns = pattern_service.generate_patterns(name, language)
            assert len(patterns) > 0, f"Should generate patterns for {name}"

            # Should handle special characters gracefully
            for pattern in patterns:
                assert isinstance(pattern.pattern, str)
                assert len(pattern.pattern) > 0