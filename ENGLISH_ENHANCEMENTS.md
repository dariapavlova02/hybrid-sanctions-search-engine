# English Normalization Enhancements

This document describes the English normalization enhancements implemented in the AI service, focusing on structured name parsing, nickname expansion, and improved handling of English-specific features.

## Overview

The English normalization enhancements provide:

1. **Structured Name Parsing**: Using `nameparser` library for accurate parsing of English names
2. **Nickname Expansion**: Converting common nicknames to full forms (Bill → William)
3. **Surname Particle Handling**: Proper handling of particles like "van der", "de la", etc.
4. **Punctuation Preservation**: Maintaining apostrophes and hyphens in names
5. **Optional NER Integration**: Using spaCy for enhanced entity recognition

## Features

### 1. Nameparser Integration

The `NameparserAdapter` provides a standardized interface to the `nameparser` library for parsing English names into structured components.

**Key Components:**
- `first`: First name
- `middles`: List of middle names
- `last`: Last name (including particles)
- `suffix`: Suffixes like "Jr.", "Sr.", "III"
- `nickname`: Original nickname if detected
- `particles`: Surname particles like "van", "de", "von"
- `confidence`: Parsing confidence score

**Example:**
```python
from src.ai_service.layers.normalization.nameparser_adapter import get_nameparser_adapter

nameparser = get_nameparser_adapter()
parsed = nameparser.parse_en_name("Dr. Bill J. de la Cruz Jr.")

# Results:
# first: "william" (expanded from Bill)
# middles: ["J."]
# last: "de la Cruz"
# suffix: "Jr."
# nickname: "Bill"
# particles: ["de", "la"]
# confidence: 0.85
```

### 2. Nickname Expansion

The system includes a comprehensive dictionary of English nicknames and their full forms.

**Supported Nicknames:**
- Male: Bill → William, Bob → Robert, Jim → James, Mike → Michael, etc.
- Female: Beth → Elizabeth, Liz → Elizabeth, Katie → Katherine, etc.

**Configuration:**
- `enable_en_nickname_expansion=True` (default)
- Dictionary: `data/lexicons/en_nicknames.json`

**Example:**
```python
expanded, was_expanded = nameparser.expand_nickname("Bill")
# Result: expanded="william", was_expanded=True
```

### 3. Surname Particle Handling

Proper handling of surname particles to maintain cultural naming conventions.

**Supported Particles:**
- Dutch: van, van der, van den, van de
- French: de, de la, du, des, d', l'
- German: von, von der
- Italian: di, da, del, della
- Spanish: de, de la, de los, de las, el, los, las

**Configuration:**
- Dictionary: `data/lexicons/en_surname_particles.txt`
- Particles are preserved in the last name component

**Example:**
```python
parsed = nameparser.parse_en_name("John van der Berg")
# Result: last="van der Berg", particles=["van", "der"]
```

### 4. Punctuation Preservation

Careful handling of apostrophes and hyphens in English names.

**Features:**
- Apostrophes preserved: O'Connor, D'Angelo, O'Brien
- Hyphens preserved: Anne-Marie, Jean-Pierre, Mary-Jane
- Title case applied while preserving punctuation

**Example:**
```python
result = nameparser._title_case_with_punctuation("o'connor")
# Result: "O'Connor"
```

### 5. Optional NER Integration

Integration with spaCy's English NER model for enhanced entity recognition.

**Features:**
- Person entity detection
- Organization entity detection
- Suppression of organization names from person output
- Enhanced confidence for person candidates

**Configuration:**
- `enable_spacy_en_ner=False` (default, requires spaCy installation)
- Model: `en_core_web_sm`

**Example:**
```python
from src.ai_service.layers.normalization.ner_gateways.spacy_en import get_spacy_en_ner

ner = get_spacy_en_ner()
hints = ner.extract_entities("Apple Inc. CEO Tim Cook")
# Result: person_spans=[(15, 23)], org_spans=[(0, 9)]
```

## Configuration Flags

### English-Specific Flags

| Flag | Default | Description |
|------|---------|-------------|
| `en_use_nameparser` | `True` | Use nameparser for English names |
| `enable_en_nickname_expansion` | `True` | Expand English nicknames |
| `enable_spacy_en_ner` | `False` | Enable spaCy English NER |

### Usage

```python
from src.ai_service.layers.normalization.normalization_service import NormalizationService

service = NormalizationService()

result = await service.normalize_async(
    "Dr. Bill J. de la Cruz Jr.",
    language='en',
    en_use_nameparser=True,
    enable_en_nickname_expansion=True,
    enable_spacy_en_ner=False
)
```

## File Structure

```
src/ai_service/layers/normalization/
├── nameparser_adapter.py          # Nameparser integration
├── ner_gateways/
│   ├── spacy_en.py               # English NER gateway
│   └── __init__.py               # NER gateways exports
└── processors/
    └── normalization_factory.py  # Updated factory with EN support

data/lexicons/
├── en_nicknames.json             # English nickname dictionary
└── en_surname_particles.txt      # Surname particles dictionary

tests/lang/en/
├── test_nameparser_basic.py      # Nameparser tests
├── test_nicknames.py             # Nickname expansion tests
├── test_apostrophes_hyphens.py   # Punctuation tests
└── test_ner_optional.py          # NER tests (optional)
```

## Testing

### Running Tests

```bash
# Run all English tests
pytest tests/lang/en/ -v

# Run specific test categories
pytest tests/lang/en/test_nameparser_basic.py -v
pytest tests/lang/en/test_nicknames.py -v
pytest tests/lang/en/test_apostrophes_hyphens.py -v
pytest tests/lang/en/test_ner_optional.py -v
```

### Test Coverage

- **Nameparser Tests**: Basic parsing, complex names, edge cases
- **Nickname Tests**: Expansion, case insensitivity, non-nicknames
- **Punctuation Tests**: Apostrophes, hyphens, title case
- **NER Tests**: Entity detection, role tagging, confidence enhancement

## Dependencies

### Required
- `nameparser`: For structured name parsing
- `pytest`: For testing

### Optional
- `spacy`: For NER functionality
- `en_core_web_sm`: spaCy English model

### Installation

```bash
# Required dependencies
pip install nameparser pytest

# Optional NER dependencies
pip install spacy
python -m spacy download en_core_web_sm
```

## Performance Considerations

### Caching
- Nameparser adapter uses singleton pattern
- NER gateway uses singleton pattern
- Lexicon loading is cached

### Performance Impact
- Nameparser adds ~5-10ms per name
- NER adds ~50-100ms per text (when enabled)
- Nickname expansion is O(1) dictionary lookup

### Recommendations
- Enable nameparser for better accuracy
- Enable NER only when high accuracy is required
- Use caching for production workloads

## Error Handling

### Graceful Degradation
- Falls back to default classification if nameparser fails
- Continues without NER if spaCy is unavailable
- Handles malformed input gracefully

### Logging
- Warnings for failed nameparser parsing
- Errors for critical failures
- Debug information for troubleshooting

## Examples

### Basic Usage

```python
from src.ai_service.layers.normalization.normalization_service import NormalizationService

service = NormalizationService()

# Simple name
result = await service.normalize_async("John Smith", language='en')
print(result.normalized)  # "John Smith"

# Complex name with nickname
result = await service.normalize_async("Bill Smith", language='en')
print(result.normalized)  # "William Smith"

# Name with particles
result = await service.normalize_async("John van der Berg", language='en')
print(result.normalized)  # "John van der Berg"
```

### Advanced Usage

```python
# With all features enabled
result = await service.normalize_async(
    "Dr. Bill J. de la Cruz Jr.",
    language='en',
    en_use_nameparser=True,
    enable_en_nickname_expansion=True,
    enable_spacy_en_ner=True
)

print(result.normalized)  # "Dr. William J. de la Cruz Jr."
print(result.tokens)      # ["William", "J.", "de la Cruz", "Jr."]
```

## Migration Guide

### From Legacy English Normalization

1. **Enable nameparser**: Set `en_use_nameparser=True`
2. **Enable nickname expansion**: Set `enable_en_nickname_expansion=True`
3. **Update tests**: Use new test structure in `tests/lang/en/`
4. **Optional NER**: Enable `enable_spacy_en_ner=True` if needed

### Backward Compatibility

- All existing functionality is preserved
- New features are opt-in via configuration flags
- Default behavior maintains backward compatibility

## Troubleshooting

### Common Issues

1. **Nameparser not working**: Check if `nameparser` is installed
2. **Nicknames not expanding**: Verify `en_nicknames.json` is loaded
3. **NER not available**: Install spaCy and download English model
4. **Particles not detected**: Check `en_surname_particles.txt` format

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug tracing in normalization
result = await service.normalize_async(
    "Bill Smith",
    language='en',
    debug_tracing=True
)
```

## Future Enhancements

### Planned Features
- Support for more nickname variations
- Additional surname particle patterns
- Integration with other NER models
- Performance optimizations

### Contributing
- Add new nicknames to `en_nicknames.json`
- Add new particles to `en_surname_particles.txt`
- Extend test coverage
- Improve error handling

## Conclusion

The English normalization enhancements provide a robust, accurate, and flexible system for processing English names. The modular design allows for easy customization and extension while maintaining backward compatibility and performance.
