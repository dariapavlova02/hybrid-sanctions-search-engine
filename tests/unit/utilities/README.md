# Utilities Tests

This directory contains unit tests for utility services including caching, templates, patterns, and helper functions.

## Test Files

- `test_cache_service.py` - Caching service functionality
- `test_template_builder.py` - Template building service
- `test_enhanced_template_builder.py` - Enhanced template features
- `test_pattern_service.py` - Pattern matching service
- `test_final_ac_optimizer.py` - Aho-Corasick pattern optimization
- `test_optimized_ac_pattern_generator.py` - Pattern generation
- `test_vector_processing.py` - Vector processing utilities
- `test_build_templates_script.py` - Template building scripts
- `test_run_service_script.py` - Service runner scripts
- `test_canary_overfit.py` - Overfitting detection tests
- `test_edge_cases_comprehensive.py` - Edge case handling
- `test_flags_ab_strict.py` - A/B testing flag validation
- `test_input_validation.py` - Input validation utilities
- `test_name_dictionaries_validation.py` - Dictionary validation

## Test Categories

### Caching
- Cache hit/miss behavior
- TTL management
- Memory usage
- Performance optimization

### Template Building
- Template generation
- Pattern optimization
- Aho-Corasick integration
- Performance metrics

### Pattern Matching
- Pattern compilation
- Search optimization
- Memory efficiency
- Accuracy validation

### Utilities
- Input validation
- Dictionary validation
- Edge case handling
- Script functionality

## Running Tests

```bash
# Run all utility tests
pytest tests/unit/utilities/ -v

# Run specific utility tests
pytest tests/unit/utilities/test_cache_service.py -v
pytest tests/unit/utilities/test_template_builder.py -v
```
