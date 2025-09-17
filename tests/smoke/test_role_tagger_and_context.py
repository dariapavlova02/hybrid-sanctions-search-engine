"""Smoke tests for role tagger and organizational context detection."""

import pytest
from src.ai_service.layers.normalization.lexicon_loader import Lexicons
from src.ai_service.layers.normalization.role_tagger import RoleTagger, TokenRole


class TestRoleTaggerAndContext:
    """Test role tagger and organizational context detection."""

    @pytest.fixture
    def mock_lexicons(self):
        """Create mock lexicons for testing."""
        return Lexicons(
            stopwords={
                "ru": {"и", "в", "з", "та", "на", "по", "за", "до", "от", "для"},
                "uk": {"і", "в", "з", "та", "на", "по", "за", "до", "від", "для"},
                "en": {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to"}
            },
            legal_forms={"ооо", "зао", "оао", "пао", "ао", "ип", "чп", "фоп", "тов", "пп", "llc", "ltd", "inc", "corp", "co", "gmbh"},
            payment_context={"платеж", "платёж", "платити", "платити", "одержувач", "відправник", "отправитель", "получатель", "рахунок", "счет"}
        )

    @pytest.fixture
    def role_tagger(self):
        """Create role tagger instance for testing."""
        from src.ai_service.layers.normalization.lexicon_loader import get_lexicons
        lexicons = get_lexicons()
        return RoleTagger(lexicons, window=3)

    def test_organization_span_detection(self, role_tagger):
        """Test organization span detection."""
        text = "оплата ТОВ ПРИВАТБАНК Ивану Петрову"
        tokens = text.split()
        
        role_tags = role_tagger.tag(tokens, "uk")
        
        # Check organization detection
        org_spans = role_tagger.get_organization_spans(role_tags)
        assert len(org_spans) == 1
        
        # Check person candidates
        person_candidates = role_tagger.get_person_candidates(role_tags)
        assert "Ивану" in person_candidates
        assert "Петрову" in person_candidates

    def test_stopwords_filtering(self, role_tagger):
        """Test stopwords filtering."""
        text = "и Иван в Петров на работе"
        tokens = text.split()
        
        role_tags = role_tagger.tag(tokens, "ru")
        
        # Check stopword filtering
        stopword_count = role_tagger.get_stopword_count(role_tags)
        assert stopword_count >= 3
        
        # Check person candidates
        person_candidates = role_tagger.get_person_candidates(role_tags)
        assert "Иван" in person_candidates
        assert "Петров" in person_candidates
        assert "и" not in person_candidates
        assert "в" not in person_candidates
        assert "на" not in person_candidates

    def test_multiple_organization_spans(self, role_tagger):
        """Test multiple organization spans."""
        text = "ТОВ ПРИВАТБАНК и ООО РОМАШКА работают вместе"
        tokens = text.split()
        
        role_tags = role_tagger.tag(tokens, "ru")
        
        # Check organization detection
        org_spans = role_tagger.get_organization_spans(role_tags)
        assert len(org_spans) == 2

    def test_edge_cases(self, role_tagger):
        """Test edge cases handling."""
        # Empty text
        role_tags = role_tagger.tag([], "ru")
        assert len(role_tags) == 0
        
        # Single token
        role_tags = role_tagger.tag(["Иван"], "ru")
        assert len(role_tags) == 1
        assert role_tags[0].role == TokenRole.PERSON_CANDIDATE
        
        # Single stopword
        role_tags = role_tagger.tag(["и"], "ru")
        assert len(role_tags) == 1
        assert role_tags[0].role == TokenRole.STOPWORD

    def test_case_insensitive_legal_forms(self, role_tagger):
        """Test case-insensitive legal form matching."""
        test_cases = ["ТОВ", "тов", "Тов"]
        
        for legal_form in test_cases:
            text = f"{legal_form} ПРИВАТБАНК"
            tokens = text.split()
            
            role_tags = role_tagger.tag(tokens, "ru")
            org_spans = role_tagger.get_organization_spans(role_tags)
            
            assert len(org_spans) == 1, f"Failed for legal form: {legal_form}"


if __name__ == "__main__":
    pytest.main([__file__])