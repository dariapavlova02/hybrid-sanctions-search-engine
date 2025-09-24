#!/usr/bin/env python3
"""
Fix httpx version issue by patching the missing __version__ attribute
"""

try:
    import httpx
    if not hasattr(httpx, '__version__'):
        # Add missing __version__ attribute for compatibility
        httpx.__version__ = "0.13.3"
        print(f"✅ Patched httpx.__version__ = '{httpx.__version__}'")
    else:
        print(f"✅ httpx already has __version__ = '{httpx.__version__}'")

    # Test elasticsearch import
    from elasticsearch import AsyncElasticsearch
    print("✅ Elasticsearch import successful")

except ImportError as e:
    print(f"❌ Import failed: {e}")