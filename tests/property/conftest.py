"""
Configuration for property-based tests

This module provides pytest fixtures and configuration for property-based
testing of the hybrid search system.
"""

import pytest
import asyncio
from typing import AsyncGenerator

from test_anti_cheat_regression import HybridSearchTester


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def search_tester() -> AsyncGenerator[HybridSearchTester, None]:
    """
    Create a search tester instance for the entire test session.
    
    This fixture ensures that the search tester is properly initialized
    and cleaned up for all property-based tests.
    """
    tester = HybridSearchTester()
    
    # Verify Elasticsearch is available
    try:
        health_response = await tester.client.get(f"{tester.es_url}/_cluster/health")
        if health_response.status_code != 200:
            pytest.skip("Elasticsearch is not available")
    except Exception:
        pytest.skip("Elasticsearch is not available")
    
    yield tester
    
    # Cleanup
    await tester.cleanup()


@pytest.fixture(scope="function")
async def isolated_search_tester() -> AsyncGenerator[HybridSearchTester, None]:
    """
    Create an isolated search tester instance for each test function.
    
    This fixture provides complete isolation between test functions,
    ensuring that tests don't interfere with each other.
    """
    tester = HybridSearchTester()
    
    # Verify Elasticsearch is available
    try:
        health_response = await tester.client.get(f"{tester.es_url}/_cluster/health")
        if health_response.status_code != 200:
            pytest.skip("Elasticsearch is not available")
    except Exception:
        pytest.skip("Elasticsearch is not available")
    
    yield tester
    
    # Cleanup
    await tester.cleanup()


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
        if "test_anti_cheat_regression" in item.nodeid:
            item.add_marker(pytest.mark.property)
            item.add_marker(pytest.mark.invariant)
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if "slow" in item.name or "invariant" in item.name:
            item.add_marker(pytest.mark.slow)
