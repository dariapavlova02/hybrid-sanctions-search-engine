# conftest.py - Global pytest configuration and fixtures
"""
Global pytest configuration for AI Normalization Service tests.

This file contains shared fixtures and pytest configuration that applies
to all tests across the entire test suite.
"""

import pytest
import httpx


def pytest_configure():
    """
    Configure pytest before test collection.

    This includes monkey patches for compatibility issues.
    """
    # Fix httpx/starlette compatibility issues
    # Create compatibility layer for TestClient
    try:
        # Import httpx modules that starlette expects
        import httpx._client as httpx_client_module
        import httpx._types as httpx_types_module

        # Make sure httpx has the attributes starlette expects
        if not hasattr(httpx, 'BaseTransport'):
            # Create a BaseTransport based on AsyncBaseTransport
            class BaseTransport(httpx.AsyncBaseTransport):
                pass
            httpx.BaseTransport = BaseTransport

        if not hasattr(httpx, 'Client'):
            # Create synchronous Client based on AsyncClient
            class Client(httpx.AsyncClient):
                pass
            httpx.Client = Client

        # Ensure _client module exists with USE_CLIENT_DEFAULT
        if not hasattr(httpx, '_client'):
            class ClientModule:
                USE_CLIENT_DEFAULT = object()
            httpx._client = ClientModule()

    except ImportError:
        # Fallback to simple monkey patching if modules don't exist
        if not hasattr(httpx, 'BaseTransport'):
            httpx.BaseTransport = httpx.AsyncBaseTransport
        if not hasattr(httpx, 'Client'):
            httpx.Client = httpx.AsyncClient


@pytest.fixture(scope="session", autouse=True)
def setup_httpx_compatibility():
    """
    Auto-fixture to ensure httpx compatibility is maintained.

    This ensures the monkey patch persists throughout the test session.
    """
    if not hasattr(httpx, 'BaseTransport'):
        httpx.BaseTransport = httpx.AsyncBaseTransport
    if not hasattr(httpx, 'Client'):
        httpx.Client = httpx.AsyncClient
    yield