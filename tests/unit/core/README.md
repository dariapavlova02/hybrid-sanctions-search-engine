# Core Unified Architecture Tests

This directory contains unit tests for the core unified architecture components.

## 🏗️ New Unified Architecture

**All deprecated orchestrator implementations have been removed and replaced with:**

- **UnifiedOrchestrator** - Single orchestrator implementing 9-layer CLAUDE.md specification
- **OrchestratorFactory** - Factory for creating configured orchestrator instances
- **Unified Contracts** - Consistent data structures across all layers

## Test Files

- `test_unified_orchestrator.py` - ✅ **Main orchestrator tests** for 9-layer pipeline
- `test_unified_contracts.py` - ✅ **Contract validation tests** for all data structures

## Test Categories

### Unified Orchestrator Tests
- ✅ Complete 9-layer pipeline execution
- ✅ Service integration and coordination
- ✅ Flag behavior validation (CLAUDE.md requirement)
- ✅ Error handling and graceful degradation
- ✅ Performance requirements (≤10ms short strings)

### Contract Validation Tests
- ✅ TokenTrace structure and completeness
- ✅ NormalizationResult with all metadata fields
- ✅ SignalsResult with structured persons/organizations
- ✅ Serialization/deserialization compatibility

## Key Features Tested

### CLAUDE.md Compliance
- **9-Layer Pipeline**: Validation → SmartFilter → Language → Unicode → **Normalization** → Signals → Variants → Embeddings → Response
- **Flag Behavior**: Real impact from `remove_stop_words`, `preserve_names`, `enable_advanced_features`
- **ORG_ACRONYMS**: Always tagged as `unknown`
- **ASCII Handling**: No morphology in ru/uk context
- **Performance**: Monitoring and warnings

### Architecture Benefits
- **Single Source of Truth**: One orchestrator replaces 3+ implementations
- **Clean Layer Separation**: Each layer has specific responsibilities
- **Comprehensive Tracing**: TokenTrace for every normalized token
- **Structured Signals**: Persons and organizations with full metadata

## Running Tests

```bash
# Run all core unified architecture tests
pytest tests/unit/core/ -v

# Run specific test files
pytest tests/unit/core/test_unified_orchestrator.py -v
pytest tests/unit/core/test_unified_contracts.py -v

# Test specific functionality
pytest tests/unit/core/ -k "contract" -v
pytest tests/unit/core/ -k "orchestrator" -v
```

## Migration Notes

**⚠️ Deprecated (Removed):**
- ~~`OrchestratorService`~~ → `UnifiedOrchestrator`
- ~~`OrchestratorV2`~~ → `UnifiedOrchestrator`
- ~~`CleanOrchestrator`~~ → `UnifiedOrchestrator`

**✅ Current (Active):**
- `UnifiedOrchestrator` - THE single orchestrator
- `OrchestratorFactory` - Proper initialization
- New contracts system - Consistent data structures

See `MIGRATION_GUIDE.md` for complete migration information.