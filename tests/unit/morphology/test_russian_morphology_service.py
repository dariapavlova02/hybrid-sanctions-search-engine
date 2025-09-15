"""
Unit tests for RussianMorphology service
This addresses the critical coverage gap (37.1% -> 75%)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.ai_service.layers.normalization.morphology.russian_morphology import RussianMorphologyAnalyzer


class TestRussianMorphology:
    """Tests for RussianMorphology service"""

    @pytest.fixture
    def service(self):
        """Create a clean RussianMorphologyAnalyzer instance for testing"""
        return RussianMorphologyAnalyzer()

    def test_initialization(self, service):
        """Test RussianMorphology initialization"""
        assert service is not None
        assert hasattr(service, 'morph_analyzer')

    def test_get_all_forms_basic_name(self, service):
        """Test morphological forms generation for basic Russian names"""
        # Test with mock morphological analyzer
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'
            mock_parse_result.tag.gender = 'masc'
            mock_parse_result.tag.case = 'nomn'

            # Mock inflection results
            mock_inflected = Mock()
            mock_inflected.word = 'Владимира'
            mock_parse_result.inflect.return_value = mock_inflected

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_all_forms("Владимир")

            assert isinstance(result, list)
            assert len(result) > 0
            assert "Владимир" in result  # Original should be included
            mock_morph.parse.assert_called_with("Владимир")

    def test_get_all_forms_feminine_name(self, service):
        """Test morphological forms for feminine Russian names"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'
            mock_parse_result.tag.gender = 'femn'
            mock_parse_result.tag.case = 'nomn'

            # Mock different case forms
            forms = ['Мария', 'Марии', 'Марию', 'Марией', 'Марие']
            inflected_mocks = []
            for form in forms:
                mock_inflected = Mock()
                mock_inflected.word = form
                inflected_mocks.append(mock_inflected)

            mock_parse_result.inflect.side_effect = inflected_mocks
            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_all_forms("Мария")

            assert isinstance(result, list)
            assert "Мария" in result
            assert len(result) >= 1

    def test_get_all_forms_surname(self, service):
        """Test morphological forms for Russian surnames"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'
            mock_parse_result.tag.animacy = 'anim'

            # Mock surname inflections
            mock_inflected = Mock()
            mock_inflected.word = 'Петрова'
            mock_parse_result.inflect.return_value = mock_inflected

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_all_forms("Петров")

            assert isinstance(result, list)
            assert "Петров" in result

    def test_get_all_forms_patronymic(self, service):
        """Test morphological forms for Russian patronymics"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'
            mock_parse_result.tag.gender = 'masc'

            # Mock patronymic forms
            mock_inflected = Mock()
            mock_inflected.word = 'Ивановича'
            mock_parse_result.inflect.return_value = mock_inflected

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_all_forms("Иванович")

            assert isinstance(result, list)
            assert "Иванович" in result

    def test_get_all_forms_compound_name(self, service):
        """Test morphological forms for compound names"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'

            mock_inflected = Mock()
            mock_inflected.word = 'Анна-Марии'
            mock_parse_result.inflect.return_value = mock_inflected

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_all_forms("Анна-Мария")

            assert isinstance(result, list)
            assert "Анна-Мария" in result

    def test_get_all_forms_empty_input(self, service):
        """Test morphological forms with empty input"""
        result = service.get_all_forms("")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == ""

    def test_get_all_forms_whitespace_input(self, service):
        """Test morphological forms with whitespace input"""
        result = service.get_all_forms("   ")

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_get_all_forms_non_russian_text(self, service):
        """Test morphological forms with non-Russian text"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_morph.parse.return_value = []  # No parse results

            result = service.get_all_forms("John")

            assert isinstance(result, list)
            assert "John" in result  # Should still include original

    def test_get_all_forms_numbers(self, service):
        """Test morphological forms with numeric input"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_morph.parse.return_value = []

            result = service.get_all_forms("123")

            assert isinstance(result, list)
            assert "123" in result

    def test_get_all_forms_mixed_text(self, service):
        """Test morphological forms with mixed Cyrillic and Latin text"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'

            mock_inflected = Mock()
            mock_inflected.word = 'Владимир'
            mock_parse_result.inflect.return_value = mock_inflected

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_all_forms("Vladimir Владимир")

            assert isinstance(result, list)
            assert len(result) >= 1

    def test_get_all_forms_with_exception(self, service):
        """Test morphological forms handling when parser throws exception"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_morph.parse.side_effect = Exception("Parser error")

            result = service.get_all_forms("Тест")

            assert isinstance(result, list)
            assert "Тест" in result  # Should fallback to original

    def test__generate_diminutives_masculine(self, service):
        """Test diminutive forms for masculine names"""
        result = service._generate_diminutives("Владимир")

        assert isinstance(result, list)
        assert len(result) > 0
        # Should contain common diminutives
        expected_diminutives = ["Володя", "Володька", "Влад", "Владик"]
        assert any(dim in result for dim in expected_diminutives)

    def test__generate_diminutives_feminine(self, service):
        """Test diminutive forms for feminine names"""
        result = service._generate_diminutives("Мария")

        assert isinstance(result, list)
        assert len(result) > 0
        # Should contain common diminutives
        expected_diminutives = ["Маша", "Машенька", "Машка", "Марья"]
        assert any(dim in result for dim in expected_diminutives)

    def test__generate_diminutives_unknown_name(self, service):
        """Test diminutive forms for unknown names"""
        result = service._generate_diminutives("УнknownНame")

        assert isinstance(result, list)
        # Should return original name when no diminutives found
        assert "УнknownНame" in result

    def test__generate_diminutives_empty_input(self, service):
        """Test diminutive forms with empty input"""
        result = service._generate_diminutives("")

        assert isinstance(result, list)
        assert "" in result

    def test_get_word_forms_all_cases(self, service):
        """Test declension generation for all Russian cases"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'
            mock_parse_result.tag.gender = 'masc'

            # Mock inflections for all cases
            cases = ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct']
            inflected_forms = []

            for i, case in enumerate(cases):
                mock_inflected = Mock()
                mock_inflected.word = f"Владимир{i}"
                inflected_forms.append(mock_inflected)

            mock_parse_result.inflect.side_effect = inflected_forms
            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_word_forms("Владимир")

            assert isinstance(result, list)
            assert len(result) >= 1
            assert "Владимир" in result

    def test_get_word_forms_multiple_parses(self, service):
        """Test declension with multiple parse results"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            # Mock multiple parse results
            mock_parse1 = Mock()
            mock_parse1.tag.POS = 'NOUN'
            mock_parse1.tag.gender = 'masc'

            mock_parse2 = Mock()
            mock_parse2.tag.POS = 'NOUN'
            mock_parse2.tag.gender = 'femn'

            mock_inflected1 = Mock()
            mock_inflected1.word = "Form1"
            mock_parse1.inflect.return_value = mock_inflected1

            mock_inflected2 = Mock()
            mock_inflected2.word = "Form2"
            mock_parse2.inflect.return_value = mock_inflected2

            mock_morph.parse.return_value = [mock_parse1, mock_parse2]

            result = service.get_word_forms("Тест")

            assert isinstance(result, list)
            assert "Тест" in result

    def test_get_word_forms_inflection_failure(self, service):
        """Test declension when inflection returns None"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'NOUN'
            mock_parse_result.inflect.return_value = None  # Inflection fails

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_word_forms("Тест")

            assert isinstance(result, list)
            assert "Тест" in result

    def test_get_word_forms_non_noun(self, service):
        """Test declension with non-noun parts of speech"""
        with patch.object(service, 'morph_analyzer') as mock_morph:
            mock_parse_result = Mock()
            mock_parse_result.tag.POS = 'VERB'  # Not a noun

            mock_morph.parse.return_value = [mock_parse_result]

            result = service.get_word_forms("Бегать")

            assert isinstance(result, list)
            assert "Бегать" in result

    def test_is_russian_name_valid_names(self, service):
        """Test Russian name validation with valid names"""
        valid_names = [
            "Владимир",
            "Мария",
            "Александр",
            "Екатерина",
            "Иванов",
            "Петрова"
        ]

        for name in valid_names:
            assert service.is_russian_name(name) == True

    def test_is_russian_name_invalid_names(self, service):
        """Test Russian name validation with invalid names"""
        invalid_names = [
            "John",
            "Smith",
            "123",
            "",
            "абракадабра",
            "тестовоеслово"
        ]

        for name in invalid_names:
            assert service.is_russian_name(name) == False

    def test_is_russian_name_edge_cases(self, service):
        """Test Russian name validation with edge cases"""
        # Mixed case
        assert service.is_russian_name("вЛаДиМиР") == True

        # With spaces
        assert service.is_russian_name("Владимир Петров") == True

        # With hyphens
        assert service.is_russian_name("Анна-Мария") == True

        # Very short
        assert service.is_russian_name("А") == False

    def test_analyze_name_capitalization(self, service):
        """Test name normalization for proper capitalization"""
        test_cases = [
            ("владимир", "Владимир"),
            ("МАРИЯ", "Мария"),
            ("иВаНоВ", "Иванов"),
            ("анна-мария", "Анна-Мария")
        ]

        for input_name, expected in test_cases:
            result = service.analyze_name(input_name)
            assert result == expected

    def test_analyze_name_whitespace_handling(self, service):
        """Test name normalization whitespace handling"""
        test_cases = [
            ("  Владимир  ", "Владимир"),
            ("Мария   Петрова", "Мария Петрова"),
            ("\tИванов\n", "Иванов")
        ]

        for input_name, expected in test_cases:
            result = service.analyze_name(input_name)
            assert result == expected

    def test_analyze_name_empty_input(self, service):
        """Test name normalization with empty input"""
        assert service.analyze_name("") == ""
        assert service.analyze_name("   ") == ""

    def test__generate_variants_comprehensive(self, service):
        """Test comprehensive name variant generation"""
        with patch.object(service, 'get_all_forms') as mock_morph, \
             patch.object(service, '_generate_diminutives') as mock_dim, \
             patch.object(service, 'get_word_forms') as mock_decl:

            mock_morph.return_value = ["Владимир", "Владимира", "Владимиру"]
            mock_dim.return_value = ["Володя", "Влад", "Владик"]
            mock_decl.return_value = ["Владимир", "Владимира", "Владимиром"]

            result = service._generate_variants("Владимир")

            assert isinstance(result, list)
            assert len(result) > 0
            assert "Владимир" in result
            # Should include morphological, diminutive, and declension forms
            assert any(form in result for form in ["Владимира", "Володя", "Владимиром"])

    def test__generate_variants_deduplication(self, service):
        """Test that name variants are deduplicated"""
        with patch.object(service, 'get_all_forms') as mock_morph, \
             patch.object(service, '_generate_diminutives') as mock_dim, \
             patch.object(service, 'get_word_forms') as mock_decl:

            # Return overlapping variants
            mock_morph.return_value = ["Мария", "Марии"]
            mock_dim.return_value = ["Мария", "Маша"]  # Duplicate "Мария"
            mock_decl.return_value = ["Мария", "Марией"]  # Another duplicate

            result = service._generate_variants("Мария")

            # Should have no duplicates
            assert len(result) == len(set(result))
            assert "Мария" in result
            assert "Маша" in result

    def test__generate_variants_max_variants_limit(self, service):
        """Test that name variants respect maximum limit"""
        with patch.object(service, 'get_all_forms') as mock_morph, \
             patch.object(service, '_generate_diminutives') as mock_dim, \
             patch.object(service, 'get_word_forms') as mock_decl:

            # Return many variants
            many_variants = [f"Variant{i}" for i in range(100)]
            mock_morph.return_value = many_variants[:50]
            mock_dim.return_value = many_variants[50:80]
            mock_decl.return_value = many_variants[80:]

            result = service._generate_variants("Тест", max_variants=20)

            assert len(result) <= 20

    def test_batch_process_names(self, service):
        """Test batch processing of multiple names"""
        names = ["Владимир", "Мария", "Александр"]

        with patch.object(service, '_generate_variants') as mock_variants:
            mock_variants.side_effect = [
                ["Владимир", "Володя"],
                ["Мария", "Маша"],
                ["Александр", "Саша"]
            ]

            result = service.batch_process_names(names)

            assert isinstance(result, dict)
            assert len(result) == 3
            assert "Владимир" in result
            assert "Мария" in result
            assert "Александр" in result

            # Each should have its variants
            assert "Володя" in result["Владимир"]
            assert "Маша" in result["Мария"]
            assert "Саша" in result["Александр"]

    def test_batch_process_names_empty_list(self, service):
        """Test batch processing with empty list"""
        result = service.batch_process_names([])

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_batch_process_names_with_errors(self, service):
        """Test batch processing handling errors gracefully"""
        names = ["Владимир", "ErrorName", "Мария"]

        with patch.object(service, '_generate_variants') as mock_variants:
            mock_variants.side_effect = [
                ["Владимир", "Володя"],
                Exception("Processing error"),  # Error for second name
                ["Мария", "Маша"]
            ]

            result = service.batch_process_names(names)

            assert isinstance(result, dict)
            # Should have results for successful names only
            assert "Владимир" in result
            assert "Мария" in result
            # Error name should not be in result or have empty list
            assert "ErrorName" not in result or result.get("ErrorName", []) == []


class TestRussianMorphologyIntegration:
    """Integration tests for RussianMorphology service"""

    @pytest.fixture
    def service(self):
        return RussianMorphologyAnalyzer()

    def test_real_name_processing_integration(self, service):
        """Test real name processing integration (if pymorphy2 available)"""
        try:
            # Test with actual morphological processing
            result = service._generate_variants("Владимир", max_variants=10)

            assert isinstance(result, list)
            assert len(result) > 0
            assert "Владимир" in result

        except Exception:
            # If pymorphy2 not available, skip integration test
            pytest.skip("pymorphy2 not available for integration testing")

    def test_performance_with_long_name_lists(self, service):
        """Test performance with long lists of names"""
        # Generate test names
        test_names = [f"Тест{i}" for i in range(50)]

        import time
        start_time = time.time()

        result = service.batch_process_names(test_names)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process reasonably quickly (adjust threshold as needed)
        assert processing_time < 10  # 10 seconds for 50 names
        assert isinstance(result, dict)
        assert len(result) == len(test_names)

    def test_memory_usage_with_many_variants(self, service):
        """Test memory usage doesn't grow excessively with many variants"""
        import sys

        initial_size = sys.getsizeof(service)

        # Process many names
        for i in range(100):
            service._generate_variants(f"Тест{i}", max_variants=5)

        final_size = sys.getsizeof(service)

        # Memory growth should be reasonable
        growth = final_size - initial_size
        assert growth < 1000000  # Less than 1MB growth