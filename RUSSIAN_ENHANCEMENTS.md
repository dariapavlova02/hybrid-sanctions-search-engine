# Russian Normalization Enhancements

This document describes the Russian-specific enhancements added to the AI service normalization system.

## Overview

The Russian normalization enhancements provide specialized handling for Russian text, including:

1. **Stopwords for Initials Conflict Prevention** - Prevents Russian prepositions and conjunctions from being incorrectly marked as initials
2. **'ё' Policy** - Configurable handling of the Russian letter 'ё' (preserve or fold to 'е')
3. **Enhanced Patronymics** - Improved detection and normalization of patronymics to nominative case
4. **Expanded Nicknames** - Extended dictionary of Russian diminutives and nicknames
5. **Hyphenated Surnames** - Proper handling of hyphenated surnames like "Петрова-Сидорова"
6. **Optional Russian NER** - Integration with spaCy's Russian NER model for entity recognition

## Features

### 1. Stopwords for Initials Conflict Prevention

**Problem**: Russian prepositions and conjunctions like "с", "и", "на" were being incorrectly marked as initials in contexts like "перевод с карты И. Иванов".

**Solution**: Created `data/lexicons/ru_stopwords_init.txt` with Russian prepositions and conjunctions that should never be marked as initials.

**Usage**:
```python
result = await service.normalize_async(
    "перевод с карты И. Иванов",
    language="ru",
    strict_stopwords=True  # Enable stopwords filtering
)
```

**Configuration**:
- `strict_stopwords=True` - Enables stopwords filtering for initials conflict prevention
- `strict_stopwords=False` - Disables stopwords filtering (default behavior)

### 2. 'ё' Policy

**Problem**: Need to handle the Russian letter 'ё' consistently - either preserve it or convert it to 'е'.

**Solution**: Implemented configurable 'ё' strategy with tracing.

**Usage**:
```python
# Preserve 'ё' characters
result = await service.normalize_async(
    "Семён Петров",
    language="ru",
    ru_yo_strategy="preserve"  # Keep 'ё' as 'ё'
)

# Convert 'ё' to 'е'
result = await service.normalize_async(
    "Семён Петров",
    language="ru",
    ru_yo_strategy="fold"  # Convert 'ё' to 'е'
)
```

**Configuration**:
- `ru_yo_strategy="preserve"` - Keep 'ё' characters (default)
- `ru_yo_strategy="fold"` - Convert 'ё' to 'е'

**Tracing**: All 'ё' conversions are traced with detailed information about the transformation.

### 3. Enhanced Patronymics

**Problem**: Patronymics in oblique cases (genitive, dative, etc.) were not being normalized to nominative case.

**Solution**: Enhanced patronymic detection patterns and normalization to always return nominative case.

**Features**:
- Comprehensive patronymic suffix patterns for all cases
- Automatic normalization to nominative case
- Special handling for ambiguous "-ович" endings (Belarusian surnames)
- Rule-based fallback for morphological analysis

**Usage**:
```python
# Patronymics are automatically detected and normalized
result = await service.normalize_async(
    "Иван Петровича Сидоров",  # Genitive patronymic
    language="ru"
)
# Result: "Иван Петрович Сидоров" (nominative)
```

**Supported Patterns**:
- Masculine: ович, евич, йович, ич + all case forms
- Feminine: овна, евна, ична + all case forms
- Genitive, dative, instrumental, vocative forms

### 4. Expanded Russian Nicknames

**Problem**: Limited coverage of Russian diminutives and nicknames.

**Solution**: Expanded `data/diminutives_ru.json` with comprehensive Russian nicknames.

**New Additions**:
- Вова → Владимир
- Саша → Александр
- Коля → Николай
- Лёша → Алексей
- Дима → Дмитрий
- Миша → Михаил
- Женя → Евгений/Евгения (gender-dependent)

**Usage**:
```python
result = await service.normalize_async(
    "Вова Петров",
    language="ru",
    enable_ru_nickname_expansion=True
)
# Result: "Владимир Петров"
```

**Configuration**:
- `enable_ru_nickname_expansion=True` - Enable nickname expansion (default)
- `enable_ru_nickname_expansion=False` - Disable nickname expansion

### 5. Hyphenated Surnames

**Problem**: Hyphenated surnames like "Петрова-Сидорова" needed proper handling and normalization.

**Solution**: Enhanced hyphenated name processing with feminine form preservation.

**Features**:
- Proper segmentation by single hyphens only
- Title case normalization for each segment
- Preservation of feminine forms
- Support for apostrophes and special characters
- Validation of name segments

**Usage**:
```python
# Hyphenated surnames are automatically normalized
result = await service.normalize_async(
    "Анна Петрова-Сидорова",
    language="ru"
)
# Result: "Анна Петрова-Сидорова" (properly capitalized)
```

**Supported Patterns**:
- Петрова-Сидорова (feminine-feminine)
- Петров-Сидоров (masculine-masculine)
- O'Neil-Smith (with apostrophes)
- Multiple hyphens: Петрова-Сидорова-Иванова

### 6. Optional Russian NER

**Problem**: Need for Named Entity Recognition to improve role tagging accuracy.

**Solution**: Integration with spaCy's Russian NER model (`ru_core_news_sm`).

**Features**:
- Person entity detection (PER)
- Organization entity detection (ORG)
- Integration with role tagging
- Graceful fallback when model is unavailable

**Usage**:
```python
result = await service.normalize_async(
    "Иван Петров работает в ООО Рога и копыта",
    language="ru",
    enable_spacy_ru_ner=True
)
```

**Installation**:
```bash
python -m spacy download ru_core_news_sm
```

**Configuration**:
- `enable_spacy_ru_ner=True` - Enable Russian NER
- `enable_spacy_ru_ner=False` - Disable Russian NER (default)

## API Reference

### New Service Parameters

```python
async def normalize_async(
    self,
    text: str,
    *,
    language: Optional[str] = None,
    # ... existing parameters ...
    
    # Russian-specific flags
    ru_yo_strategy: str = "preserve",  # 'preserve' or 'fold'
    enable_ru_nickname_expansion: bool = True,
    enable_spacy_ru_ner: bool = False,
) -> NormalizationResult:
```

### New Configuration Options

```python
@dataclass
class NormalizationConfig:
    # ... existing fields ...
    
    # Russian-specific flags
    ru_yo_strategy: str = "preserve"  # Russian 'ё' policy
    enable_ru_nickname_expansion: bool = True  # Expand Russian nicknames
    enable_spacy_ru_ner: bool = False  # Enable spaCy Russian NER
```

## Testing

Comprehensive tests are provided for all Russian features:

- `tests/lang/ru/test_stopwords_initials.py` - Stopwords conflict prevention
- `tests/lang/ru/test_yo_policy.py` - 'ё' policy handling
- `tests/lang/ru/test_patronymics.py` - Patronymic detection and normalization
- `tests/lang/ru/test_nicknames.py` - Nickname expansion
- `tests/lang/ru/test_hyphen_surnames.py` - Hyphenated surname handling
- `tests/lang/ru/test_ner_optional.py` - Russian NER functionality

Run tests:
```bash
pytest tests/lang/ru/ -v
```

## Demo

A comprehensive demo script is provided:

```bash
python demo_russian_enhancements.py
```

The demo showcases all Russian features with examples and explanations.

## Performance Considerations

- **Caching**: All Russian features use appropriate caching for performance
- **Lazy Loading**: NER models are loaded only when needed
- **Fallback**: Graceful degradation when optional dependencies are unavailable
- **Tracing**: Detailed tracing for debugging and monitoring

## Dependencies

### Required
- `pymorphy3` - For morphological analysis
- `unicodedata` - For Unicode normalization

### Optional
- `spacy` + `ru_core_news_sm` - For Russian NER
- `nameparser` - For English name parsing (if using mixed language)

## Migration Guide

### From Previous Version

1. **Update Service Calls**: Add new Russian-specific parameters to `normalize_async` calls
2. **Update Configuration**: Add Russian flags to `NormalizationConfig` if using directly
3. **Install Dependencies**: Install `ru_core_news_sm` if using Russian NER
4. **Update Tests**: Update existing tests to use new parameters

### Example Migration

```python
# Before
result = await service.normalize_async(
    "Семён Петрович Иванов",
    language="ru"
)

# After
result = await service.normalize_async(
    "Семён Петрович Иванов",
    language="ru",
    strict_stopwords=True,
    ru_yo_strategy="fold",
    enable_ru_nickname_expansion=True,
    enable_spacy_ru_ner=False
)
```

## Troubleshooting

### Common Issues

1. **'ё' not being converted**: Check `ru_yo_strategy` parameter
2. **Patronymics not normalized**: Ensure `enable_advanced_features=True`
3. **Nicknames not expanded**: Check `enable_ru_nickname_expansion=True`
4. **NER not working**: Install `ru_core_news_sm` model
5. **Stopwords not filtered**: Enable `strict_stopwords=True`

### Debug Mode

Enable detailed tracing:

```python
result = await service.normalize_async(
    text,
    language="ru",
    debug_tracing=True
)

# Check traces
for trace in result.trace:
    print(f"{trace.token} -> {trace.role} ({trace.rule})")
```

## Future Enhancements

Potential future improvements:

1. **Gender Detection**: Enhanced gender detection for ambiguous names
2. **Regional Variants**: Support for regional Russian name variants
3. **Historical Names**: Support for historical Russian naming conventions
4. **Performance**: Further optimization for large-scale processing
5. **Accuracy**: Machine learning-based improvements for edge cases

## Contributing

When contributing to Russian features:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure backward compatibility
5. Test with real-world Russian text samples

## License

This enhancement is part of the AI service normalization system and follows the same license terms.
