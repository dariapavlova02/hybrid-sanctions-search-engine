# Production Configuration Profile

This document describes the production configuration profile for the AI Normalization Service, including feature flags, their purposes, and deployment strategies.

## Production Feature Flags (Current Profile)

### Core Processing Flags

**`use_factory_normalizer: false`**
- **Purpose**: Choose between factory (new) and legacy normalization implementations
- **Production Setting**: `false` (legacy implementation)
- **Rationale**: Legacy implementation is battle-tested and stable for production workloads
- **Impact**: Uses the original normalization pipeline with proven reliability

**`fix_initials_double_dot: false`**
- **Purpose**: Fix double dots in initials (И.. → И.)
- **Production Setting**: `false` (disabled)
- **Rationale**: Conservative approach - avoid changing existing behavior in production
- **Impact**: Initials with double dots remain unchanged

**`preserve_hyphenated_case: false`**
- **Purpose**: Preserve case in hyphenated surnames (петрова-сидорова → Петрова-Сидорова)
- **Production Setting**: `false` (disabled)
- **Rationale**: Consistent with existing production behavior
- **Impact**: Hyphenated names follow standard capitalization rules

### Search Integration Flags

**`enable_ac_tier0: false`**
- **Purpose**: Enable Aho-Corasick tier-0 search optimization
- **Production Setting**: `false` (disabled)
- **Rationale**: Conservative rollout - requires performance validation under production load
- **Impact**: Standard search algorithm without tier-0 optimization

**`enable_vector_fallback: false`**
- **Purpose**: Enable vector search fallback when primary search fails
- **Production Setting**: `false` (disabled)
- **Rationale**: Vector search adds complexity and latency - needs gradual rollout
- **Impact**: No fallback to vector search, relies on primary search mechanisms

### Validation Flags

**`require_tin_dob_gate: missing in production`**
- **Purpose**: Require TIN/DOB validation gating (only in staging)
- **Production Setting**: Not configured (implicitly false)
- **Rationale**: Validation gates are for staging/testing, not production
- **Impact**: No additional validation requirements

## Configuration Strategy by Environment

### Development Environment
```yaml
development:
  feature_flags:
    use_factory_normalizer: false    # Test against legacy baseline
    fix_initials_double_dot: false   # Conservative defaults
    preserve_hyphenated_case: false  # Conservative defaults
    enable_ac_tier0: false           # Disabled for baseline testing
    enable_vector_fallback: false    # Disabled for baseline testing
```

**Strategy**: Conservative baseline for development and testing against known behavior.

### Staging Environment
```yaml
staging:
  feature_flags:
    use_factory_normalizer: true     # Test new implementation
    fix_initials_double_dot: true    # Test improvements
    preserve_hyphenated_case: false  # Still conservative
    enable_ac_tier0: true            # Test search optimizations
    enable_vector_fallback: false    # Still conservative on complex features
    require_tin_dob_gate: true       # Test validation gates
```

**Strategy**: Progressive feature enablement for validation before production.

### Production Environment
```yaml
production:
  feature_flags:
    use_factory_normalizer: false   # Battle-tested legacy implementation
    fix_initials_double_dot: false  # No behavior changes in production
    preserve_hyphenated_case: false # No behavior changes in production
    enable_ac_tier0: false          # Conservative - no performance unknowns
    enable_vector_fallback: false   # Conservative - no complexity additions
```

**Strategy**: Maximum stability and reliability with proven implementations.

## Feature Flag Categories

### 1. Implementation Selection Flags
- `use_factory_normalizer`: Core architecture choice
- **Production Policy**: Use legacy until factory is fully validated

### 2. Behavior Modification Flags
- `fix_initials_double_dot`: Changes output format
- `preserve_hyphenated_case`: Changes capitalization behavior
- **Production Policy**: Minimize behavior changes to maintain consistency

### 3. Performance Optimization Flags
- `enable_ac_tier0`: Search performance optimization
- **Production Policy**: Validate performance impact thoroughly before enabling

### 4. Feature Addition Flags
- `enable_vector_fallback`: Adds new search capabilities
- **Production Policy**: Gradual rollout with extensive monitoring

### 5. Validation/Testing Flags
- `require_tin_dob_gate`: Testing and validation infrastructure
- **Production Policy**: Generally excluded from production

## Rollout Strategy

### Phase 1: Development Validation
1. All flags set to conservative defaults
2. Validate baseline behavior
3. Test individual flag impacts

### Phase 2: Staging Validation
1. Progressive enablement of new features
2. Performance and accuracy testing
3. Edge case validation

### Phase 3: Production Rollout
1. Flags remain conservative until proven
2. Gradual enablement with monitoring
3. Immediate rollback capability

## Monitoring and Rollback

### Key Metrics to Monitor
- **Normalization accuracy**: Compare outputs before/after flag changes
- **Performance metrics**: Latency, throughput, resource usage
- **Error rates**: Failed normalizations, exceptions
- **Search performance**: Hit rates, response times

### Rollback Procedures
1. **Immediate rollback**: Set flag to `false` in configuration
2. **Service restart**: May be required for some flag changes
3. **Monitoring**: Verify metrics return to baseline
4. **Communication**: Notify stakeholders of rollback

## Environment Variable Overrides

Feature flags can be overridden via environment variables:
```bash
AISVC_FLAG_USE_FACTORY_NORMALIZER=true
AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT=true
AISVC_FLAG_PRESERVE_HYPHENATED_CASE=true
AISVC_FLAG_ENABLE_AC_TIER0=true
AISVC_FLAG_ENABLE_VECTOR_FALLBACK=true
```

**Production Policy**: Environment overrides should be used sparingly and with careful monitoring.

## Security Considerations

### Flag Validation
- All flags have boolean validation
- Invalid values default to `false` (safe defaults)
- Configuration loading is fail-safe

### Access Control
- Flag changes require deployment
- No runtime flag modification in production
- Configuration is version-controlled

## Deprecation Strategy

### Phase-out Process
1. **Deprecation notice**: Flag marked as deprecated in docs
2. **Default change**: Default value updated to new behavior
3. **Warning period**: Logs warning when deprecated flag is used
4. **Removal**: Flag completely removed from codebase

### Example: strict_stopwords Removal
- **Issue**: Flag was always `false`, providing no functionality
- **Action**: Complete removal from codebase
- **Result**: Simplified configuration and reduced maintenance burden

## Best Practices

### Flag Design
1. **Boolean flags**: Simple on/off switches preferred
2. **Safe defaults**: Default to conservative/stable behavior
3. **Clear naming**: Use `enable_*` prefix for consistency
4. **Documentation**: Document purpose, impact, and rollout strategy

### Configuration Management
1. **Version control**: All flag changes tracked in git
2. **Environment parity**: Maintain consistent flag names across environments
3. **Gradual rollout**: Test in development → staging → production
4. **Monitoring**: Track metrics before, during, and after flag changes

### Operational Procedures
1. **Change approval**: Flag changes require code review
2. **Deployment coordination**: Coordinate with operations team
3. **Rollback preparedness**: Have rollback plan before enabling flags
4. **Documentation updates**: Update docs when flags change behavior

## Future Considerations

### Planned Flag Evolution
- Factory normalizer will eventually become default (`use_factory_normalizer: true`)
- Search optimizations will be enabled after performance validation
- Behavioral improvements will be phased in gradually

### Configuration Modernization
- Consider feature flag management system for runtime flag control
- Implement A/B testing framework for gradual rollouts
- Add automatic rollback based on metrics thresholds