# Normalization Tokenizer Improvements

This document describes the tokenizer improvements implemented in the normalization system for handling initials and hyphenated names.

## Overview

The tokenizer improvements address two specific issues commonly found in name normalization:

1. **Double Dots in Initials**: Collapsing multiple dots after initials (И.. → И.)
2. **Hyphenated Names**: Proper case normalization for hyphenated surnames (петрова-сидорова → Петрова-Сидорова)

These improvements are controlled by feature flags and can be enabled/disabled without affecting legacy behavior.

## Feature Flags

### Environment Variables

- `FIX_INITIALS_DOUBLE_DOT`: Enable double dot collapse (default: false)
- `PRESERVE_HYPHENATED_CASE`: Enable hyphenated name case normalization (default: false)

### Configuration

```python
from src.ai_service.utils.feature_flags import get_feature_flag_manager

flags = get_feature_flag_manager()
print(f"Double dot fix: {flags._flags.fix_initials_double_dot}")
print(f"Hyphenated case: {flags._flags.preserve_hyphenated_case}")
```

## Initial Double Dot Collapse

### Problem

Text containing initials often has inconsistent punctuation:
- `И.. Петров` (double dots)
- `И. Петров` (correct single dot)

### Solution

The `collapse_double_dots` function normalizes initials by removing extra dots.

### Rules

1. **Collapse**: Single letter + multiple dots → Single letter + one dot
   - `И..` → `И.`
   - `О..` → `О.`
   - `J..` → `J.`

2. **Preserve Ellipsis**: Three dots remain unchanged
   - `...` → `...` (preserved)

3. **Preserve Abbreviations**: Internal dots in abbreviations
   - `и.о.` → `и.о.` (preserved)
   - `т.о.` → `т.о.` (preserved)

### Examples

```python
from src.ai_service.layers.normalization.token_ops import collapse_double_dots

# Basic collapse
assert collapse_double_dots(["И..", "И."]) == ["И.", "И."]
assert collapse_double_dots(["J..", "R.."]) == ["J.", "R."]

# Preserved cases
assert collapse_double_dots(["..."]) == ["..."]         # ellipsis
assert collapse_double_dots(["и.о."]) == ["и.о."]       # abbreviation
```

### Language Support

- **Russian**: И, О, А, etc.
- **Ukrainian**: І, О, У, etc.
- **English**: J, R, M, etc.
- **Unicode**: All Unicode letters supported

## Hyphenated Name Normalization

### Problem

Hyphenated surnames often have inconsistent capitalization:
- `петрова-сидорова` (lowercase)
- `ИВАНОВ-ПЕТРОВ` (uppercase)
- `o'neil-smith` (mixed case)

### Solution

The `normalize_hyphenated_name` function provides proper title case for hyphenated names.

### Rules

1. **Split by Hyphen**: Only single hyphens (`-`)
   - Preserve em-dashes (`—`) and double hyphens (`--`)

2. **Validate Segments**: Each segment must contain only:
   - Unicode letters (`\p{L}`)
   - Allowed apostrophes (`'`, `'`, `` ` ``)
   - No dots, numbers, or other punctuation

3. **Title Case**: When `titlecase=True`
   - Capitalize first letter of each segment
   - Preserve case of remaining letters

### Examples

```python
from src.ai_service.layers.normalization.token_ops import normalize_hyphenated_name

# Russian names
assert normalize_hyphenated_name("петрова-сидорова", titlecase=True) == "Петрова-Сидорова"
assert normalize_hyphenated_name("ИВАНОВ-ПЕТРОВ", titlecase=True) == "Иванов-Петров"

# English names with apostrophes
assert normalize_hyphenated_name("o'neil-smith", titlecase=True) == "O'Neil-Smith"

# Preserved cases
assert normalize_hyphenated_name("test—dash", titlecase=True) == "test—dash"    # em-dash
assert normalize_hyphenated_name("test--dash", titlecase=True) == "test--dash"  # double hyphen
```

### Language Support

- **Russian**: Full Cyrillic support
- **Ukrainian**: Full Cyrillic support
- **English**: Latin letters + apostrophes
- **Unicode**: All Unicode letter categories

## Integration

### Processing Flow

1. **Tokenization**: Standard tokenization produces initial tokens
2. **Improvements**: Feature flag-controlled improvements applied
3. **Classification**: Role classification proceeds with improved tokens
4. **Tracing**: Improvement operations logged in trace

### Trace Information

When improvements are applied, trace entries are added:

```json
{
  "type": "tokenizer",
  "action": "collapse_double_dots",
  "count": 2
}

{
  "type": "tokenizer",
  "action": "normalize_hyphen",
  "original": "петрова-сидорова",
  "normalized": "Петрова-Сидорова"
}
```

### Usage in NormalizationService

```python
import os
from src.ai_service.layers.normalization.normalization_service import NormalizationService

# Enable features
os.environ["FIX_INITIALS_DOUBLE_DOT"] = "true"
os.environ["PRESERVE_HYPHENATED_CASE"] = "true"

service = NormalizationService()

# Test double dot collapse
result = await service.normalize_async("И.. И.", language="ru")
print(result.normalized)  # "И. И."

# Test hyphenated names
result = await service.normalize_async("петрова-сидорова", language="ru")
print(result.normalized)  # "Петрова-Сидорова"
```

## Performance Characteristics

### Performance Goals

- **p95 degradation**: ≤ +1ms on short strings
- **Operations**: Simple string operations, no regex compilation
- **Caching**: Feature flags cached at service initialization

### Complexity

- **Double Dot Collapse**: O(n) where n = number of tokens
- **Hyphenated Normalization**: O(m) where m = length of token
- **Memory**: In-place modifications where possible

### Benchmarks

Typical performance on short strings (10-50 characters):
- **Without improvements**: ~1-2ms
- **With improvements**: ~1-3ms
- **Degradation**: <1ms (within target)

## Backward Compatibility

### Legacy Behavior

When feature flags are disabled (default), the tokenizer behaves exactly as before:
- No double dot collapse
- No hyphenated name normalization
- No additional trace entries

### Migration Strategy

1. **Phase 1**: Deploy with flags disabled
2. **Phase 2**: Enable flags in development/staging
3. **Phase 3**: Gradual rollout in production
4. **Phase 4**: Enable by default

### Testing

```bash
# Run tokenizer-specific tests
pytest tests/smoke/test_tokenizer_initials_and_hyphens.py

# Test with flags enabled
FIX_INITIALS_DOUBLE_DOT=true PRESERVE_HYPHENATED_CASE=true pytest tests/smoke/

# Test legacy behavior (flags disabled)
pytest tests/smoke/test_tokenizer_initials_and_hyphens.py::TestTokenizerWithoutFlags
```

## Troubleshooting

### Common Issues

1. **Feature flags not working**
   - Check environment variables are set correctly
   - Restart service after changing environment
   - Verify `get_feature_flag_manager()` returns updated flags

2. **Performance degradation**
   - Profile with `result.processing_time`
   - Check for large numbers of hyphenated tokens
   - Verify simple operations are being used

3. **Unexpected normalization**
   - Check trace entries for improvement operations
   - Verify input validation (valid segments)
   - Test with flags disabled for comparison

### Debug Mode

```python
import logging
logging.getLogger('src.ai_service.layers.normalization').setLevel(logging.DEBUG)

# Enable trace logging to see improvement operations
result = await service.normalize_async(text, language="ru")
for trace in result.trace:
    print(trace)
```

## Examples

### Complete Examples

```python
import asyncio
import os
from src.ai_service.layers.normalization.normalization_service import NormalizationService

async def example_usage():
    # Enable improvements
    os.environ["FIX_INITIALS_DOUBLE_DOT"] = "true"
    os.environ["PRESERVE_HYPHENATED_CASE"] = "true"

    service = NormalizationService()

    # Russian example
    result = await service.normalize_async("И.. петрова-сидорова", language="ru")
    print(f"Input: И.. петрова-сидорова")
    print(f"Output: {result.normalized}")  # "И. Петрова-Сидорова"
    print(f"Success: {result.success}")
    print(f"Trace: {len(result.trace)} operations")

    # Ukrainian example
    result = await service.normalize_async("І.. ковальська-шевченко", language="uk")
    print(f"Input: І.. ковальська-шевченко")
    print(f"Output: {result.normalized}")  # "І. Ковальська-Шевченко"

    # English example
    result = await service.normalize_async("J.. O'Neil-Smith", language="en")
    print(f"Input: J.. O'Neil-Smith")
    print(f"Output: {result.normalized}")  # "J. O'Neil-Smith"

if __name__ == "__main__":
    asyncio.run(example_usage())
```

### Before/After Comparison

| Input | Without Flags | With Flags |
|-------|---------------|------------|
| `И.. И.` | `И.. И.` | `И. И.` |
| `петрова-сидорова` | `петрова-сидорова` | `Петрова-Сидорова` |
| `J.. R..` | `J.. R..` | `J. R.` |
| `o'neil-smith` | `o'neil-smith` | `O'Neil-Smith` |
| `...` | `...` | `...` (unchanged) |
| `и.о.` | `и.о.` | `и.о.` (unchanged) |