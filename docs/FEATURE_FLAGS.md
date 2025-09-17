# Feature Flags Documentation

This document describes the feature flags system for safe rollout of new functionality in the AI normalization service.

## Overview

The feature flags system allows for controlled, gradual rollout of new features and improvements without risking system stability. Flags can be configured at multiple levels with clear precedence rules.

## Configuration Levels

1. **Environment Variables** (highest priority)
2. **YAML Configuration File** (medium priority)
3. **API Request Flags** (request-level override)
4. **Default Values** (lowest priority)

## Available Feature Flags

### Core Normalization Flags

| Flag | Default | Description | Impact |
|------|---------|-------------|---------|
| `use_factory_normalizer` | `false` | Use factory-based normalization instead of legacy | Routes to factory implementation |
| `fix_initials_double_dot` | `false` | Collapse double dots in initials (И.. → И.) | Tokenizer post-processing |
| `preserve_hyphenated_case` | `false` | Preserve proper case in hyphenated names | Tokenizer post-processing |
| `strict_stopwords` | `false` | Use stricter stopword filtering | Tokenizer filtering |

### Search Integration Flags

| Flag | Default | Description | Impact |
|------|---------|-------------|---------|
| `enable_ac_tier0` | `false` | Enable AC (exact match) search tier | Search service routing |
| `enable_vector_fallback` | `false` | Enable vector search fallback | Search service fallback |

### Gender and Case Enforcement

| Flag | Default | Description | Impact |
|------|---------|-------------|---------|
| `enforce_nominative` | `true` | Enforce nominative case in results | Morphology processing |
| `preserve_feminine_surnames` | `true` | Preserve feminine surname forms | Gender-aware processing |

## Configuration Methods

### 1. Environment Variables

Set environment variables with the `AISVC_FLAG_` prefix:

```bash
export AISVC_FLAG_USE_FACTORY_NORMALIZER=true
export AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT=true
export AISVC_FLAG_PRESERVE_HYPHENATED_CASE=false
export AISVC_FLAG_STRICT_STOPWORDS=true
export AISVC_FLAG_ENABLE_AC_TIER0=false
export AISVC_FLAG_ENABLE_VECTOR_FALLBACK=false
export AISVC_FLAG_ENFORCE_NOMINATIVE=true
export AISVC_FLAG_PRESERVE_FEMININE_SURNAMES=true
```

### 2. YAML Configuration File

Create or modify `src/ai_service/config/feature_flags.yaml`:

```yaml
development:
  feature_flags:
    use_factory_normalizer: false
    fix_initials_double_dot: true
    preserve_hyphenated_case: false
    strict_stopwords: true
    enable_ac_tier0: false
    enable_vector_fallback: false
    enforce_nominative: true
    preserve_feminine_surnames: true

staging:
  feature_flags:
    use_factory_normalizer: true
    fix_initials_double_dot: true
    preserve_hyphenated_case: true
    strict_stopwords: false
    enable_ac_tier0: true
    enable_vector_fallback: false
    enforce_nominative: true
    preserve_feminine_surnames: true

production:
  feature_flags:
    use_factory_normalizer: false
    fix_initials_double_dot: false
    preserve_hyphenated_case: false
    strict_stopwords: true
    enable_ac_tier0: false
    enable_vector_fallback: false
    enforce_nominative: true
    preserve_feminine_surnames: true
```

### 3. API Request Override

Include flags in API requests:

```json
{
  "text": "Иван Петров",
  "language": "ru",
  "options": {
    "flags": {
      "use_factory_normalizer": true,
      "fix_initials_double_dot": true,
      "preserve_hyphenated_case": true,
      "strict_stopwords": false
    }
  }
}
```

## API Examples

### Basic Normalization Request

```bash
curl -X POST "http://localhost:8000/normalize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Иван Петров",
    "language": "ru"
  }'
```

### Request with Feature Flags

```bash
curl -X POST "http://localhost:8000/normalize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "И.. Петров-сидоров",
    "language": "ru",
    "options": {
      "flags": {
        "fix_initials_double_dot": true,
        "preserve_hyphenated_case": true,
        "strict_stopwords": true
      }
    }
  }'
```

### Process Request with Flags

```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Иван Петров",
    "generate_variants": false,
    "generate_embeddings": false,
    "options": {
      "flags": {
        "use_factory_normalizer": true,
        "enable_ac_tier0": true
      }
    }
  }'
```

## Flag Behavior and Effects

### `use_factory_normalizer`

**Purpose**: Controls which normalization implementation to use.

**Values**:
- `true`: Use factory-based normalization (new implementation)
- `false`: Use legacy normalization (stable implementation)

**Impact**: Routes requests to different normalization code paths.

**Example**:
```json
{
  "flags": {
    "use_factory_normalizer": true
  }
}
```

### `fix_initials_double_dot`

**Purpose**: Collapse multiple dots in initials to single dots.

**Values**:
- `true`: Collapse И.. → И.
- `false`: Leave initials unchanged

**Impact**: Post-processing in tokenizer.

**Example**:
- Input: "И.. Петров"
- Output: "И. Петров" (with `fix_initials_double_dot: true`)

### `preserve_hyphenated_case`

**Purpose**: Preserve proper capitalization in hyphenated names.

**Values**:
- `true`: Capitalize each part after hyphen
- `false`: Leave hyphenated names unchanged

**Impact**: Post-processing in tokenizer.

**Example**:
- Input: "петрова-сидорова"
- Output: "Петрова-Сидорова" (with `preserve_hyphenated_case: true`)

### `strict_stopwords`

**Purpose**: Apply stricter stopword filtering.

**Values**:
- `true`: Use strict stopword filtering
- `false`: Use standard stopword filtering

**Impact**: Tokenizer filtering logic.

**Example**:
- Input: "и Иван в Петров на"
- Output: "Иван Петров" (with `strict_stopwords: true`)

### `enable_ac_tier0`

**Purpose**: Enable AC (exact match) search tier.

**Values**:
- `true`: Enable AC search
- `false`: Disable AC search

**Impact**: Search service routing.

### `enable_vector_fallback`

**Purpose**: Enable vector search as fallback.

**Values**:
- `true`: Enable vector search fallback
- `false`: Disable vector search fallback

**Impact**: Search service fallback behavior.

## Testing and Validation

### Test Coverage Matrix

| Flag | Unit Tests | Integration Tests | Acceptance Tests |
|------|------------|-------------------|------------------|
| `use_factory_normalizer` | ✅ | ✅ | ✅ |
| `fix_initials_double_dot` | ✅ | ✅ | ✅ |
| `preserve_hyphenated_case` | ✅ | ✅ | ✅ |
| `strict_stopwords` | ✅ | ✅ | ✅ |
| `enable_ac_tier0` | ✅ | ⚠️ | ⚠️ |
| `enable_vector_fallback` | ✅ | ⚠️ | ⚠️ |
| `enforce_nominative` | ✅ | ✅ | ✅ |
| `preserve_feminine_surnames` | ✅ | ✅ | ✅ |

Legend:
- ✅ Fully tested
- ⚠️ Partially tested (infrastructure ready)

### Running Tests

```bash
# Run all feature flag tests
pytest tests/feature_flags/ tests/acceptance/test_rollout_safety.py tests/unit/test_defensive_flags.py

# Run specific test categories
pytest tests/feature_flags/ -v  # Configuration tests
pytest tests/acceptance/test_rollout_safety.py -v  # Acceptance tests
pytest tests/unit/test_defensive_flags.py -v  # Defensive logic tests
```

## Defensive Handling

The system includes defensive handling for invalid or malformed flags:

1. **Invalid Types**: Non-FeatureFlags objects are replaced with defaults
2. **Invalid Values**: Non-boolean values are reset to defaults
3. **Missing Flags**: Missing flags use global configuration
4. **Unknown Flags**: Unknown flags are ignored
5. **Exceptions**: Any validation errors fall back to defaults

### Example Defensive Scenarios

```python
# Invalid type - uses defaults
{"flags": "invalid_string"}

# Invalid values - corrected to defaults
{"flags": {"use_factory_normalizer": "not_a_boolean"}}

# Unknown flags - ignored
{"flags": {"unknown_flag": true}}

# Mixed valid/invalid - valid kept, invalid corrected
{"flags": {
  "use_factory_normalizer": true,  # Valid - kept
  "fix_initials_double_dot": "invalid"  # Invalid - corrected
}}
```

## Monitoring and Tracing

All feature flags are included in response traces for monitoring and debugging:

```json
{
  "trace": [
    {
      "type": "flags",
      "value": {
        "use_factory_normalizer": true,
        "fix_initials_double_dot": true,
        "preserve_hyphenated_case": false,
        "strict_stopwords": true,
        "enable_ac_tier0": false,
        "enable_vector_fallback": false,
        "enforce_nominative": true,
        "preserve_feminine_surnames": true
      },
      "scope": "request"
    }
  ]
}
```

## Rollout Strategy

### Phase 1: Infrastructure (Current)
- ✅ Feature flags system implemented
- ✅ Defensive handling in place
- ✅ Comprehensive test coverage
- ✅ Documentation complete

### Phase 2: Gradual Rollout
- Enable flags in staging environment
- Monitor performance and accuracy
- Gradual rollout to production

### Phase 3: Full Deployment
- Enable all flags by default
- Remove legacy code paths
- Clean up feature flag system

## Troubleshooting

### Common Issues

1. **Flags not taking effect**
   - Check environment variable names (must start with `AISVC_FLAG_`)
   - Verify YAML file syntax
   - Check API request format

2. **Unexpected behavior**
   - Check flag precedence (ENV > YAML > API > Defaults)
   - Verify flag values are boolean
   - Check logs for validation warnings

3. **Performance issues**
   - Monitor with `use_factory_normalizer` flag
   - Check search flags impact
   - Review processing traces

### Debug Commands

```bash
# Check current flag values
curl -X POST "http://localhost:8000/normalize" \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' | jq '.trace[] | select(.type == "flags")'

# Test specific flag combinations
curl -X POST "http://localhost:8000/normalize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "И.. Петров-сидоров",
    "options": {
      "flags": {
        "fix_initials_double_dot": true,
        "preserve_hyphenated_case": true
      }
    }
  }'
```

## Migration Guide

### From Legacy to Factory Normalization

1. **Enable in staging**:
   ```yaml
   staging:
     feature_flags:
       use_factory_normalizer: true
   ```

2. **Monitor performance**:
   - Check processing times
   - Verify accuracy
   - Monitor error rates

3. **Gradual production rollout**:
   ```yaml
   production:
     feature_flags:
       use_factory_normalizer: true
   ```

4. **Remove legacy code** (future phase):
   - Remove legacy normalization service
   - Clean up feature flag system
   - Update documentation

## Security Considerations

- Feature flags are included in traces - ensure no sensitive data
- Environment variables should be properly secured
- YAML configuration files should have appropriate permissions
- API requests with flags should be validated

## Performance Impact

- Feature flag validation adds minimal overhead
- Flag processing in tokenizer is lightweight
- Tracing adds small memory overhead
- No significant performance impact on normal operations
