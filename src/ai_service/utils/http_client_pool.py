#!/usr/bin/env python3
"""
HTTP Client Pool Manager

Provides optimized HTTP clients with connection pooling for improved performance.
Supports both sync (requests) and async (httpx) patterns.
"""

import asyncio
from typing import Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import httpx
import requests.adapters
from requests import Session

from .logging_config import get_logger


class HttpClientPool:
    """
    Centralized HTTP client pool manager.

    Features:
    - Connection pooling with configurable limits
    - Both sync and async client support
    - Automatic connection reuse
    - Configurable timeouts and retries
    - Proper cleanup on shutdown
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        max_workers: int = 10,
        default_timeout: float = 30.0
    ):
        """
        Initialize HTTP client pool.

        Args:
            max_connections: Maximum total connections
            max_keepalive_connections: Maximum keepalive connections
            keepalive_expiry: How long to keep connections alive (seconds)
            max_workers: Maximum worker threads for sync operations
            default_timeout: Default request timeout
        """
        self.logger = get_logger(__name__)
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.default_timeout = default_timeout

        # Thread pool for sync operations
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Client instances
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_session: Optional[Session] = None

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def get_async_client(self) -> httpx.AsyncClient:
        """Get async HTTP client with connection pooling."""
        if self._async_client is None:
            async with self._lock:
                if self._async_client is None:
                    # Create async client with basic configuration
                    # Note: Connection pooling will be handled by the underlying aiohttp/httpx transport
                    client_kwargs = {
                        'timeout': self.default_timeout,
                    }

                    # Try to add limits if supported
                    try:
                        # Check if httpx.Limits is available
                        if hasattr(httpx, 'Limits'):
                            client_kwargs['limits'] = httpx.Limits(
                                max_connections=self.max_connections,
                                max_keepalive_connections=self.max_keepalive_connections,
                            )
                    except Exception:
                        # If limits are not supported, just log and continue
                        self.logger.info("httpx.Limits not available, using default connection settings")

                    self._async_client = httpx.AsyncClient(**client_kwargs)
                    self.logger.info(f"Created async HTTP client with max_connections={self.max_connections}")

        return self._async_client

    def get_sync_session(self) -> Session:
        """Get sync HTTP session with connection pooling."""
        if self._sync_session is None:
            self._sync_session = Session()

            # Configure connection pool adapter
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=25,  # Number of connection pools to cache
                pool_maxsize=self.max_keepalive_connections,  # Maximum number of connections in the pool
                max_retries=3,  # Number of retries for failed requests
                pool_block=False  # Don't block if pool is full
            )

            # Mount adapter for both HTTP and HTTPS
            self._sync_session.mount('http://', adapter)
            self._sync_session.mount('https://', adapter)

            # Set default timeout
            self._sync_session.timeout = self.default_timeout

            self.logger.info(f"Created sync HTTP session with pool_maxsize={self.max_keepalive_connections}")

        return self._sync_session

    async def async_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make async HTTP request using pooled client.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            HTTP response
        """
        client = await self.get_async_client()
        return await client.request(method, url, **kwargs)

    async def async_post_json(
        self,
        url: str,
        data: Dict[str, Any],
        timeout: Optional[float] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make async POST request with JSON data.

        Args:
            url: Request URL
            data: JSON data to send
            timeout: Request timeout
            **kwargs: Additional request parameters

        Returns:
            HTTP response
        """
        client = await self.get_async_client()
        return await client.post(
            url,
            json=data,
            timeout=timeout or self.default_timeout,
            **kwargs
        )

    def sync_post_json(
        self,
        url: str,
        data: Dict[str, Any],
        timeout: Optional[float] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make sync POST request with JSON data using pooled session.

        Args:
            url: Request URL
            data: JSON data to send
            timeout: Request timeout
            **kwargs: Additional request parameters

        Returns:
            HTTP response
        """
        session = self.get_sync_session()
        return session.post(
            url,
            json=data,
            timeout=timeout or self.default_timeout,
            **kwargs
        )

    def sync_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make sync HTTP request using pooled session.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            HTTP response
        """
        session = self.get_sync_session()
        return session.request(method, url, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {
            "max_connections": self.max_connections,
            "max_keepalive_connections": self.max_keepalive_connections,
            "keepalive_expiry": self.keepalive_expiry,
            "default_timeout": self.default_timeout,
            "async_client_created": self._async_client is not None,
            "sync_session_created": self._sync_session is not None,
        }

        # Add async client stats if available
        if self._async_client:
            client_stats = {}
            # Try to get client status, different httpx versions have different APIs
            try:
                client_stats["is_closed"] = getattr(self._async_client, 'is_closed', False)
            except AttributeError:
                client_stats["status"] = "active"
            stats["async_client"] = client_stats

        return stats

    async def cleanup(self) -> None:
        """Cleanup all resources."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
            self.logger.info("Closed async HTTP client")

        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None
            self.logger.info("Closed sync HTTP session")

        if self._executor:
            self._executor.shutdown(wait=True)
            self.logger.info("Shutdown HTTP client thread pool")


# Global instance for shared use
_global_pool: Optional[HttpClientPool] = None


def get_http_pool() -> HttpClientPool:
    """Get global HTTP client pool instance."""
    global _global_pool
    if _global_pool is None:
        _global_pool = HttpClientPool()
    return _global_pool


async def cleanup_global_pool() -> None:
    """Cleanup global HTTP client pool."""
    global _global_pool
    if _global_pool:
        await _global_pool.cleanup()
        _global_pool = None