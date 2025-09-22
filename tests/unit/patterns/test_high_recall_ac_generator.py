#!/usr/bin/env python3
"""
Comprehensive test suite for High-Recall AC Pattern Generator

Tests all tiers, canonicalization, and production-ready functionality.
"""

import pytest
import json
from unittest.mock import patch, mock_open

from ai_service.layers.patterns.high_recall_ac_generator import (
    HighRecallACGenerator,
    PatternTier,
    PatternType,
    LanguageDetector,
    TextCanonicalizer,
    DocumentPatternGenerator,
    NamePatternGenerator,
    CompanyPatternGenerator,
)


class TestLanguageDetector:
    """Test language detection functionality"""

    def test_detect_script_cyrillic(self):
        assert LanguageDetector.detect_script("Иван Петров") == "cyrillic"
        assert LanguageDetector.detect_script("Іван Петро") == "cyrillic"

    def test_detect_script_latin(self):
        assert LanguageDetector.detect_script("John Smith") == "latin"
        assert LanguageDetector.detect_script("Roman Kovrykov") == "latin"

    def test_detect_script_mixed(self):
        assert LanguageDetector.detect_script("Иван Smith") == "mixed"
        assert LanguageDetector.detect_script("John Петров") == "mixed"

    def test_detect_language_russian(self):
        assert LanguageDetector.detect_language("Иван Петров") == "ru"

    def test_detect_language_ukrainian(self):
        assert LanguageDetector.detect_language("Іван Петрович") == "uk"
        assert LanguageDetector.detect_language("Ковальський") == "uk"

    def test_detect_language_english(self):
        assert LanguageDetector.detect_language("John Smith") == "en"

    def test_detect_language_mixed(self):
        assert LanguageDetector.detect_language("Иван Smith") == "mixed"


class TestTextCanonicalizer:
    """Test text canonicalization functionality"""

    def test_basic_normalization(self):
        assert TextCanonicalizer.normalize_for_ac("  John   Smith  ") == "John Smith"
        assert TextCanonicalizer.normalize_for_ac("JOHN SMITH") == "JOHN SMITH"

    def test_apostrophe_normalization(self):
        assert TextCanonicalizer.normalize_for_ac("O'Connor") == "O'Connor"
        assert TextCanonicalizer.normalize_for_ac("O'Connor") == "O'Connor"

    def test_hyphen_normalization(self):
        assert TextCanonicalizer.normalize_for_ac("Jean-Pierre") == "Jean-Pierre"
        assert TextCanonicalizer.normalize_for_ac("Jean–Pierre") == "Jean-Pierre"

    def test_deglyph_mapping(self):
        result = TextCanonicalizer.normalize_for_ac("Иван")
        # Should contain some deglyphed characters
        assert len(result) > 0

    def test_casefold_by_language(self):
        assert TextCanonicalizer.casefold_by_language("JOHN", "en") == "john"
        assert TextCanonicalizer.casefold_by_language("ИВАН", "ru") == "иван"


class TestDocumentPatternGenerator:
    """Test document pattern generation"""

    def setUp(self):
        self.generator = DocumentPatternGenerator()

    def test_generate_itn_patterns_valid(self):
        patterns = DocumentPatternGenerator().generate_itn_patterns("1234567890")
        assert len(patterns) == 1
        assert patterns[0].pattern == "1234567890"
        assert patterns[0].metadata.tier == PatternTier.TIER_0
        assert patterns[0].metadata.pattern_type == PatternType.TAX_NUMBER

    def test_generate_itn_patterns_invalid(self):
        patterns = DocumentPatternGenerator().generate_itn_patterns("123")  # Too short
        assert len(patterns) == 0

        patterns = DocumentPatternGenerator().generate_itn_patterns("abc123")  # Non-numeric
        assert len(patterns) == 0

    def test_generate_passport_patterns(self):
        patterns = DocumentPatternGenerator().generate_passport_patterns("AB123456")
        assert len(patterns) == 4  # Multiple variants

        pattern_strs = [p.pattern for p in patterns]
        assert "AB123456" in pattern_strs
        assert "AB-123456" in pattern_strs
        assert "AB 123456" in pattern_strs
        assert "ab123456" in pattern_strs

    def test_generate_iban_patterns(self):
        patterns = DocumentPatternGenerator().generate_iban_patterns("UA211234567890123456789012345")
        assert len(patterns) == 2  # Solid and spaced

        pattern_strs = [p.pattern for p in patterns]
        assert "UA211234567890123456789012345" in pattern_strs


class TestNamePatternGenerator:
    """Test name pattern generation across all tiers"""

    def setUp(self):
        self.generator = NamePatternGenerator()

    def test_is_full_name(self):
        assert self.generator.is_full_name("John Smith") == True
        assert self.generator.is_full_name("John") == False
        assert self.generator.is_full_name("John Middle Smith") == True

    def test_tier_0_patterns(self):
        patterns = NamePatternGenerator().generate_tier_0_patterns("John Smith", "en")
        assert len(patterns) == 1
        assert patterns[0].metadata.tier == PatternTier.TIER_0
        assert patterns[0].metadata.pattern_type == PatternType.FULL_NAME_CANON

    def test_tier_0_rejects_single_names(self):
        patterns = NamePatternGenerator().generate_tier_0_patterns("John", "en")
        assert len(patterns) == 0

    def test_tier_1_nickname_expansion(self):
        generator = NamePatternGenerator()
        # Mock nickname expansion
        generator.nicknames["en"]["William"] = ["Bill", "Will"]

        patterns = generator.generate_tier_1_patterns("Bill Gates", "en")
        # Should generate William Gates variant
        bill_to_william = [p for p in patterns if "William" in p.pattern]
        assert len(bill_to_william) > 0

    def test_tier_1_apostrophe_variants(self):
        patterns = NamePatternGenerator().generate_tier_1_patterns("O'Connor Smith", "en")
        apostrophe_variants = [p for p in patterns if p.metadata.pattern_type == PatternType.APOSTROPHE_VARIANT]
        assert len(apostrophe_variants) > 0

    def test_tier_2_initial_variants(self):
        patterns = NamePatternGenerator().generate_tier_2_patterns("John Michael Smith", "en")
        initial_patterns = [p for p in patterns if p.metadata.pattern_type == PatternType.INITIALS_VARIANT]
        assert len(initial_patterns) > 0

        # Should have variants like "John M. Smith", "J. M. Smith", etc.
        pattern_strs = [p.pattern for p in initial_patterns]
        assert any("J." in p for p in pattern_strs)

    def test_tier_2_hyphen_variants(self):
        patterns = NamePatternGenerator().generate_tier_2_patterns("Jean Pierre Smith", "en")
        hyphen_patterns = [p for p in patterns if p.metadata.pattern_type == PatternType.HYPHEN_VARIANT]
        assert len(hyphen_patterns) > 0

    def test_tier_3_aggressive_patterns(self):
        patterns = NamePatternGenerator().generate_tier_3_patterns("John Michael Smith", "en")
        aggressive_patterns = [p for p in patterns if p.metadata.tier == PatternTier.TIER_3]
        assert len(aggressive_patterns) > 0

        # Should have context requirements
        assert all(p.metadata.requires_context for p in aggressive_patterns)

    def test_tier_3_surname_only(self):
        patterns = NamePatternGenerator().generate_tier_3_patterns("John Smith", "en")
        surname_patterns = [p for p in patterns if p.metadata.pattern_type == PatternType.SURNAME_ONLY]
        assert len(surname_patterns) > 0
        assert surname_patterns[0].pattern == "Smith"


class TestCompanyPatternGenerator:
    """Test company pattern generation"""

    def test_tier_0_canonical_companies(self):
        patterns = CompanyPatternGenerator().generate_tier_0_patterns('ООО "РОМАШКА"', "ru")
        assert len(patterns) > 0
        assert patterns[0].metadata.tier == PatternTier.TIER_0

    def test_tier_1_quote_variants(self):
        patterns = CompanyPatternGenerator().generate_tier_1_patterns('ООО "РОМАШКА"', "ru")
        quote_patterns = [p for p in patterns if p.metadata.pattern_type == PatternType.COMPANY_FORM_VARIANT]
        # Should generate different quote styles
        assert len(quote_patterns) > 0

    def test_tier_2_no_form_variants(self):
        patterns = CompanyPatternGenerator().generate_tier_2_patterns('ООО "РОМАШКА"', "ru")
        no_form_patterns = [p for p in patterns if p.metadata.pattern_type == PatternType.COMPANY_NO_FORM]
        assert len(no_form_patterns) > 0
        # Should extract quoted name without legal form
        assert any('"РОМАШКА"' in p.pattern for p in no_form_patterns)

    def test_tier_3_aggressive_company_patterns(self):
        patterns = CompanyPatternGenerator().generate_tier_3_patterns("РОМАШКА РИТЕЙЛ ГРУП", "ru")
        aggressive_patterns = [p for p in patterns if p.metadata.tier == PatternTier.TIER_3]
        assert len(aggressive_patterns) > 0


class TestHighRecallACGenerator:
    """Test main generator functionality"""

    def test_initialization(self):
        generator = HighRecallACGenerator()
        assert generator.language_detector is not None
        assert generator.document_generator is not None
        assert generator.name_generator is not None
        assert generator.company_generator is not None

    def test_tier_limits(self):
        generator = HighRecallACGenerator()
        assert generator.tier_limits[PatternTier.TIER_0] == 3
        assert generator.tier_limits[PatternTier.TIER_1] == 8
        assert generator.tier_limits[PatternTier.TIER_2] == 12
        assert generator.tier_limits[PatternTier.TIER_3] == 200

    def test_generate_patterns_for_person(self):
        generator = HighRecallACGenerator()

        person_data = {
            "id": 1,
            "name": "John Smith",
            "name_en": "John Smith",
            "itn": "1234567890",
            "birthdate": "1980-01-01"
        }

        patterns = generator.generate_patterns_for_person(person_data)
        assert len(patterns) > 0

        # Should have patterns from multiple tiers
        tiers = set(p.metadata.tier for p in patterns)
        assert PatternTier.TIER_0 in tiers  # ITN and canonical names

        # All patterns should have entity_id set
        assert all(p.entity_id == "1" for p in patterns)

    def test_generate_patterns_for_company(self):
        generator = HighRecallACGenerator()

        company_data = {
            "id": 2,
            "name": 'LLC "TESTCORP"',
            "tax_number": "9876543210"
        }

        patterns = generator.generate_patterns_for_company(company_data)
        assert len(patterns) > 0

        # Should have company-specific patterns
        company_patterns = [p for p in patterns if p.entity_type == "company"]
        assert len(company_patterns) > 0

    def test_export_for_ac(self):
        generator = HighRecallACGenerator()

        person_data = {
            "id": 1,
            "name": "John Smith",
            "itn": "1234567890"
        }

        patterns = generator.generate_patterns_for_person(person_data)
        ac_patterns = generator.export_for_ac(patterns)

        assert len(ac_patterns) == len(patterns)

        # Check AC format
        for ac_pattern in ac_patterns:
            assert "pattern" in ac_pattern
            assert "tier" in ac_pattern
            assert "type" in ac_pattern
            assert "entity_id" in ac_pattern
            assert "confidence" in ac_pattern

    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": 1, "name": "Test Name", "itn": "1234567890"}]')
    def test_generate_full_corpus_persons_only(self, mock_file):
        generator = HighRecallACGenerator()

        with patch("json.load") as mock_json:
            mock_json.return_value = [{"id": 1, "name": "Test Name", "itn": "1234567890"}]

            corpus = generator.generate_full_corpus(persons_file="test.json")

            assert corpus["statistics"]["persons_processed"] == 1
            assert corpus["statistics"]["patterns_generated"] > 0
            assert "patterns" in corpus
            assert "generation_timestamp" in corpus

    def test_apply_tier_limits(self):
        generator = HighRecallACGenerator()

        # Create mock patterns exceeding limits
        from ai_service.layers.patterns.high_recall_ac_generator import GeneratedPattern, PatternMetadata

        patterns = []
        for i in range(10):  # More than Tier 0 limit of 3
            metadata = PatternMetadata(
                tier=PatternTier.TIER_0,
                pattern_type=PatternType.TAX_NUMBER,
                language="en",
                confidence=1.0,
                source_field="test"
            )
            patterns.append(GeneratedPattern(
                pattern=f"pattern_{i}",
                canonical=f"canonical_{i}",
                metadata=metadata,
                entity_id="test",
                entity_type="person"
            ))

        filtered = generator._apply_tier_limits(patterns)
        assert len(filtered) <= generator.tier_limits[PatternTier.TIER_0]


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios"""

    def test_ukrainian_person_comprehensive(self):
        generator = HighRecallACGenerator()

        person_data = {
            "id": 1,
            "name": "Ковриков Роман Валерійович",
            "name_en": "Kovrykov Roman Valeriiovych",
            "itn": "782611846337",
            "birthdate": "1976-08-09"
        }

        patterns = generator.generate_patterns_for_person(person_data)

        # Should have patterns from all tiers
        tier_counts = {}
        for pattern in patterns:
            tier = pattern.metadata.tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        assert PatternTier.TIER_0 in tier_counts  # Documents and canonical
        assert PatternTier.TIER_2 in tier_counts  # Initials, morphology
        assert PatternTier.TIER_3 in tier_counts  # Aggressive patterns

        # Should have both Ukrainian and English patterns
        ua_patterns = [p for p in patterns if "Ковриков" in p.pattern]
        en_patterns = [p for p in patterns if "Kovrykov" in p.pattern]
        assert len(ua_patterns) > 0
        assert len(en_patterns) > 0

    def test_russian_company_comprehensive(self):
        generator = HighRecallACGenerator()

        company_data = {
            "id": 2,
            "name": 'ООО "РОМАШКА"',
            "tax_number": "1234567890"
        }

        patterns = generator.generate_patterns_for_company(company_data)

        # Should have company patterns
        canonical_patterns = [p for p in patterns if p.metadata.tier == PatternTier.TIER_0]
        assert len(canonical_patterns) > 0

        # Should have quoted name without form
        no_form_patterns = [p for p in patterns if p.metadata.pattern_type == PatternType.COMPANY_NO_FORM]
        assert len(no_form_patterns) > 0

    def test_performance_on_large_dataset(self):
        """Test performance characteristics"""
        generator = HighRecallACGenerator()

        # Create a dataset of 100 persons
        persons = []
        for i in range(100):
            persons.append({
                "id": i,
                "name": f"Person{i} Surname{i}",
                "itn": f"123456789{i % 10}",
            })

        import time
        start_time = time.time()

        all_patterns = []
        for person in persons:
            patterns = generator.generate_patterns_for_person(person)
            all_patterns.extend(patterns)

        processing_time = time.time() - start_time

        # Should process reasonably fast
        assert processing_time < 5.0  # Less than 5 seconds for 100 persons
        assert len(all_patterns) > 100  # Should generate multiple patterns per person


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_inputs(self):
        generator = HighRecallACGenerator()

        # Empty person data
        patterns = generator.generate_patterns_for_person({})
        assert len(patterns) == 0

        # Empty company data
        patterns = generator.generate_patterns_for_company({})
        assert len(patterns) == 0

    def test_invalid_data_types(self):
        generator = HighRecallACGenerator()

        # Non-string names should be handled gracefully
        patterns = generator.generate_patterns_for_person({"id": 1, "name": None})
        assert len(patterns) == 0

    def test_special_characters_in_names(self):
        generator = HighRecallACGenerator()

        person_data = {
            "id": 1,
            "name": "Jean-Claude Van Damme",  # Hyphens
        }

        patterns = generator.generate_patterns_for_person(person_data)
        assert len(patterns) > 0

        # Should handle hyphens appropriately
        hyphen_patterns = [p for p in patterns if "-" in p.pattern]
        assert len(hyphen_patterns) > 0

    def test_unicode_handling(self):
        generator = HighRecallACGenerator()

        person_data = {
            "id": 1,
            "name": "Björk Guðmundsdóttir",  # Nordic characters
        }

        patterns = generator.generate_patterns_for_person(person_data)
        assert len(patterns) > 0

    def test_very_long_names(self):
        generator = HighRecallACGenerator()

        person_data = {
            "id": 1,
            "name": "Very Long Name With Many Words That Exceeds Normal Length",
        }

        patterns = generator.generate_patterns_for_person(person_data)
        # Should still generate patterns but respect limits
        assert len(patterns) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])