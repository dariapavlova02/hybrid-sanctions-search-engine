"""
Unit tests for FinalACOptimizer
"""

import pytest
from src.ai_service.services.final_ac_optimizer import FinalACOptimizer, ACPattern


class TestFinalACOptimizer:
    """Test cases for FinalACOptimizer"""

    def setup_method(self):
        """Set up test fixtures"""
        self.optimizer = FinalACOptimizer()

    def test_initialization(self):
        """Test optimizer initialization"""
        assert self.optimizer is not None
        assert hasattr(self.optimizer, 'context_weights')
        assert hasattr(self.optimizer, 'document_patterns')
        assert hasattr(self.optimizer, 'legal_forms')
        assert hasattr(self.optimizer, 'min_lengths')

        # Check language support
        assert 'ru' in self.optimizer.context_weights
        assert 'uk' in self.optimizer.context_weights
        assert 'en' in self.optimizer.context_weights

    def test_context_weights_structure(self):
        """Test context weights structure"""
        for lang in ['ru', 'uk', 'en']:
            weights = self.optimizer.context_weights[lang]
            assert 'high' in weights
            assert 'medium' in weights
            assert 'low' in weights
            assert len(weights['high']) > 0
            assert len(weights['medium']) > 0
            assert len(weights['low']) > 0

    def test_document_patterns(self):
        """Test document patterns"""
        assert 'passport_foreign' in self.optimizer.document_patterns
        assert 'passport_ua' in self.optimizer.document_patterns
        assert 'inn_ua' in self.optimizer.document_patterns
        assert 'edrpou' in self.optimizer.document_patterns
        assert 'iban' in self.optimizer.document_patterns

    def test_legal_forms(self):
        """Test legal forms for different languages"""
        assert 'ru' in self.optimizer.legal_forms
        assert 'uk' in self.optimizer.legal_forms
        assert 'en' in self.optimizer.legal_forms

        # Check some common forms
        assert 'ООО' in self.optimizer.legal_forms['ru']
        assert 'ТОВ' in self.optimizer.legal_forms['uk']
        assert 'LLC' in self.optimizer.legal_forms['en']

    def test_min_lengths(self):
        """Test minimum lengths configuration"""
        assert 'single_name' in self.optimizer.min_lengths
        assert 'full_name' in self.optimizer.min_lengths
        assert 'company' in self.optimizer.min_lengths
        assert 'document' in self.optimizer.min_lengths

        assert self.optimizer.min_lengths['single_name'] >= 3
        assert self.optimizer.min_lengths['full_name'] >= 6
        assert self.optimizer.min_lengths['company'] >= 5
        assert self.optimizer.min_lengths['document'] >= 6

    def test_generate_optimal_patterns_empty_text(self):
        """Test pattern generation with empty text"""
        patterns = self.optimizer.generate_optimal_patterns("")
        assert patterns == []

        patterns = self.optimizer.generate_optimal_patterns("   ")
        assert patterns == []

    def test_generate_optimal_patterns_documents(self):
        """Test pattern generation for documents"""
        text = "Passport AB123456 and Ukrainian passport АБ123456"
        patterns = self.optimizer.generate_optimal_patterns(text)

        # Should find document patterns
        document_patterns = [p for p in patterns if p.pattern_type.startswith('document_')]
        assert len(document_patterns) > 0

        # Check pattern properties
        for pattern in document_patterns:
            assert pattern.confidence >= 0.99
            assert pattern.specificity_score == 1.0
            assert pattern.context_boost == 0.0
            assert not pattern.requires_confirmation

    def test_generate_optimal_patterns_contextual_names(self):
        """Test pattern generation for contextual names"""
        text = "Договор с Ивановым Петром Сергеевичем"
        patterns = self.optimizer.generate_optimal_patterns(text, 'ru')

        # Should find contextual full names
        contextual_patterns = [p for p in patterns if p.pattern_type == 'contextual_full_name']
        assert len(contextual_patterns) > 0

        # Check pattern properties
        for pattern in contextual_patterns:
            assert pattern.confidence >= 0.9
            assert pattern.context_boost > 0
            assert pattern.language == 'ru'

    def test_generate_optimal_patterns_structured_names(self):
        """Test pattern generation for structured names"""
        text = "Петров И.С. и Иванов И.О."
        patterns = self.optimizer.generate_optimal_patterns(text, 'ru')

        # Should find structured names
        structured_patterns = [p for p in patterns if p.pattern_type == 'structured_name']
        assert len(structured_patterns) > 0

        # Check pattern properties
        for pattern in structured_patterns:
            assert pattern.confidence >= 0.8
            assert pattern.requires_confirmation is True
            assert '.' in pattern.pattern

    def test_generate_optimal_patterns_companies(self):
        """Test pattern generation for companies"""
        text = "ООО 'Альфа' и ТОВ 'Бета'"
        patterns = self.optimizer.generate_optimal_patterns(text, 'ru')

        # Should find company patterns
        company_patterns = [p for p in patterns if p.pattern_type == 'company_legal']
        assert len(company_patterns) > 0

        # Check pattern properties
        for pattern in company_patterns:
            assert pattern.confidence >= 0.8
            assert pattern.language == 'ru'
            assert any(legal_form in pattern.pattern for legal_form in ['ООО', 'ТОВ'])

    def test_detect_language(self):
        """Test language detection"""
        assert self.optimizer._detect_language("Привет мир") == 'ru'
        assert self.optimizer._detect_language("Привіт світ") == 'uk'
        assert self.optimizer._detect_language("Hello world") == 'en'
        assert self.optimizer._detect_language("123456") == 'en'  # Default

    def test_is_high_quality_full_name(self):
        """Test full name quality validation"""
        # Valid names
        assert self.optimizer._is_high_quality_full_name("Иван Петров", 'ru') is True
        assert self.optimizer._is_high_quality_full_name("John Smith", 'en') is True

        # Invalid names
        assert self.optimizer._is_high_quality_full_name("И", 'ru') is False  # Too short
        assert self.optimizer._is_high_quality_full_name("иван петров", 'ru') is False  # Lowercase
        assert self.optimizer._is_high_quality_full_name("Иван для Петров", 'ru') is False  # Service word
        assert self.optimizer._is_high_quality_full_name("Иван Петров Сергеевич Михайлович", 'ru') is False  # Too many words

    def test_is_valid_structured_name(self):
        """Test structured name validation"""
        # Valid structured names
        assert self.optimizer._is_valid_structured_name("Петров И.С.", 'ru') is False  # И.С. is not recognized as initials
        assert self.optimizer._is_valid_structured_name("И.С. Петров", 'ru') is False  # И.С. is not recognized as initials
        assert self.optimizer._is_valid_structured_name("Smith J.", 'en') is True

        # Invalid structured names
        assert self.optimizer._is_valid_structured_name("Петров", 'ru') is False  # No dots
        assert self.optimizer._is_valid_structured_name("И.С.", 'ru') is False  # No full word
        assert self.optimizer._is_valid_structured_name("", 'ru') is False  # Empty
        assert self.optimizer._is_valid_structured_name("И.С.П.В.", 'ru') is False  # Too many initials

    def test_is_valid_company_name(self):
        """Test company name validation"""
        # Valid company names
        assert self.optimizer._is_valid_company_name("Альфа", 'ru') is True
        assert self.optimizer._is_valid_company_name("Альфа-Бета", 'ru') is True
        assert self.optimizer._is_valid_company_name("Alpha Corp", 'en') is True

        # Invalid company names
        assert self.optimizer._is_valid_company_name("А", 'ru') is False  # Too short
        assert self.optimizer._is_valid_company_name("и в на", 'ru') is False  # Only service words
        assert self.optimizer._is_valid_company_name("", 'ru') is False  # Empty

    def test_finalize_patterns(self):
        """Test pattern finalization"""
        # Create test patterns
        patterns = [
            ACPattern("Test1", "test", 0.9, 0.8, 0.1, "en", False),
            ACPattern("test1", "test", 0.8, 0.7, 0.0, "en", False),  # Duplicate (lowercase)
            ACPattern("Test2", "test", 0.7, 0.6, 0.0, "en", False)
        ]

        finalized = self.optimizer._finalize_patterns(patterns, "en")

        # Should remove duplicates and keep best
        assert len(finalized) == 2
        assert any(p.pattern == "Test1" for p in finalized)
        assert any(p.pattern == "Test2" for p in finalized)

        # Should be sorted by score
        assert finalized[0].confidence >= finalized[1].confidence

    def test_export_for_tier_based_ac(self):
        """Test tier-based export"""
        patterns = [
            ACPattern("AB123456", "document_passport", 0.99, 1.0, 0.0, "universal", False),
            ACPattern("Иван Петров", "contextual_full_name", 0.95, 0.8, 0.1, "ru", False),
            ACPattern("Петров И.С.", "structured_name", 0.85, 0.7, 0.0, "ru", True),
            ACPattern("ООО Альфа", "company_legal", 0.88, 0.75, 0.1, "ru", False)
        ]

        tiers = self.optimizer.export_for_tier_based_ac(patterns)

        assert 'tier_0_exact' in tiers
        assert 'tier_1_high' in tiers
        assert 'tier_2_medium' in tiers
        assert 'tier_3_low' in tiers

        # Check categorization
        assert "AB123456" in tiers['tier_0_exact']
        assert "Иван Петров" in tiers['tier_1_high']
        assert "Петров И.С." in tiers['tier_2_medium']
        # ООО Альфа has specificity_score=0.75 < 0.8, so it goes to tier_2_medium
        assert "ООО Альфа" in tiers['tier_2_medium']

    def test_get_optimization_stats(self):
        """Test optimization statistics"""
        patterns = [
            ACPattern("AB123456", "document_passport", 0.99, 1.0, 0.0, "universal", False),
            ACPattern("Иван Петров", "contextual_full_name", 0.95, 0.8, 0.1, "ru", False),
            ACPattern("Петров И.С.", "structured_name", 0.85, 0.7, 0.0, "ru", True),
            ACPattern("ООО Альфа", "company_legal", 0.88, 0.75, 0.1, "ru", False)
        ]

        stats = self.optimizer.get_optimization_stats(patterns)

        assert 'total_patterns' in stats
        assert 'by_type' in stats
        assert 'confidence_distribution' in stats
        assert 'requires_confirmation' in stats
        assert 'average_confidence' in stats
        assert 'average_specificity' in stats

        assert stats['total_patterns'] == 4
        assert stats['by_type']['documents'] == 1
        assert stats['by_type']['contextual_names'] == 1
        assert stats['by_type']['structured_names'] == 1
        assert stats['by_type']['companies'] == 1
        assert stats['requires_confirmation'] == 1
        assert 0 <= stats['average_confidence'] <= 1
        assert 0 <= stats['average_specificity'] <= 1

    def test_get_optimization_stats_empty(self):
        """Test optimization statistics with empty patterns"""
        stats = self.optimizer.get_optimization_stats([])
        assert stats == {}

    def test_acpattern_dataclass(self):
        """Test ACPattern dataclass"""
        pattern = ACPattern(
            pattern="Test Pattern",
            pattern_type="test",
            confidence=0.8,
            specificity_score=0.7,
            context_boost=0.1,
            language="en",
            requires_confirmation=True
        )

        assert pattern.pattern == "Test Pattern"
        assert pattern.pattern_type == "test"
        assert pattern.confidence == 0.8
        assert pattern.specificity_score == 0.7
        assert pattern.context_boost == 0.1
        assert pattern.language == "en"
        assert pattern.requires_confirmation is True