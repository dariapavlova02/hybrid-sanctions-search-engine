#!/usr/bin/env python3
"""
Fix search configuration to enable search functionality for IP 95.217.84.234
"""

import sys
import os
import json
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def fix_search_configuration():
    """Create a comprehensive search configuration fix."""
    print("🔧 FIXING SEARCH CONFIGURATION")
    print("="*50)

    # 1. Check current configuration
    print("📊 CURRENT CONFIGURATION:")
    try:
        from ai_service.config.settings import SERVICE_CONFIG
        print(f"  enable_search: {SERVICE_CONFIG.enable_search}")
        print(f"  elasticsearch_url: {getattr(SERVICE_CONFIG, 'elasticsearch_url', 'Not set')}")
    except Exception as e:
        print(f"  ❌ Cannot check current config: {e}")

    # 2. Show environment variables needed
    print(f"\n⚙️ REQUIRED ENVIRONMENT VARIABLES:")
    env_vars = {
        'ENABLE_SEARCH': 'true',
        'ELASTICSEARCH_URL': 'http://localhost:9200',  # Default local ES
        'ELASTICSEARCH_HOSTS': 'localhost:9200',
        'WATCHLIST_INDEX': 'watchlist',
        'WATCHLIST_AC_INDEX': 'watchlist_ac',
        'WATCHLIST_VECTOR_INDEX': 'watchlist_vector'
    }

    for var, default_value in env_vars.items():
        current = os.getenv(var, 'Not set')
        print(f"  {var}: {current} (should be: {default_value})")

    # 3. Create a simple script to enable search
    print(f"\n📝 CREATING SEARCH ENABLE SCRIPT:")

    enable_script = """#!/bin/bash
# Enable search functionality for ai-service

echo "🔧 Enabling search functionality..."

# Set environment variables
export ENABLE_SEARCH=true
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_HOSTS=localhost:9200
export WATCHLIST_INDEX=watchlist
export WATCHLIST_AC_INDEX=watchlist_ac
export WATCHLIST_VECTOR_INDEX=watchlist_vector

echo "✅ Search environment variables set:"
echo "  ENABLE_SEARCH=$ENABLE_SEARCH"
echo "  ELASTICSEARCH_URL=$ELASTICSEARCH_URL"
echo "  ELASTICSEARCH_HOSTS=$ELASTICSEARCH_HOSTS"

# Check if Elasticsearch is running
if curl -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
    echo "✅ Elasticsearch is running at $ELASTICSEARCH_URL"
else
    echo "⚠️  Elasticsearch is not running at $ELASTICSEARCH_URL"
    echo "   Please start Elasticsearch or update ELASTICSEARCH_URL"
fi

echo "🔍 Search functionality should now be enabled!"
echo "   Restart the ai-service to apply changes."
"""

    with open('/Users/dariapavlova/Desktop/ai-service/enable_search.sh', 'w') as f:
        f.write(enable_script)

    # Make it executable
    os.chmod('/Users/dariapavlova/Desktop/ai-service/enable_search.sh', 0o755)
    print("  ✅ Created enable_search.sh script")

    # 4. Create sample test data
    print(f"\n📄 CREATING SAMPLE SANCTIONS DATA:")

    # Create sample data with Poroshenko
    sample_data = [
        {
            "id": "poroshenko_1",
            "name": "Петро Олексійович Порошенко",
            "aliases": ["Petro Poroshenko", "Порошенко П.О.", "Poroshenko Petro"],
            "dob": "1965-09-26",
            "nationality": "Ukraine",
            "sanctions": ["EU", "UK"],
            "type": "person",
            "status": "active"
        },
        {
            "id": "poroshenko_2",
            "name": "Порошенко Петро",
            "aliases": ["P. Poroshenko", "Петр Порошенко"],
            "type": "person",
            "status": "active"
        }
    ]

    with open('/Users/dariapavlova/Desktop/ai-service/sample_sanctions_data.json', 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)

    print("  ✅ Created sample_sanctions_data.json")

    # 5. Create a test script
    print(f"\n🧪 CREATING TEST SCRIPT:")

    test_script = """#!/usr/bin/env python3
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
"""

    with open('/Users/dariapavlova/Desktop/ai-service/test_search_fix.py', 'w') as f:
        f.write(test_script)

    print("  ✅ Created test_search_fix.py")

    # 6. Summary and next steps
    print(f"\n📋 SUMMARY & NEXT STEPS:")
    print(f"")
    print(f"🎯 ROOT CAUSE IDENTIFIED:")
    print(f"   - ENABLE_SEARCH=false (search disabled)")
    print(f"   - search_service=None in UnifiedOrchestrator")
    print(f"   - No Elasticsearch connection")
    print(f"")
    print(f"🔧 TO FIX:")
    print(f"   1. Run: ./enable_search.sh")
    print(f"   2. Ensure Elasticsearch is running")
    print(f"   3. Load sanctions data into indices")
    print(f"   4. Initialize UnifiedOrchestrator with search_service")
    print(f"")
    print(f"🧪 TO TEST:")
    print(f"   Run: python test_search_fix.py")

if __name__ == "__main__":
    fix_search_configuration()