"""
Configuration for property-based tests

This module provides pytest fixtures and configuration for property-based
testing of the normalization service.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@pytest.fixture(scope="module")
def normalization_service():
    """Module-scoped normalization service fixture."""
    from src.ai_service.layers.normalization.normalization_service import NormalizationService
    service = NormalizationService()
    yield service
    # Cleanup caches
    if hasattr(service, 'normalization_factory'):
        if hasattr(service.normalization_factory, '_normalization_cache'):
            service.normalization_factory._normalization_cache.clear()


@pytest.fixture(scope="session")
def flags():
    """Session-scoped flags fixture."""
    return {
        "remove_stop_words": True,
        "preserve_names": True,
        "enable_advanced_features": True,
        "strict_stopwords": True,
        "preserve_feminine_suffix_uk": False,
        "enable_spacy_uk_ner": False
    }


def pytest_addoption(parser):
    """Add command line options for property-based tests."""
    # Only add options if they don't already exist
    if not any(opt.dest == 'property_max_examples' for opt in parser._anonymous.options):
        parser.addoption(
            "--property-max-examples",
            type=int,
            default=1000,
            help="Maximum examples for property-based tests"
        )


# Pytest configuration for property-based tests
def pytest_configure(config):
    """Configure pytest for property-based testing."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "property: mark test as property-based test"
    )
    config.addinivalue_line(
        "markers", "invariant: mark test as invariant test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for property-based tests."""
    for item in items:
        # Mark property-based tests
        if "test_normalization_properties" in item.nodeid:
            item.add_marker(pytest.mark.property)
            item.add_marker(pytest.mark.invariant)
        
        # Mark slow tests
        if "slow" in item.name or "invariant" in item.name:
            item.add_marker(pytest.mark.slow)
