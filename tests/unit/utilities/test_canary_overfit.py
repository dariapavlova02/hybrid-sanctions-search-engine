"""
Canary tests to prevent overfitting to specific test cases.
These tests ensure that context words are never treated as personal names.
"""

import pytest
from ai_service.layers.normalization.normalization_service import NormalizationService


class TestCanaryOverfit:
    """Test that context words are never treated as personal names"""

    @pytest.fixture
    def service(self):
        """Create NormalizationService instance"""
        return NormalizationService()

    @pytest.mark.asyncio
    async def test_context_words_never_become_names(self, service):
        """Test that context words like 'та', 'и', 'and', 'разом', 'працюють' never become given/surname"""
        # Test case from the requirement: "П.І. Коваленко, ТОВ "ПРИВАТБАНК" та Петросян працюють разом"
        text = 'П.І. Коваленко, ТОВ "ПРИВАТБАНК" та Петросян працюють разом'
        result = await service.normalize(text, language='uk', preserve_names=True)
        
        # Check that context words are not in normalized output
        normalized = result.normalized.lower()
        context_words = ['та', 'працюють', 'разом']
        
        for context_word in context_words:
            assert context_word not in normalized, f"Context word '{context_word}' should not appear in normalized output: {result.normalized}"
        
        # Check that only actual names are preserved
        expected_names = ['п.і.', 'коваленко', 'петросян']
        for name in expected_names:
            assert name in normalized, f"Expected name '{name}' not found in normalized output: {result.normalized}"
        
        # Check that organization is detected
        assert 'приватбанк' in normalized.lower(), f"Organization 'ПРИВАТБАНК' should be detected in normalized output: {result.normalized}"

    @pytest.mark.asyncio
    async def test_ukrainian_context_words(self, service):
        """Test Ukrainian context words are never treated as names"""
        context_words = ['та', 'і', 'або', 'але', 'щоб', 'як', 'що', 'хто', 'де', 'коли', 'чому']
        context_words.extend(['працюють', 'працює', 'працюю', 'працюємо', 'працюєте', 'працювати'])
        context_words.extend(['разом', 'окремо', 'тут', 'там', 'тепер', 'зараз'])
        context_words.extend(['дуже', 'досить', 'майже', 'зовсім', 'повністю', 'частково'])
        context_words.extend(['добре', 'погано', 'краще', 'гірше', 'найкраще', 'найгірше'])
        context_words.extend(['може', 'можна', 'можливо', 'ймовірно', 'звичайно'])
        context_words.extend(['так', 'ні', 'можливо'])
        
        for context_word in context_words:
            # Test each context word in a sentence with actual names
            text = f'Іван {context_word} Петро Коваленко'
            result = await service.normalize(text, language='uk', preserve_names=True)
            
            # Context word should not appear in normalized output
            assert context_word not in result.normalized.lower(), f"Context word '{context_word}' should not appear in normalized output: {result.normalized}"
            
            # Only actual names should be preserved
            assert 'іван' in result.normalized.lower(), f"Expected name 'Іван' not found in normalized output: {result.normalized}"
            assert 'петро' in result.normalized.lower(), f"Expected name 'Петро' not found in normalized output: {result.normalized}"
            assert 'коваленко' in result.normalized.lower(), f"Expected name 'Коваленко' not found in normalized output: {result.normalized}"

    @pytest.mark.asyncio
    async def test_russian_context_words(self, service):
        """Test Russian context words are never treated as names"""
        context_words = ['и', 'или', 'но', 'чтобы', 'как', 'что', 'кто', 'где', 'когда', 'почему']
        context_words.extend(['работают', 'работает', 'работаю', 'работаем', 'работаете', 'работать'])
        context_words.extend(['вместе', 'отдельно', 'здесь', 'там', 'теперь', 'сейчас'])
        context_words.extend(['очень', 'довольно', 'почти', 'совсем', 'полностью', 'частично'])
        context_words.extend(['хорошо', 'плохо', 'лучше', 'хуже', 'лучший', 'худший'])
        context_words.extend(['может', 'можно', 'возможно', 'вероятно', 'обычно'])
        context_words.extend(['да', 'нет', 'возможно'])
        
        for context_word in context_words:
            # Test each context word in a sentence with actual names
            text = f'Иван {context_word} Петр Коваленко'
            result = await service.normalize(text, language='ru', preserve_names=True)
            
            # Context word should not appear in normalized output
            assert context_word not in result.normalized.lower(), f"Context word '{context_word}' should not appear in normalized output: {result.normalized}"
            
            # Only actual names should be preserved
            assert 'иван' in result.normalized.lower(), f"Expected name 'Иван' not found in normalized output: {result.normalized}"
            assert 'петр' in result.normalized.lower(), f"Expected name 'Петр' not found in normalized output: {result.normalized}"
            assert 'коваленко' in result.normalized.lower(), f"Expected name 'Коваленко' not found in normalized output: {result.normalized}"

    @pytest.mark.asyncio
    async def test_english_context_words(self, service):
        """Test English context words are never treated as names"""
        context_words = ['and', 'or', 'but', 'so', 'if', 'when', 'where', 'why', 'how', 'what', 'who', 'which']
        context_words.extend(['work', 'works', 'working', 'worked'])
        context_words.extend(['together', 'separately', 'here', 'there', 'now', 'then'])
        context_words.extend(['very', 'quite', 'almost', 'completely', 'partially'])
        context_words.extend(['good', 'bad', 'better', 'worse', 'best', 'worst'])
        context_words.extend(['can', 'could', 'may', 'might', 'should', 'would', 'must'])
        context_words.extend(['yes', 'no', 'maybe', 'perhaps', 'probably', 'usually'])
        
        for context_word in context_words:
            # Test each context word in a sentence with actual names
            text = f'John {context_word} Jane Smith'
            result = await service.normalize(text, language='en', preserve_names=True)
            
            # Context word should not appear in normalized output
            assert context_word not in result.normalized.lower(), f"Context word '{context_word}' should not appear in normalized output: {result.normalized}"
            
            # Only actual names should be preserved
            assert 'john' in result.normalized.lower(), f"Expected name 'John' not found in normalized output: {result.normalized}"
            assert 'jane' in result.normalized.lower(), f"Expected name 'Jane' not found in normalized output: {result.normalized}"
            assert 'smith' in result.normalized.lower(), f"Expected name 'Smith' not found in normalized output: {result.normalized}"

    @pytest.mark.asyncio
    async def test_mixed_language_context_words(self, service):
        """Test mixed language context words are never treated as names"""
        # Test case with mixed Ukrainian and English context words
        text = 'П.І. Коваленко and ТОВ "ПРИВАТБАНК" та Петросян work together разом'
        result = await service.normalize(text, language='uk', preserve_names=True)
        
        # Context words should not appear in normalized output
        context_words = ['and', 'та', 'work', 'together', 'разом']
        normalized = result.normalized.lower()
        
        for context_word in context_words:
            assert context_word not in normalized, f"Context word '{context_word}' should not appear in normalized output: {result.normalized}"
        
        # Only actual names should be preserved
        expected_names = ['п.і.', 'коваленко', 'петросян', 'приватбанк']
        for name in expected_names:
            assert name in normalized, f"Expected name '{name}' not found in normalized output: {result.normalized}"

    @pytest.mark.asyncio
    async def test_positional_heuristics_blocked_for_context_words(self, service):
        """Test that positional heuristics (first→given, last→surname) are blocked for context words"""
        # Test case where context word is in first position
        text = 'та Іван Петро Коваленко'
        result = await service.normalize(text, language='uk', preserve_names=True)
        
        # 'та' should not become 'given' due to positional heuristics
        assert 'та' not in result.normalized.lower(), f"Context word 'та' should not appear in normalized output: {result.normalized}"
        assert 'іван' in result.normalized.lower(), f"Expected name 'Іван' not found in normalized output: {result.normalized}"
        assert 'петро' in result.normalized.lower(), f"Expected name 'Петро' not found in normalized output: {result.normalized}"
        assert 'коваленко' in result.normalized.lower(), f"Expected name 'Коваленко' not found in normalized output: {result.normalized}"
        
        # Test case where context word is in last position
        text = 'Іван Петро Коваленко разом'
        result = await service.normalize(text, language='uk', preserve_names=True)
        
        # 'разом' should not become 'surname' due to positional heuristics
        assert 'разом' not in result.normalized.lower(), f"Context word 'разом' should not appear in normalized output: {result.normalized}"
        assert 'іван' in result.normalized.lower(), f"Expected name 'Іван' not found in normalized output: {result.normalized}"
        assert 'петро' in result.normalized.lower(), f"Expected name 'Петро' not found in normalized output: {result.normalized}"
        assert 'коваленко' in result.normalized.lower(), f"Expected name 'Коваленко' not found in normalized output: {result.normalized}"
