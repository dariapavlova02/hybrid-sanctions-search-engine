#!/usr/bin/env python3
import os
import sys

# Set environment variables for testing
os.environ['ENABLE_SEARCH'] = 'true'
os.environ['ELASTICSEARCH_URL'] = 'http://localhost:9200'

sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_search():
    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.config import HybridSearchConfig

        # Create search service
        search_config = HybridSearchConfig()
        search_service = HybridSearchService(search_config)

        # Create orchestrator with search service
        from ai_service.layers.validation.validation_service import ValidationService
        from ai_service.layers.language.language_detection_service import LanguageDetectionService
        from ai_service.layers.unicode.unicode_service import UnicodeService
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.signals.signals_service import SignalsService

        orchestrator = UnifiedOrchestrator(
            validation_service=ValidationService(),
            language_service=LanguageDetectionService(),
            unicode_service=UnicodeService(),
            normalization_service=NormalizationService(),
            signals_service=SignalsService(),
            search_service=search_service  # ← This is the key!
        )

        # Test search
        result = await orchestrator.process_async("Порошенк Петро")

        print(f"Search results: {result.search_results}")
        print(f"Total hits: {result.search_results.get('total_hits', 0)}")

        return result.search_results.get('total_hits', 0) > 0

    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_search())
    print(f"Test {'PASSED' if success else 'FAILED'}")
