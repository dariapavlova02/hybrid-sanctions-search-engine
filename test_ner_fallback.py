#!/usr/bin/env python3
"""
Test script to verify NER graceful fallback and ner_disabled flag.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig

async def test_ner_fallback():
    """Test that NER graceful fallback works and ner_disabled flag is set."""
    print("Testing NER graceful fallback...")
    
    # Create factory (should gracefully handle missing NER models)
    factory = NormalizationFactory()
    
    # Check that ner_disabled is set correctly
    print(f"NER disabled flag: {factory.ner_disabled}")
    
    # Test normalization
    config = NormalizationConfig(
        language="en",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True
    )
    
    result = await factory.normalize_text("John Smith", config)
    
    print(f"Success: {result.success}")
    print(f"Normalized: '{result.normalized}'")
    print(f"Tokens: {result.tokens}")
    print(f"NER disabled in result: {result.ner_disabled}")
    print(f"Errors: {result.errors}")
    
    # Check trace for ner_disabled flag
    if result.trace:
        for trace in result.trace:
            if trace.flags and 'ner_disabled' in trace.flags:
                print(f"Found ner_disabled flag in trace: {trace.flags}")
                break
        else:
            print("No ner_disabled flag found in trace")
    
    return result.success and result.ner_disabled

if __name__ == "__main__":
    success = asyncio.run(test_ner_fallback())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
