#!/usr/bin/env python3

import os

print("🔍 Debugging search functionality issue")

# Check environment variables
print(f"ENABLE_SEARCH: {os.getenv('ENABLE_SEARCH', 'not_set')}")
print(f"ENABLE_EMBEDDINGS: {os.getenv('ENABLE_EMBEDDINGS', 'not_set')}")

# Check httpx version issue
try:
    import httpx
    print(f"httpx version: {getattr(httpx, '__version__', 'No __version__ attribute')}")
    print(f"httpx dir: {dir(httpx)[:10]}...")
except ImportError as e:
    print(f"httpx import error: {e}")

# Check elasticsearch
try:
    import elasticsearch
    print(f"elasticsearch imported successfully")
except ImportError as e:
    print(f"elasticsearch import error: {e}")

# Check if we can at least import basic AI service modules
try:
    import sys
    sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')
    from ai_service.config.settings import SERVICE_CONFIG
    print(f"SERVICE_CONFIG.enable_search: {SERVICE_CONFIG.enable_search}")
    print(f"SERVICE_CONFIG.enable_embeddings: {SERVICE_CONFIG.enable_embeddings}")
except Exception as e:
    print(f"Config import error: {e}")

print("\n💡 Solution: Need to fix httpx dependency conflict in elasticsearch")
print("   This is why search doesn't work - the search service can't load!")