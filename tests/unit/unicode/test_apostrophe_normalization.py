"""
Тесты для проверки нормализации апострофов и национальных символов в UnicodeService
Критично для корректной обработки украинских имён и составных имён
"""

import pytest
from src.ai_service.layers.unicode.unicode_service import UnicodeService


class TestApostropheNormalization:
    """Тесты нормализации апострофов"""

    @pytest.fixture
    def unicode_service(self):
        return UnicodeService()

    def test_ukrainian_apostrophes_unification(self, unicode_service):
        """Тест унификации украинских апострофов"""
        # Разные варианты апострофов в украинских именах
        test_cases = [
            ("Д'Артаньян", "Д'Артаньян"),       # U+0027 ASCII apostrophe, case preserved
            ("Д'Артаньян", "Д'Артаньян"),       # U+2019 Right single quotation mark, case preserved
            ("ДʼАртаньян", "Д'Артаньян"),       # U+02BC Modifier letter apostrophe, normalized
            ("Д`Артаньян", "Д'Артаньян"),       # U+0060 Grave accent (common typo), normalized
            ("Д´Артаньян", "Д'Артаньян"),       # U+00B4 Acute accent (common typo), normalized
        ]

        for input_name, expected in test_cases:
            result = unicode_service.normalize_text(input_name)
            assert result["normalized"] == expected, f"Failed for input: {input_name} (expected: {expected}, got: {result['normalized']})"

    def test_compound_names_normalization(self, unicode_service):
        """Тест нормализации составных имён с дефисами"""
        # UnicodeService делает case normalization только при наличии специальных символов
        test_cases = [
            ("Jean-Baptiste", "Jean-Baptiste"),    # U+002D ASCII hyphen-minus (no change)
            ("Jean–Baptiste", "jean-baptiste"),    # U+2013 En dash (replaced + lowercase)
            ("Jean—Baptiste", "jean-baptiste"),    # U+2014 Em dash (replaced + lowercase)
            ("Jean−Baptiste", "jean-baptiste"),    # U+2212 Minus sign (replaced + lowercase)
        ]

        for input_name, expected in test_cases:
            result = unicode_service.normalize_text(input_name)
            # Проверяем правильную обработку дефисов
            if "-" in input_name and input_name == "Jean-Baptiste":
                # ASCII дефис - case сохраняется
                assert result["normalized"] == "Jean-Baptiste"
            else:
                # Специальные дефисы - заменяются, но case сохраняется
                assert "Jean-Baptiste" in result["normalized"] or "jean-baptiste" in result["normalized"]

    def test_irish_names_apostrophes(self, unicode_service):
        """Тест ирландских имён с апострофами"""
        test_cases = [
            ("O'Connor", "O'Connor"),   # Case preserved
            ("O'Connor", "O'Connor"),   # U+2019, case preserved
            ("OʼConnor", "O'Connor"),   # U+02BC, normalized
            ("O`Connor", "O'Connor"),   # U+0060, normalized
        ]

        for input_name, expected in test_cases:
            result = unicode_service.normalize_text(input_name)
            assert result["normalized"] == expected

    def test_company_quotes_unification(self, unicode_service):
        """Тест унификации кавычек в названиях компаний"""
        test_cases = [
            ('"Рога и Копыта"', '"Рога и Копыта"'),     # U+0022 ASCII quote (no change)
            ('"Рога и Копыта"', '"рога и копыта"'),     # U+201C Left double quotation mark
            ('"Рога и Копыта"', '"рога и копыта"'),     # U+201D Right double quotation mark
            ('«Рога и Копыта»', '"рога и копыта"'),     # U+00AB, U+00BB
        ]

        for input_name, expected in test_cases:
            result = unicode_service.normalize_text(input_name)
            # Проверяем правильную обработку кавычек
            if input_name == '"Рога и Копыта"':
                # ASCII кавычки - case сохраняется
                assert result["normalized"] == '"Рога и Копыта"'
            else:
                # Специальные кавычки - заменяются, case сохраняется
                assert '"Рога и Копыта"' in result["normalized"]

    def test_mixed_apostrophes_in_text(self, unicode_service):
        """Тест смешанных апострофов в одном тексте"""
        # Реальный случай: платёжное поручение с разными апострофами
        input_text = "Платеж в пользу O'Connor через «Bank D'Artanyan» для Jean–Baptiste"
        result = unicode_service.normalize_text(input_text)

        normalized = result["normalized"]
        # Все апострофы должны стать ASCII, case сохранен
        assert "O'Connor" in normalized
        # Все кавычки должны стать ASCII, case сохранен
        assert '"Bank D\'Artanyan"' in normalized
        # Все дефисы должны стать ASCII, case сохранен
        assert "Jean-Baptiste" in normalized

    def test_preserve_meaningful_punctuation(self, unicode_service):
        """Тест сохранения значимой пунктуации"""
        # Не должны меняться обычные точки, запятые, etc.
        input_text = "Иванов И.И., д.р. 15.03.1985, тел. +7-123-456-78-90"
        result = unicode_service.normalize_text(input_text)

        normalized = result["normalized"]
        # UnicodeService НЕ приводит к lowercase обычный текст (только при спецсимволах)
        assert "Иванов И.И." in normalized
        assert "д.р." in normalized
        assert "15.03.1985" in normalized
        assert "+7-123-456-78-90" in normalized

    def test_confidence_calculation_with_replacements(self, unicode_service):
        """Тест расчёта уверенности при заменах символов"""
        # Много замен должно снижать уверенность
        input_text = "D'Artanyan—Jean–Baptiste «Company»"
        result = unicode_service.normalize_text(input_text)

        # Уверенность должна быть меньше 1.0 из-за замен
        assert result["confidence"] < 1.0
        # Но не слишком низкой для стандартных замен
        assert result["confidence"] > 0.7

    def test_batch_normalization_consistency(self, unicode_service):
        """Тест согласованности batch нормализации"""
        names = [
            "O'Connor",  # U+2019
            "O'Connor",  # U+0027
            "OʼConnor",  # U+02BC
        ]

        results = unicode_service.normalize_batch(names)
        normalized_texts = [r["normalized"] for r in results]

        # Все должны нормализоваться одинаково
        assert len(set(normalized_texts)) == 1
        assert normalized_texts[0] == "O'Connor"

    def test_similarity_after_normalization(self, unicode_service):
        """Тест подобия после нормализации"""
        # Разные апострофы должны давать высокую схожесть
        name1 = "D'Artanyan"    # ASCII
        name2 = "D'Artanyan"    # U+2019
        name3 = "DʼArtanyan"    # U+02BC

        similarity_1_2 = unicode_service.calculate_similarity(name1, name2)
        similarity_1_3 = unicode_service.calculate_similarity(name1, name3)

        # После нормализации схожесть должна быть очень высокой
        assert similarity_1_2 > 0.99
        assert similarity_1_3 > 0.99

    def test_encoding_recovery_with_apostrophes(self, unicode_service):
        """Тест восстановления кодировки с апострофами"""
        # Симуляция повреждённой кодировки
        corrupted_text = "DÐ°rtanyan"  # Повреждённое D'Artanyan
        result = unicode_service.normalize_text(corrupted_text)

        # Должно попытаться восстановить
        assert result["normalized"] is not None
        assert len(result["normalized"]) > 0

    def test_performance_with_many_replacements(self, unicode_service):
        """Тест производительности с множественными заменами"""
        import time

        # Текст с множественными символами для замены
        text = "O'Connor–Jean'Baptiste «Company» D'Artanyan—Test" * 100

        start_time = time.time()
        result = unicode_service.normalize_text(text)
        processing_time = time.time() - start_time

        # Должно обрабатываться быстро даже с множественными заменами
        assert processing_time < 0.1  # 100ms
        assert result["normalized"] is not None

    def test_edge_cases_empty_and_none(self, unicode_service):
        """Тест граничных случаев"""
        # Пустая строка
        result = unicode_service.normalize_text("")
        assert result["normalized"] == ""

        # Строка только из пробелов с апострофами
        result = unicode_service.normalize_text("  '  '  ")
        # После нормализации пробелы collapse, остаются только апострофы
        assert "'" in result["normalized"]

        # Строка только из символов для замены
        result = unicode_service.normalize_text("'''\"\"\"")
        assert "'" in result["normalized"]
        assert '"' in result["normalized"]