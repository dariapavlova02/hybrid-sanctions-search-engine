# MorphologyAdapter Documentation

## Overview

The `MorphologyAdapter` is a unified interface for morphological analysis using pymorphy3 with advanced caching, thread safety, and fallback behavior for Ukrainian language support.

## Architecture

### Core Components

- **MorphologyAdapter**: Main class providing morphological analysis
- **MorphParse**: Immutable dataclass representing parse results
- **Global Adapter**: Singleton pattern for sharing across requests
- **LRU Cache**: Configurable caching for performance optimization

### Key Features

- **Thread Safety**: All operations are thread-safe using RLock
- **LRU Caching**: Configurable cache size (default: 50,000 entries)
- **UK Dictionary Support**: Automatic fallback when Ukrainian dictionary unavailable
- **Performance Optimized**: Target p95 < 10ms, average < 2ms with warm cache
- **Graceful Degradation**: Continues working when pymorphy3 unavailable

## API Reference

### MorphologyAdapter

#### Constructor

```python
MorphologyAdapter(cache_size: int = 50000)
```

**Parameters:**
- `cache_size`: Maximum number of cached parse results (default: 50,000)

#### Methods

##### parse(token: str, lang: str) -> List[MorphParse]

Parse a token and return morphological analysis results.

**Parameters:**
- `token`: Token to analyze
- `lang`: Language code ('ru' or 'uk')

**Returns:**
- List of `MorphParse` objects with morphological information

**Example:**
```python
adapter = MorphologyAdapter()
parses = adapter.parse("Иванова", "ru")
for parse in parses:
    print(f"Normal: {parse.normal}, Gender: {parse.gender}, Case: {parse.case}")
```

##### to_nominative(token: str, lang: str) -> str

Convert token to nominative case.

**Parameters:**
- `token`: Token to convert
- `lang`: Language code ('ru' or 'uk')

**Returns:**
- Nominative form of the token

**Example:**
```python
adapter = MorphologyAdapter()
nominative = adapter.to_nominative("Ивановой", "ru")  # Returns "Иванова"
```

##### detect_gender(token: str, lang: str) -> str

Detect grammatical gender of token.

**Parameters:**
- `token`: Token to analyze
- `lang`: Language code ('ru' or 'uk')

**Returns:**
- Gender: 'masc', 'femn', or 'unknown'

**Example:**
```python
adapter = MorphologyAdapter()
gender = adapter.detect_gender("Анна", "ru")  # Returns "femn"
```

##### warmup(samples: List[Tuple[str, str]]) -> None

Warm up cache with common names and surnames.

**Parameters:**
- `samples`: List of (token, language) tuples to pre-cache

**Example:**
```python
adapter = MorphologyAdapter()
samples = [("Анна", "ru"), ("Иван", "ru"), ("Олена", "uk")]
adapter.warmup(samples)
```

##### clear_cache() -> None

Clear all cached results (useful for testing).

##### get_cache_stats() -> Dict[str, int]

Get cache statistics.

**Returns:**
- Dictionary with cache statistics (size, hits, misses)

##### is_uk_available() -> bool

Check if Ukrainian dictionary is available.

### MorphParse

Immutable dataclass representing a morphological parse result.

**Fields:**
- `normal`: Normal form of the word
- `tag`: Morphological tag string
- `score`: Confidence score (0.0 to 1.0)
- `case`: Grammatical case (e.g., 'nomn', 'gent')
- `gender`: Grammatical gender ('masc', 'femn', or None)
- `nominative`: Nominative form of the word

### Global Adapter Functions

#### get_global_adapter(cache_size: int = 50000) -> MorphologyAdapter

Get global adapter instance (singleton pattern).

**Parameters:**
- `cache_size`: Cache size for initial creation (ignored on subsequent calls)

**Returns:**
- Global MorphologyAdapter instance

#### clear_global_cache() -> None

Clear global adapter cache.

## Caching Strategy

### LRU Cache Implementation

The adapter uses three separate LRU caches:
- **Parse Cache**: Stores raw morphological analysis results
- **Nominative Cache**: Stores nominative form conversions
- **Gender Cache**: Stores gender detection results

### Cache Configuration

- **Default Size**: 50,000 entries per cache
- **Thread Safety**: All cache operations are thread-safe
- **Memory Management**: Automatic eviction of least recently used entries

### Performance Characteristics

With warmed cache:
- **Average Time**: < 2ms per operation
- **P95 Time**: < 10ms per operation
- **Cache Hit Ratio**: > 80% for repeated operations

## Fallback Behavior

### Ukrainian Dictionary Fallback

When Ukrainian dictionary is not available:

1. **Warning Logged**: One-time warning about missing UK dictionary
2. **Fallback to Russian**: Uses Russian analyzer for Ukrainian tokens
3. **Identity Behavior**: Returns original token for operations that fail
4. **Service Continuity**: Service continues working without crashing

### pymorphy3 Unavailability

When pymorphy3 is not installed:

1. **Error Logged**: Error message about missing dependency
2. **Empty Results**: Parse operations return empty lists
3. **Identity Behavior**: Other operations return original tokens
4. **Service Continuity**: Service continues working with limited functionality

## Thread Safety

### Implementation Details

- **RLock Usage**: All critical sections protected by RLock
- **Immutable Data**: MorphParse objects are immutable
- **Cache Safety**: LRU cache operations are thread-safe
- **Global State**: Global adapter access is thread-safe

### Concurrent Access

The adapter is designed for high-concurrency environments:
- Multiple threads can safely access the same adapter instance
- Cache operations are atomic and thread-safe
- No shared mutable state between operations

## Performance Optimization

### Caching Strategy

1. **Pre-warming**: Use `warmup()` for common names
2. **Cache Size**: Adjust based on memory constraints
3. **Global Sharing**: Use global adapter for request sharing

### Best Practices

1. **Warm Cache**: Always warm up cache with common names
2. **Reuse Adapter**: Use global adapter instead of creating new instances
3. **Monitor Performance**: Use `get_cache_stats()` for monitoring
4. **Batch Operations**: Process multiple tokens in batches

## Error Handling

### Graceful Degradation

The adapter implements graceful degradation at multiple levels:

1. **Missing Dependencies**: Continues working with limited functionality
2. **Parse Failures**: Returns empty results instead of crashing
3. **Inflection Errors**: Falls back to normal form
4. **Cache Errors**: Continues without caching

### Logging

- **Debug Level**: Individual parse failures
- **Warning Level**: Missing dictionaries, initialization issues
- **Error Level**: Critical failures that affect functionality

## Usage Examples

### Basic Usage

```python
from src.ai_service.layers.normalization.morphology_adapter import get_global_adapter

# Get global adapter
adapter = get_global_adapter()

# Parse token
parses = adapter.parse("Иванова", "ru")
print(f"Found {len(parses)} parses")

# Convert to nominative
nominative = adapter.to_nominative("Ивановой", "ru")
print(f"Nominative: {nominative}")

# Detect gender
gender = adapter.detect_gender("Анна", "ru")
print(f"Gender: {gender}")
```

### Advanced Usage

```python
# Custom adapter with large cache
adapter = MorphologyAdapter(cache_size=100000)

# Warm up with common names
samples = [
    ("Анна", "ru"), ("Мария", "ru"), ("Иван", "ru"),
    ("Олена", "uk"), ("Ірина", "uk"), ("Іван", "uk"),
]
adapter.warmup(samples)

# Check cache statistics
stats = adapter.get_cache_stats()
print(f"Cache size: {stats['parse_cache_size']}")
print(f"Cache hits: {stats['parse_cache_hits']}")

# Clear cache when needed
adapter.clear_cache()
```

### Integration with NormalizationService

```python
from src.ai_service.layers.normalization.normalization_service import NormalizationService

# Service automatically uses global adapter
service = NormalizationService()

# Warm up morphology cache
service.warmup_morphology_cache()

# Normalize text (uses morphology adapter internally)
result = service.normalize("Анна Ивановой", language="ru")
print(f"Normalized: {result.normalized}")
```

## Adding Dictionaries

### Installing Ukrainian Dictionary

```bash
# Install Ukrainian dictionary for pymorphy3
pip install pymorphy3-dicts-uk
```

### Verifying Installation

```python
adapter = MorphologyAdapter()
if adapter.is_uk_available():
    print("Ukrainian dictionary is available")
else:
    print("Ukrainian dictionary not available, using fallback")
```

### Custom Dictionary Support

To add support for additional languages:

1. Install language-specific dictionary
2. Modify `_create_analyzer()` method
3. Add language code to supported languages
4. Update tests and documentation

## Troubleshooting

### Common Issues

1. **Slow Performance**: Ensure cache is warmed up
2. **Memory Usage**: Reduce cache size if needed
3. **UK Fallback**: Check if Ukrainian dictionary is installed
4. **Thread Issues**: Use global adapter for sharing

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger('src.ai_service.layers.normalization.morphology_adapter').setLevel(logging.DEBUG)

# Check cache statistics
adapter = get_global_adapter()
stats = adapter.get_cache_stats()
print(f"Cache stats: {stats}")

# Test specific token
parses = adapter.parse("problematic_token", "ru")
print(f"Parses: {parses}")
```

### Performance Monitoring

```python
import time

# Measure operation time
start = time.perf_counter()
result = adapter.parse("token", "ru")
end = time.perf_counter()
print(f"Operation took {(end - start) * 1000:.2f}ms")
```

## Testing

### Unit Tests

```bash
# Run unit tests
python -m pytest tests/unit/morphology/test_adapter_basic.py -v
```

### Performance Tests

```bash
# Run performance tests
python -m pytest tests/performance/test_morph_adapter_perf.py -v
```

### Test Coverage

The adapter is thoroughly tested with:
- Unit tests for all methods
- Performance tests for speed requirements
- Thread safety tests
- Fallback behavior tests
- Error handling tests

## Migration Guide

### From Old MorphologyAdapter

1. **Import Change**: Update import path
2. **Global Adapter**: Use `get_global_adapter()` instead of creating instances
3. **Cache Management**: Use new cache management methods
4. **Error Handling**: Update error handling for new behavior

### Backward Compatibility

The new adapter maintains backward compatibility with existing code:
- Same method signatures
- Same return types
- Same error handling patterns
- Additional features are opt-in
