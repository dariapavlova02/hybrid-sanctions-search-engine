# Deprecated Files Backup List

## Files to be removed in cleanup:

### Orchestrator Files (deprecated)
- `src/ai_service/core/orchestrator_service.py` - Original orchestrator (deprecated)
- `src/ai_service/core/orchestrator_v2.py` - V2 orchestrator (deprecated)
- `src/ai_service/orchestration/clean_orchestrator.py` - Clean orchestrator (deprecated)

### Supporting Files for Old Orchestrators
- `src/ai_service/core/service_coordinator.py` - Used by deprecated orchestrators
- `src/ai_service/core/statistics_manager.py` - Used by deprecated orchestrators
- `src/ai_service/orchestration/` - Entire orchestration directory (superseded)

### Reason for Removal
All functionality consolidated into:
- `src/ai_service/core/unified_orchestrator.py` - THE unified orchestrator
- `src/ai_service/core/orchestrator_factory.py` - Factory for initialization

### Date Removed
[Date will be added when removed]

### Backup Location
[If needed, files can be retrieved from git history before this commit]

## Migration Complete
✅ main.py updated to use UnifiedOrchestrator
✅ All tests use new contracts
✅ Deprecation warnings were in place
✅ Migration guide provided