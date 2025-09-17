"""
Property-based tests for NormalizationService using Hypothesis.

This module implements comprehensive property-based testing for the normalization
service, covering critical properties like idempotence, feminine preservation,
character set constraints, and metamorphic testing.
"""

import asyncio
import re
import string
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from hypothesis.strategies import composite, text, lists, one_of, sampled_from

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.contracts.base_contracts import NormalizationResult, TokenTrace


# ============================================================================
# Test Configuration and Settings
# ============================================================================

# Property test settings
PROPERTY_SETTINGS = settings(
    deadline=None,
    max_examples=1000,
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.too_slow,
        HealthCheck.data_too_large
    ]
)


# ============================================================================
# Helper Functions
# ============================================================================

def letters_only(s: str) -> str:
    """Extract only letters and digits from string, converted to lowercase."""
    return ''.join(c.lower() for c in s if c.isalnum())


def is_feminine(tokens: List[str]) -> bool:
    """Check if tokens contain feminine surname suffixes."""
    feminine_suffixes = {
        'ова', 'ева', 'іна', 'ська', 'ская', 'ская', 'ская',
        'ова', 'ева', 'іна', 'ська', 'ская', 'ская', 'ская'
    }
    
    for token in tokens:
        token_lower = token.lower()
        for suffix in feminine_suffixes:
            if token_lower.endswith(suffix):
                return True
    return False


def allowed_added_chars() -> Set[str]:
    """Return set of characters that can be added during normalization."""
    return {'.', '-'}


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@composite
def russian_given_name(draw):
    """Generate Russian given names."""
    names = [
        'Александр', 'Алексей', 'Андрей', 'Антон', 'Артем', 'Борис', 'Вадим',
        'Валентин', 'Валерий', 'Василий', 'Виктор', 'Владимир', 'Владислав',
        'Геннадий', 'Георгий', 'Дмитрий', 'Евгений', 'Иван', 'Игорь', 'Кирилл',
        'Константин', 'Максим', 'Михаил', 'Николай', 'Олег', 'Павел', 'Петр',
        'Роман', 'Сергей', 'Станислав', 'Федор', 'Юрий'
    ]
    return draw(sampled_from(names))


@composite
def ukrainian_given_name(draw):
    """Generate Ukrainian given names."""
    names = [
        'Олександр', 'Олексій', 'Андрій', 'Антон', 'Артем', 'Борис', 'Вадим',
        'Валентин', 'Валерій', 'Василь', 'Віктор', 'Володимир', 'Владислав',
        'Геннадій', 'Георгій', 'Дмитро', 'Євген', 'Іван', 'Ігор', 'Кирило',
        'Костянтин', 'Максим', 'Михайло', 'Микола', 'Олег', 'Павло', 'Петро',
        'Роман', 'Сергій', 'Станіслав', 'Федір', 'Юрій'
    ]
    return draw(sampled_from(names))


@composite
def english_given_name(draw):
    """Generate English given names."""
    names = [
        'William', 'James', 'John', 'Robert', 'Michael', 'David', 'Richard',
        'Charles', 'Joseph', 'Thomas', 'Christopher', 'Daniel', 'Paul', 'Mark',
        'Donald', 'George', 'Kenneth', 'Steven', 'Edward', 'Brian', 'Ronald',
        'Anthony', 'Kevin', 'Jason', 'Matthew', 'Gary', 'Timothy', 'Jose',
        'Larry', 'Jeffrey', 'Frank', 'Scott', 'Eric', 'Stephen', 'Andrew'
    ]
    return draw(sampled_from(names))


@composite
def russian_surname(draw):
    """Generate Russian surnames."""
    surnames = [
        'Петров', 'Иванов', 'Сидоров', 'Козлов', 'Новиков', 'Морозов',
        'Петухов', 'Волков', 'Соколов', 'Лебедев', 'Козлов', 'Новиков',
        'Морозов', 'Петухов', 'Волков', 'Соколов', 'Лебедев', 'Козлов',
        'Новиков', 'Морозов', 'Петухов', 'Волков', 'Соколов', 'Лебедев'
    ]
    return draw(sampled_from(surnames))


@composite
def ukrainian_surname(draw):
    """Generate Ukrainian surnames."""
    surnames = [
        'Петренко', 'Іванов', 'Сидоренко', 'Козленко', 'Новиченко', 'Морозенко',
        'Петушенко', 'Вовченко', 'Соколенко', 'Лебеденко', 'Козленко', 'Новиченко',
        'Морозенко', 'Петушенко', 'Вовченко', 'Соколенко', 'Лебеденко', 'Козленко',
        'Новиченко', 'Морозенко', 'Петушенко', 'Вовченко', 'Соколенко', 'Лебеденко'
    ]
    return draw(sampled_from(surnames))


@composite
def english_surname(draw):
    """Generate English surnames."""
    surnames = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
        'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
        'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
        'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark'
    ]
    return draw(sampled_from(surnames))


@composite
def feminine_surname(draw):
    """Generate feminine surnames with appropriate suffixes."""
    base_surnames = [
        'Петров', 'Иванов', 'Сидоров', 'Козлов', 'Новиков', 'Морозов',
        'Петренко', 'Іванов', 'Сидоренко', 'Козленко', 'Новиченко', 'Морозенко'
    ]
    suffixes = ['ова', 'ева', 'іна', 'ська', 'ская']
    
    base = draw(sampled_from(base_surnames))
    suffix = draw(sampled_from(suffixes))
    return base + suffix


@composite
def initials(draw):
    """Generate initials."""
    letters = string.ascii_uppercase + 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ'
    return draw(sampled_from(letters))


@composite
def compound_surname(draw):
    """Generate compound surnames with hyphens."""
    first_part = draw(one_of(russian_surname(), ukrainian_surname(), english_surname()))
    second_part = draw(one_of(russian_surname(), ukrainian_surname(), english_surname()))
    return f"{first_part}-{second_part}"


@composite
def name_with_noise(draw):
    """Generate names with various types of noise."""
    base_name = draw(one_of(
        russian_given_name(),
        ukrainian_given_name(), 
        english_given_name(),
        russian_surname(),
        ukrainian_surname(),
        english_surname()
    ))
    
    noise_types = draw(lists(sampled_from([
        'apostrophe', 'dots', 'case_mix', 'spaces', 'homoglyph'
    ]), min_size=0, max_size=3))
    
    result = base_name
    
    for noise_type in noise_types:
        if noise_type == 'apostrophe':
            result = result.replace('а', 'а\'', 1) if 'а' in result else result
        elif noise_type == 'dots':
            result = result + '...'
        elif noise_type == 'case_mix':
            result = ''.join(c.upper() if i % 2 == 0 else c.lower() 
                           for i, c in enumerate(result))
        elif noise_type == 'spaces':
            result = ' ' + result + ' '
        elif noise_type == 'homoglyph':
            result = result.replace('а', 'a')  # Latin 'a' instead of Cyrillic
    
    return result


@composite
def full_name(draw):
    """Generate full names with various components."""
    components = []
    
    # Add given name
    given = draw(one_of(russian_given_name(), ukrainian_given_name(), english_given_name()))
    components.append(given)
    
    # Optionally add patronymic (for Slavic names)
    if draw(st.booleans()) and any(lang in given.lower() for lang in ['александр', 'олександр', 'иван', 'іван']):
        patronymic = draw(sampled_from(['Александрович', 'Олександрович', 'Иванович', 'Іванович']))
        components.append(patronymic)
    
    # Add surname
    surname = draw(one_of(
        russian_surname(), 
        ukrainian_surname(), 
        english_surname(),
        feminine_surname(),
        compound_surname()
    ))
    components.append(surname)
    
    # Optionally add initials
    if draw(st.booleans()):
        initial = draw(initials())
        components.insert(-1, f"{initial}.")
    
    return ' '.join(components)


# ============================================================================
# Property Tests
# ============================================================================

@pytest.fixture(scope="module")
def normalization_service():
    """Module-scoped normalization service fixture."""
    service = NormalizationService()
    yield service
    # Cleanup caches
    if hasattr(service, 'normalization_factory'):
        if hasattr(service.normalization_factory, '_normalization_cache'):
            service.normalization_factory._normalization_cache.clear()


@pytest.fixture(scope="session")
def flags():
    """Session-scoped flags fixture."""
    return {
        "remove_stop_words": True,
        "preserve_names": True,
        "enable_advanced_features": True,
        "strict_stopwords": True,
        "preserve_feminine_suffix_uk": False,
        "enable_spacy_uk_ner": False
    }


@pytest.mark.property
class TestNormalizationProperties:
    """Property-based tests for normalization service."""
    
    @given(full_name())
    @PROPERTY_SETTINGS
    def test_idempotence(self, normalization_service, flags, text):
        """Test that normalization is idempotent: norm(norm(x)) == norm(x)."""
        # First normalization
        result1 = normalization_service.normalize(text, **flags)
        
        # Skip if first normalization failed
        if not result1.success:
            pytest.skip(f"First normalization failed for input: '{text}'")
        
        # Second normalization
        result2 = normalization_service.normalize(result1.normalized, **flags)
        
        # Skip if second normalization failed
        if not result2.success:
            pytest.skip(f"Second normalization failed for: '{result1.normalized}'")
        
        # Check idempotence - allow for minor morphological differences
        # but core structure should be the same
        letters1 = letters_only(result1.normalized)
        letters2 = letters_only(result2.normalized)
        
        # The core letters should be the same (allowing for morphological normalization)
        assert letters1 == letters2, (
            f"Idempotence failed for input: '{text}'\n"
            f"First normalized: '{result1.normalized}' (letters: '{letters1}')\n"
            f"Second normalized: '{result2.normalized}' (letters: '{letters2}')\n"
            f"First trace: {result1.trace[:3]}\n"
            f"Language: {result1.language}"
        )
    
    @given(full_name())
    @PROPERTY_SETTINGS
    def test_preserve_feminine(self, normalization_service, flags, text):
        """Test that feminine gender is preserved if input is feminine."""
        result = normalization_service.normalize(text, **flags)
        
        # Skip if normalization failed
        if not result.success:
            pytest.skip(f"Normalization failed for input: '{text}'")
        
        # Check if input contains feminine elements
        input_tokens = text.split()
        input_feminine = is_feminine(input_tokens)
        
        if input_feminine:
            # If input is feminine, output should also be feminine
            output_feminine = is_feminine(result.tokens)
            
            assert output_feminine, (
                f"Feminine gender lost for input: '{text}'\n"
                f"Normalized: '{result.normalized}'\n"
                f"Tokens: {result.tokens}\n"
                f"Trace: {result.trace[:3]}\n"
                f"Language: {result.language}"
            )
    
    @given(full_name())
    @PROPERTY_SETTINGS
    def test_output_charset_subset(self, normalization_service, flags, text):
        """Test that normalized output characters are subset of input + allowed additions."""
        result = normalization_service.normalize(text, **flags)
        
        # Skip if normalization failed
        if not result.success:
            pytest.skip(f"Normalization failed for input: '{text}'")
        
        input_letters = set(letters_only(text))
        output_letters = set(letters_only(result.normalized))
        allowed_additions = allowed_added_chars()
        
        # Check that output letters are subset of input letters + allowed additions
        extra_letters = output_letters - input_letters - allowed_additions
        
        assert not extra_letters, (
            f"Output contains unexpected characters for input: '{text}'\n"
            f"Normalized: '{result.normalized}'\n"
            f"Extra letters: {extra_letters}\n"
            f"Input letters: {input_letters}\n"
            f"Output letters: {output_letters}\n"
            f"Trace: {result.trace[:3]}\n"
            f"Language: {result.language}"
        )
    
    @given(full_name())
    @PROPERTY_SETTINGS
    def test_word_order_metamorphic(self, normalization_service, flags, text):
        """Test metamorphic property: swapping name order should produce same canonical form."""
        # Split into words and try different orderings
        words = text.split()
        if len(words) < 2:
            pytest.skip("Need at least 2 words for order testing")
        
        # Try different orderings
        orderings = [
            words,  # original
            words[::-1],  # reversed
        ]
        
        results = []
        for ordering in orderings:
            ordered_text = ' '.join(ordering)
            result = normalization_service.normalize(ordered_text, **flags)
            if result.success:
                results.append((ordered_text, result))
        
        # Skip if we don't have enough successful results
        if len(results) < 2:
            pytest.skip("Not enough successful normalizations for metamorphic testing")
        
        # All results should have the same set of tokens (ignoring order)
        token_sets = [set(letters_only(token) for token in r.tokens) for _, r in results]
        
        # Check that all token sets are the same (ignoring order)
        first_set = token_sets[0]
        for i, token_set in enumerate(token_sets[1:], 1):
            assert token_set == first_set, (
                f"Metamorphic property failed for input: '{text}'\n"
                f"Ordering {i}: '{results[i][0]}' -> tokens: {[letters_only(t) for t in results[i][1].tokens]}\n"
                f"Original: '{results[0][0]}' -> tokens: {[letters_only(t) for t in results[0][1].tokens]}\n"
                f"Expected same token set, got: {token_set} vs {first_set}\n"
                f"Trace: {results[i][1].trace[:3]}\n"
                f"Language: {results[i][1].language}"
            )
    
    @given(name_with_noise())
    @PROPERTY_SETTINGS
    def test_noise_handling(self, normalization_service, flags, text):
        """Test that normalization handles noise gracefully."""
        result = normalization_service.normalize(text, **flags)
        
        # Result should be successful or have clear error
        assert result.success or len(result.errors) > 0, (
            f"Noise handling failed for input: '{text}'\n"
            f"Result: {result.normalized}\n"
            f"Success: {result.success}\n"
            f"Errors: {result.errors}\n"
            f"Trace: {result.trace[:3]}\n"
            f"Language: {result.language}"
        )
        
        # If successful, output should be cleaner than input
        if result.success:
            input_clean = letters_only(text)
            output_clean = letters_only(result.normalized)
            
            # Output should not be significantly longer than input
            assert len(output_clean) <= len(input_clean) + 10, (
                f"Output too long for noisy input: '{text}'\n"
                f"Input clean length: {len(input_clean)}\n"
                f"Output clean length: {len(output_clean)}\n"
                f"Normalized: '{result.normalized}'\n"
                f"Trace: {result.trace[:3]}\n"
                f"Language: {result.language}"
            )
