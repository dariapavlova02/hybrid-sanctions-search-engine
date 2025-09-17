"""Elasticsearch client factory built on top of httpx.AsyncClient."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ...utils.logging_config import get_logger
from .config import HybridSearchConfig, ElasticsearchConfig


class ElasticsearchClientFactory:
    """Factory that provides configured Async HTTP clients for Elasticsearch."""

    def __init__(
        self,
        config: Optional[HybridSearchConfig] = None,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self.config = config or HybridSearchConfig.from_env()
        self.es_config: ElasticsearchConfig = self.config.elasticsearch
        self._transport = transport
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._lock = asyncio.Lock()
        self._auth = self._build_auth()
        self._headers = self._build_headers()

    def _build_auth(self) -> Optional[httpx.Auth]:
        if self.es_config.username and self.es_config.password:
            return httpx.BasicAuth(self.es_config.username, self.es_config.password)
        return None

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.es_config.api_key:
            headers["Authorization"] = f"ApiKey {self.es_config.api_key}"
        return headers

    def _timeout(self) -> httpx.Timeout:
        timeout_value = self.es_config.timeout
        return httpx.Timeout(timeout_value, connect=timeout_value)

    def get_hosts(self) -> List[str]:
        """Return normalized host list used by the factory."""
        return self.es_config.normalized_hosts()

    async def _create_client(self, base_url: str) -> httpx.AsyncClient:
        verify: Any
        if self.es_config.ca_certs:
            verify = self.es_config.ca_certs
        else:
            verify = self.es_config.verify_certs

        return httpx.AsyncClient(
            base_url=base_url,
            headers=self._headers,
            auth=self._auth,
            timeout=self._timeout(),
            verify=verify,
            transport=self._transport,
        )

    async def get_client(self, host: Optional[str] = None) -> httpx.AsyncClient:
        """Return cached client for host, creating it on first use."""
        base_host = host or self.get_hosts()[0]
        if not base_host:
            raise RuntimeError("No Elasticsearch hosts configured")

        async with self._lock:
            client = self._clients.get(base_host)
            if client is None:
                client = await self._create_client(base_host)
                self._clients[base_host] = client
        return client

    async def close(self) -> None:
        """Close all managed clients."""
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()

        for client in clients:
            try:
                await client.aclose()
            except Exception as exc:  # pragma: no cover - best effort cleanup
                self.logger.warning(f"Error closing Elasticsearch client: {exc}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check against configured hosts."""
        results = []
        overall_status = "unhealthy"

        for host in self.get_hosts():
            client = await self.get_client(host)
            host_result: Dict[str, Any] = {"host": host, "status": "unhealthy"}
            start = datetime.now()
            try:
                response = await client.get(
                    self.es_config.healthcheck_path,
                    timeout=self.es_config.smoke_test_timeout,
                )
                host_result["status_code"] = response.status_code
                host_result["elapsed_ms"] = (datetime.now() - start).total_seconds() * 1000
                if response.is_success:
                    host_result["status"] = "healthy"
                    host_result["details"] = await response.json()
                    overall_status = "healthy"
                else:
                    host_result["error"] = response.text
            except Exception as exc:  # pragma: no cover - network errors depend on runtime
                host_result["error"] = str(exc)
            results.append(host_result)

        return {
            "status": overall_status,
            "hosts": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def smoke_test(self) -> bool:
        """Run a lightweight connectivity check against Elasticsearch."""
        health = await self.health_check()
        return health.get("status") == "healthy"
