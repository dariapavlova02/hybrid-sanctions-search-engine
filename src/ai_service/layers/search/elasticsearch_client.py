"""Elasticsearch client factory using AsyncElasticsearch."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ElasticsearchException

from ...utils.logging_config import get_logger
from .config import HybridSearchConfig, ElasticsearchConfig


class ElasticsearchClientFactory:
    """Factory that provides configured AsyncElasticsearch clients."""

    def __init__(
        self,
        config: Optional[HybridSearchConfig] = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self.config = config or HybridSearchConfig.from_env()
        self.es_config: ElasticsearchConfig = self.config.elasticsearch
        self._clients: Dict[str, AsyncElasticsearch] = {}
        self._lock = asyncio.Lock()

    def _build_es_config(self) -> Dict[str, Any]:
        """Build Elasticsearch client configuration."""
        es_config = {
            "hosts": self.es_config.normalized_hosts(),
            "timeout": self.es_config.timeout,
            "max_retries": self.es_config.max_retries,
            "retry_on_timeout": self.es_config.retry_on_timeout,
            "verify_certs": self.es_config.verify_certs,
        }
        
        # Add authentication
        if self.es_config.api_key:
            es_config["api_key"] = self.es_config.api_key
        elif self.es_config.username and self.es_config.password:
            es_config["basic_auth"] = (self.es_config.username, self.es_config.password)
        
        # Add CA certificates if provided
        if self.es_config.ca_certs:
            es_config["ca_certs"] = self.es_config.ca_certs
            
        return es_config

    def get_hosts(self) -> List[str]:
        """Return normalized host list used by the factory."""
        return self.es_config.normalized_hosts()

    async def _create_client(self, host: str) -> AsyncElasticsearch:
        """Create a new AsyncElasticsearch client for the given host."""
        es_config = self._build_es_config()
        # Override hosts with single host for this client
        es_config["hosts"] = [host]
        
        return AsyncElasticsearch(**es_config)

    async def get_client(self, host: Optional[str] = None) -> AsyncElasticsearch:
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
                await client.close()
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
                # Use Elasticsearch cluster health API
                response = await client.cluster.health(
                    timeout=f"{int(self.es_config.smoke_test_timeout)}s"
                )
                host_result["elapsed_ms"] = (datetime.now() - start).total_seconds() * 1000
                if response.get("status") in ["green", "yellow"]:
                    host_result["status"] = "healthy"
                    host_result["details"] = response
                    overall_status = "healthy"
                else:
                    host_result["error"] = f"Cluster status: {response.get('status')}"
            except ElasticsearchException as exc:
                host_result["error"] = str(exc)
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
