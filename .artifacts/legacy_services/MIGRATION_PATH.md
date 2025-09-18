# Legacy Services Migration Path

## Archived Services

### normalization_service_decomposed.py
- **Archived Date**: 2024-09-18
- **Reason**: Replaced by unified NormalizationService
- **Migration**: Use `src/ai_service/layers/normalization/normalization_service.py` instead

#### Key Changes in Migration:
1. **Component Integration**: Previously separated components (TokenizerService, RoleTaggerService, MorphologyAdapter, NameAssembler) are now integrated into a single service class
2. **API Compatibility**: The main `normalize_async()` method maintains the same signature and contract
3. **Performance**: Unified service eliminates inter-component overhead
4. **Trace System**: Enhanced TokenTrace system provides better debugging capabilities

#### If You Need to Reference Old Implementation:
- Archived file contains the decomposed architecture approach
- Can be used as reference for understanding component separation
- All functionality has been preserved and enhanced in the unified service

#### Code Migration Example:
```python
# Old (decomposed):
from src.ai_service.layers.normalization.normalization_service_decomposed import NormalizationServiceDecomposed
service = NormalizationServiceDecomposed()

# New (unified):
from src.ai_service.layers.normalization.normalization_service import NormalizationService
service = NormalizationService()
```

## Active Legacy Components

### LegacyNormalizationAdapter
- **Status**: ACTIVE (backward compatibility adapter)
- **Location**: `src/ai_service/adapters/legacy_normalization_adapter.py`
- **Purpose**: Provides API compatibility layer
- **Migration Strategy**: Will be phased out when all clients migrate to new API

---
**Last Updated**: 2024-09-18
**Sprint**: Week 2 - Legacy Cleanup