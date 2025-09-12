"""Tests for extended role tagging functionality."""
import pytest
from src.ai_service.services.normalization_service import NormalizationService


class TestExtendedRoleTagging:
    """Test extended role tagging with improved patterns and multi-initial handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = NormalizationService()
    
    def test_multi_initial_splitting(self):
        """Test that multi-initials like П.І. are split into separate initials."""
        tokens = ["П.І.", "Коваленко"]
        tagged = self.service._tag_roles(tokens, "uk")
        
        # Should split П.І. into П. and І.
        assert len(tagged) == 3  # П., І., Коваленко
        assert ("П.", "initial") in tagged
        assert ("І.", "initial") in tagged
        assert ("Коваленко", "surname") in tagged
    
    def test_triple_initial_splitting(self):
        """Test that triple initials like А.Б.В. are split correctly."""
        tokens = ["А.Б.В.", "Петров"]
        tagged = self.service._tag_roles(tokens, "ru")
        
        # Should split А.Б.В. into А., Б., В.
        assert len(tagged) == 4  # А., Б., В., Петров
        assert ("А.", "initial") in tagged
        assert ("Б.", "initial") in tagged
        assert ("В.", "initial") in tagged
        assert ("Петров", "surname") in tagged
    
    def test_enhanced_patronymic_patterns_male(self):
        """Test enhanced male patronymic patterns with case endings."""
        test_cases = [
            "Петрович",    # Nominative
            "Петровича",   # Genitive/Accusative
            "Петровичу",   # Dative
            "Петровичем",  # Instrumental
            "Петровиче",   # Prepositional
            "Іванович",    # Ukrainian
            "Івановича",   # Ukrainian genitive
            "Сергійович",  # Ukrainian with й
        ]
        
        for patronymic in test_cases:
            tokens = ["Іван", patronymic, "Коваленко"]
            tagged = self.service._tag_roles(tokens, "uk")
            
            # Find the patronymic in tagged results
            patronymic_roles = [role for token, role in tagged if token == patronymic]
            assert len(patronymic_roles) == 1, f"Expected exactly one role for {patronymic}"
            assert patronymic_roles[0] == "patronymic", f"Expected patronymic role for {patronymic}, got {patronymic_roles[0]}"
    
    def test_enhanced_patronymic_patterns_female(self):
        """Test enhanced female patronymic patterns with case endings."""
        test_cases = [
            "Петрівна",    # Nominative
            "Петрівни",    # Genitive
            "Петрівну",    # Accusative
            "Петрівною",   # Instrumental
            "Петрівні",    # Prepositional/Dative
            "Іванівна",    # Ukrainian
            "Сергіївна",   # Ukrainian with double і
        ]
        
        for patronymic in test_cases:
            tokens = ["Олена", patronymic, "Коваленко"]
            tagged = self.service._tag_roles(tokens, "uk")
            
            # Find the patronymic in tagged results
            patronymic_roles = [role for token, role in tagged if token == patronymic]
            assert len(patronymic_roles) == 1, f"Expected exactly one role for {patronymic}"
            assert patronymic_roles[0] == "patronymic", f"Expected patronymic role for {patronymic}, got {patronymic_roles[0]}"
    
    def test_enhanced_surname_patterns_enko(self):
        """Test enhanced -enko surname patterns with case endings."""
        test_cases = [
            "Коваленко",   # Nominative
            "Коваленка",   # Genitive
            "Коваленку",   # Dative
            "Коваленком",  # Instrumental
            "Коваленці",   # Prepositional
            "Коваленкою",  # Instrumental feminine
        ]
        
        for surname in test_cases:
            tokens = ["Іван", "Петрович", surname]
            tagged = self.service._tag_roles(tokens, "uk")
            
            # Find the surname in tagged results
            surname_roles = [role for token, role in tagged if token == surname]
            assert len(surname_roles) == 1, f"Expected exactly one role for {surname}"
            assert surname_roles[0] == "surname", f"Expected surname role for {surname}, got {surname_roles[0]}"
    
    def test_enhanced_surname_patterns_ov_ova(self):
        """Test enhanced -ov/-ova surname patterns with case endings."""
        test_cases = [
            "Петров",      # Nominative masculine
            "Петрова",     # Nominative feminine / Genitive masculine
            "Петрову",     # Dative feminine / Accusative masculine
            "Петровым",    # Instrumental masculine
            "Петровой",    # Instrumental/Genitive/Dative/Prepositional feminine
            "Петровою",    # Instrumental feminine (Ukrainian)
        ]
        
        for surname in test_cases:
            tokens = ["Сергей", surname]
            tagged = self.service._tag_roles(tokens, "ru")
            
            # Find the surname in tagged results
            surname_roles = [role for token, role in tagged if token == surname]
            assert len(surname_roles) == 1, f"Expected exactly one role for {surname}"
            assert surname_roles[0] == "surname", f"Expected surname role for {surname}, got {surname_roles[0]}"
    
    def test_enhanced_surname_patterns_sky_ska(self):
        """Test enhanced -ський/-ська surname patterns with case endings."""
        test_cases = [
            "Левський",    # Nominative masculine
            "Левська",     # Nominative feminine
            "Левську",     # Accusative feminine
            "Левським",    # Instrumental masculine
            "Левській",    # Prepositional/Dative feminine
            "Левські",     # Nominative plural
            "Левських",    # Genitive/Prepositional plural
            "Левською",    # Instrumental feminine (Ukrainian)
        ]
        
        for surname in test_cases:
            tokens = ["Іван", surname]
            tagged = self.service._tag_roles(tokens, "uk")
            
            # Find the surname in tagged results
            surname_roles = [role for token, role in tagged if token == surname]
            assert len(surname_roles) == 1, f"Expected exactly one role for {surname}"
            assert surname_roles[0] == "surname", f"Expected surname role for {surname}, got {surname_roles[0]}"
    
    def test_new_surname_patterns_yan(self):
        """Test new -ян surname patterns."""
        test_cases = [
            "Петросян",    # Armenian surname
            "Акопян",      # Armenian surname
            "Григорян",    # Armenian surname
            "Петросяна",   # Genitive
            "Петросяну",   # Dative
            "Петросяном",  # Instrumental
        ]
        
        for surname in test_cases:
            tokens = ["Арам", surname]
            tagged = self.service._tag_roles(tokens, "ru")
            
            # Find the surname in tagged results
            surname_roles = [role for token, role in tagged if token == surname]
            assert len(surname_roles) == 1, f"Expected exactly one role for {surname}"
            assert surname_roles[0] == "surname", f"Expected surname role for {surname}, got {surname_roles[0]}"
    
    def test_new_surname_patterns_dze(self):
        """Test new -дзе surname patterns (Georgian)."""
        test_cases = [
            "Кварацхелидзе",  # Georgian surname
            "Джугашвилидзе",  # Georgian surname
            "Церетелидзе",    # Georgian surname
        ]
        
        for surname in test_cases:
            tokens = ["Георгий", surname]
            tagged = self.service._tag_roles(tokens, "ru")
            
            # Find the surname in tagged results
            surname_roles = [role for token, role in tagged if token == surname]
            assert len(surname_roles) == 1, f"Expected exactly one role for {surname}"
            assert surname_roles[0] == "surname", f"Expected surname role for {surname}, got {surname_roles[0]}"
    
    def test_conservative_unknown_tagging(self):
        """Test that unknown words are conservatively tagged as unknown."""
        test_cases = [
            ["странное", "слово"],           # Strange words
            ["НЕИЗВЕСТНО", "ЧТО"],          # Unknown uppercase
            ["123", "456"],                  # Numbers
            ["email@domain.com"],           # Email
            ["www.example.com"],            # URL
        ]
        
        for tokens in test_cases:
            tagged = self.service._tag_roles(tokens, "ru")
            
            # All should be tagged as unknown
            for token, role in tagged:
                if token in tokens:
                    assert role == "unknown", f"Expected unknown role for {token}, got {role}"
    
    def test_positional_heuristics_still_work(self):
        """Test that positional heuristics still work for ambiguous cases."""
        # First token that could be surname but is likely given name
        tokens = ["Александр", "Петрович", "Иванов"]
        tagged = self.service._tag_roles(tokens, "ru")
        
        # Should apply positional heuristics
        roles = {token: role for token, role in tagged}
        
        # Александр should be recognized as given (first position + known name)
        assert roles.get("Александр") in ["given", "unknown"]  # May depend on dictionaries
        assert roles.get("Петрович") == "patronymic"
        assert roles.get("Иванов") == "surname"
    
    def test_integration_with_organization_roles(self):
        """Test that personal name roles work alongside organization roles."""
        # This should be handled by organization logic, but personal names should still work
        tokens = ["Іван", "Петрович", "Коваленко", "ТОВ", "ТЕСТ"]
        tagged = self.service._tag_roles(tokens, "uk")
        
        roles = {token: role for token, role in tagged}
        
        # Personal names should be tagged correctly
        assert roles.get("Іван") in ["given", "unknown"]
        assert roles.get("Петрович") == "patronymic"
        assert roles.get("Коваленко") == "surname"
        
        # Organization tokens should be handled by org logic
        assert roles.get("ТОВ") == "legal_form"
        # ТЕСТ might be org or unknown depending on context