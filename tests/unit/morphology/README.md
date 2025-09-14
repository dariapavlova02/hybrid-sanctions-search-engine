# Morphology Tests

This directory contains unit tests for morphological analysis services for Ukrainian, Russian, and other languages.

## Test Files

- `test_russian_morphology_service.py` - Russian morphological analysis
- `test_russian_morphology_unit.py` - Russian morphology unit tests
- `test_ukrainian_morphology_unit.py` - Ukrainian morphology unit tests
- `test_ukrainian_morphology.py` - Ukrainian morphological analysis
- `test_morph_and_diminutives.py` - Morphological variants and diminutives
- `test_integration_morphology.py` - Morphology integration tests

## Test Categories

### Russian Morphology
- pymorphy3 integration
- Case declension
- Gender detection
- Lemmatization accuracy

### Ukrainian Morphology
- Ukrainian-specific rules
- Character handling (і, ї, є, ґ)
- Morphological analysis
- Dictionary integration

### Morphological Variants
- Diminutive forms
- Nickname mapping
- Gender agreement
- Cross-language variants

## Running Tests

```bash
# Run all morphology tests
pytest tests/unit/morphology/ -v

# Run specific language tests
pytest tests/unit/morphology/test_russian_morphology_service.py -v
pytest tests/unit/morphology/test_ukrainian_morphology.py -v
```
