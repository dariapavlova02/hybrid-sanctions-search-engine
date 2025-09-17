# Ukrainian Normalization Enhancements

This document describes the new Ukrainian-specific enhancements added to the AI normalization service.

## Overview

The enhancements include three new flags specifically designed to improve Ukrainian text normalization:

1. **`strict_stopwords`** - Prevents Ukrainian prepositions and conjunctions from being tagged as initials
2. **`preserve_feminine_suffix_uk`** - Preserves Ukrainian feminine surname suffixes (-ська/-цька) in nominative case
3. **`enable_spacy_uk_ner`** - Enables spaCy Ukrainian NER for improved entity recognition

## Features

### 1. Strict Stopwords Filtering (`strict_stopwords=True`)

**Problem**: Ukrainian prepositions and conjunctions like "з", "та", "і" can be confused with initials, leading to incorrect role tagging.

**Solution**: When `strict_stopwords=True`, these words are never tagged as initials or name roles.

**Example**:
```python
# Without strict_stopwords
text = "Переказ з картки О. Петренко"
# "з" might be tagged as initial

# With strict_stopwords=True  
text = "Переказ з картки О. Петренко"
# "з" is tagged as stopword with reason="uk_stopword_conflict"
# "О." is correctly tagged as initial
```

**Supported words**:
- Prepositions: з, зі, у, в, до, за, над, під, при, по, о, об, без, для, між
- Conjunctions: та, і, й, або, чи

### 2. Feminine Suffix Preservation (`preserve_feminine_suffix_uk=True`)

**Problem**: Ukrainian feminine surnames with suffixes like -ська/-цька were being converted to masculine forms.

**Solution**: When `preserve_feminine_suffix_uk=True`, feminine suffixes are preserved in nominative case.

**Example**:
```python
# Without preserve_feminine_suffix_uk
"Ковальської" → "Ковальська"  # Genitive to nominative, feminine preserved

# With preserve_feminine_suffix_uk=True
"Ковальської" → "Ковальська"  # Same result, but with explicit feminine preservation
```

**Supported patterns**:
- -ська/-ської/-ською/-ській/-ську → -ська (nominative)
- -цька/-цької/-цькою/-цькій/-цьку → -цька (nominative)
- -ова/-ової/-овою/-овій/-ову → -ова (nominative)
- -ева/-евої/-евою/-евій/-еву → -ева (nominative)

### 3. spaCy Ukrainian NER (`enable_spacy_uk_ner=True`)

**Problem**: Basic role tagging can misclassify organizations as person names.

**Solution**: When `enable_spacy_uk_ner=True`, spaCy's Ukrainian NER model provides hints to improve role tagging.

**Example**:
```python
# Without NER
text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
# "ПРИВАТБАНК" might be tagged as person

# With NER
text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"  
# "ПРИВАТБАНК" is correctly tagged as organization
# "Анна Ковальська" is correctly tagged as person
```

**Requirements**:
```bash
pip install spacy
python -m spacy download uk_core_news_sm
```

## Usage

### Basic Usage

```python
from src.ai_service.layers.normalization.normalization_service import NormalizationService

service = NormalizationService()

# Enable all Ukrainian enhancements
result = await service.normalize_async(
    "Переказ з картки О. Петренко",
    language="uk",
    strict_stopwords=True,
    preserve_feminine_suffix_uk=True,
    enable_spacy_uk_ner=True
)
```

### Individual Flags

```python
# Only strict stopwords
result = await service.normalize_async(
    "Переказ з картки О. Петренко",
    language="uk",
    strict_stopwords=True
)

# Only feminine suffix preservation
result = await service.normalize_async(
    "Анна Ковальської",
    language="uk", 
    preserve_feminine_suffix_uk=True
)

# Only NER (if spaCy is available)
result = await service.normalize_async(
    "Анна Ковальська працює в ТОВ ПРИВАТБАНК",
    language="uk",
    enable_spacy_uk_ner=True
)
```

## Configuration

### NormalizationConfig

```python
from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationConfig

config = NormalizationConfig(
    language="uk",
    strict_stopwords=True,
    preserve_feminine_suffix_uk=True,
    enable_spacy_uk_ner=True
)
```

### Feature Flags

The flags can also be controlled via feature flags:

```python
# In your configuration
{
    "ukrainian_enhancements": {
        "strict_stopwords": True,
        "preserve_feminine_suffix_uk": True,
        "enable_spacy_uk_ner": True
    }
}
```

## Testing

### Run Tests

```bash
# Test stopwords vs initials
pytest tests/lang/uk/test_stopwords_initials.py -v

# Test feminine suffix preservation  
pytest tests/lang/uk/test_feminine_suffix.py -v

# Test NER functionality (requires spaCy)
pytest tests/lang/uk/test_ner_optional.py -v
```

### Demo Script

```bash
python demo_ukrainian_enhancements.py
```

## Implementation Details

### Files Modified

1. **`lexicon_loader.py`** - Added support for `stopwords_init` lexicons
2. **`role_tagger.py`** - Added `strict_stopwords` and NER hint support
3. **`gender_rules.py`** - Added `preserve_feminine_suffix_uk` parameter
4. **`morphology_processor.py`** - Added feminine suffix preservation
5. **`normalization_factory.py`** - Integrated all new flags
6. **`normalization_service.py`** - Exposed new flags in API

### Files Added

1. **`ner_gateways/spacy_uk.py`** - spaCy Ukrainian NER gateway
2. **`data/lexicons/uk_stopwords_init.txt`** - Ukrainian stopwords that conflict with initials
3. **`tests/lang/uk/`** - Ukrainian-specific tests

## Performance Considerations

- **`strict_stopwords`**: Minimal performance impact, just additional lexicon lookup
- **`preserve_feminine_suffix_uk`**: Minimal performance impact, additional pattern matching
- **`enable_spacy_uk_ner`**: Higher performance impact, requires spaCy model loading and processing

## Error Handling

- If spaCy is not available, NER functionality gracefully degrades
- If Ukrainian model is not installed, NER returns empty hints
- All flags are backward compatible and default to `False`

## Future Enhancements

1. Support for more Ukrainian feminine patterns
2. Additional NER models (e.g., Ukrainian BERT-based)
3. Integration with other Slavic languages
4. Performance optimizations for NER processing
