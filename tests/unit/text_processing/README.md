# Text Processing Tests

This directory contains unit tests for text processing services including language detection, normalization, and variant generation.

## Test Files

- `test_language_detection_service.py` - Language detection and classification
- `test_unicode_service.py` - Unicode normalization and character handling
- `test_normalization_service.py` - Text normalization for search
- `test_normalization_logic.py` - Core normalization algorithms
- `test_normalization_result_fields.py` - Normalization result data structures
- `test_flags_behavior.py` - Configuration flags and behavior testing
- `test_role_tagging_extended.py` - Role-based text tagging
- `test_org_acronyms_filter.py` - Organization acronym filtering
- `test_variant_generation_service.py` - Text variant generation
- `test_advanced_normalization_service.py` - Advanced normalization features
- `test_advanced_normalization_unit.py` - Advanced normalization unit tests

## Test Categories

### Language Detection
- Multi-language text detection
- Confidence scoring
- Fallback mechanisms
- Performance optimization

### Text Normalization
- Unicode normalization
- Case handling
- Special character processing
- Language-specific rules

### Variant Generation
- Morphological variants
- Transliteration variants
- Phonetic variants
- Context-aware generation

## Running Tests

```bash
# Run all text processing tests
pytest tests/unit/text_processing/ -v

# Run specific category
pytest tests/unit/text_processing/test_language_detection_service.py -v
pytest tests/unit/text_processing/test_normalization_service.py -v
```
