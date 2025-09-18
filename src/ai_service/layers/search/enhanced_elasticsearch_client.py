"""Enhanced Elasticsearch client with robust health checks, retries, and monitoring."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import httpx
import json

from ...utils.logging_config import get_logger
from .config import HybridSearchConfig, ElasticsearchConfig


class HealthStatus(Enum):
    """Elasticsearch cluster health status."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNREACHABLE = "unreachable"


class RetryPolicy:
    """Configurable retry policy for Elasticsearch operations."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-based)."""
        if attempt == 0:
            return 0

        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter

        return delay


class EnhancedElasticsearchClient:
    """Enhanced Elasticsearch client with health monitoring and retry logic."""

    def __init__(
        self,
        config: Optional[HybridSearchConfig] = None,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        retry_policy: Optional[RetryPolicy] = None
    ) -> None:
        self.logger = get_logger(__name__)
        self.config = config or HybridSearchConfig.from_env()
        self.es_config: ElasticsearchConfig = self.config.elasticsearch
        self._transport = transport
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._lock = asyncio.Lock()
        self._auth = self._build_auth()
        self._headers = self._build_headers()
        self.retry_policy = retry_policy or RetryPolicy()

        # Health monitoring
        self._last_health_check: Optional[datetime] = None
        self._cached_health_status: Optional[Dict[str, Any]] = None
        self._health_cache_ttl: float = 30.0  # seconds

        # Connection pool status
        self._connection_failures: Dict[str, int] = {}
        self._circuit_breaker: Dict[str, bool] = {}

    def _build_auth(self) -> Optional[httpx.Auth]:
        """Build authentication for Elasticsearch."""
        if self.es_config.username and self.es_config.password:
            return httpx.BasicAuth(self.es_config.username, self.es_config.password)
        return None

    def _build_headers(self) -> Dict[str, str]:
        """Build default headers."""
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ai-service-enhanced-client/1.0"
        }
        if self.es_config.api_key:
            headers["Authorization"] = f"ApiKey {self.es_config.api_key}"
        return headers

    def _timeout(self, operation_type: str = "default") -> httpx.Timeout:
        """Get timeout for specific operation type."""
        base_timeout = self.es_config.timeout

        # Different timeouts for different operations
        timeouts = {
            "health": min(base_timeout, 5.0),
            "search": base_timeout,
            "index": base_timeout * 2,
            "bulk": base_timeout * 3,
        }

        timeout_value = timeouts.get(operation_type, base_timeout)
        return httpx.Timeout(timeout_value, connect=timeout_value * 0.5)

    def get_hosts(self) -> List[str]:
        """Return normalized host list, prioritizing healthy hosts."""
        all_hosts = self.es_config.normalized_hosts()

        # Filter out hosts in circuit breaker mode
        healthy_hosts = [
            host for host in all_hosts
            if not self._circuit_breaker.get(host, False)
        ]

        return healthy_hosts if healthy_hosts else all_hosts

    async def _create_client(self, base_url: str, operation_type: str = "default") -> httpx.AsyncClient:
        """Create HTTP client for specific host and operation type."""
        verify: Any
        if self.es_config.ca_certs:
            verify = self.es_config.ca_certs
        else:
            verify = self.es_config.verify_certs

        return httpx.AsyncClient(
            base_url=base_url,
            headers=self._headers,
            auth=self._auth,
            timeout=self._timeout(operation_type),
            verify=verify,
            transport=self._transport,
            # Connection pool settings
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def get_client(self, host: Optional[str] = None, operation_type: str = "default") -> httpx.AsyncClient:
        """Get cached client for host, creating it on first use."""
        available_hosts = self.get_hosts()
        if not available_hosts:
            raise RuntimeError("No healthy Elasticsearch hosts available")

        base_host = host or available_hosts[0]

        # Check circuit breaker
        if self._circuit_breaker.get(base_host, False):
            self.logger.warning(f"Host {base_host} is in circuit breaker mode")
            # Try next available host
            for fallback_host in available_hosts:
                if not self._circuit_breaker.get(fallback_host, False):
                    base_host = fallback_host
                    break
            else:
                raise RuntimeError("All Elasticsearch hosts are in circuit breaker mode")

        client_key = f"{base_host}:{operation_type}"
        async with self._lock:
            client = self._clients.get(client_key)
            if client is None:
                client = await self._create_client(base_host, operation_type)
                self._clients[client_key] = client

        return client

    async def _record_failure(self, host: str) -> None:
        """Record connection failure for host."""
        self._connection_failures[host] = self._connection_failures.get(host, 0) + 1

        # Activate circuit breaker after 3 consecutive failures
        if self._connection_failures[host] >= 3:
            self._circuit_breaker[host] = True
            self.logger.warning(f"Circuit breaker activated for host {host}")

            # Schedule circuit breaker reset (30 seconds)
            asyncio.create_task(self._reset_circuit_breaker(host, 30.0))

    async def _record_success(self, host: str) -> None:
        """Record successful connection for host."""
        if host in self._connection_failures:
            del self._connection_failures[host]
        if host in self._circuit_breaker:
            del self._circuit_breaker[host]

    async def _reset_circuit_breaker(self, host: str, delay: float) -> None:
        """Reset circuit breaker for host after delay."""
        await asyncio.sleep(delay)
        if host in self._circuit_breaker:
            del self._circuit_breaker[host]
            self.logger.info(f"Circuit breaker reset for host {host}")

    async def execute_with_retry(
        self,
        operation: callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute operation with retry logic."""
        last_exception = None

        for attempt in range(self.retry_policy.max_attempts):
            try:
                # Add delay for retries
                if attempt > 0:
                    delay = self.retry_policy.calculate_delay(attempt)
                    if delay > 0:
                        self.logger.debug(f"Retrying {operation_name} in {delay:.2f}s (attempt {attempt + 1})")
                        await asyncio.sleep(delay)

                result = await operation(*args, **kwargs)

                # Record success for host tracking
                if 'host' in kwargs:
                    await self._record_success(kwargs['host'])

                return result

            except httpx.TimeoutException as e:
                last_exception = e
                self.logger.warning(f"{operation_name} timeout (attempt {attempt + 1}): {e}")
                if 'host' in kwargs:
                    await self._record_failure(kwargs['host'])

            except httpx.NetworkError as e:
                last_exception = e
                self.logger.warning(f"{operation_name} network error (attempt {attempt + 1}): {e}")
                if 'host' in kwargs:
                    await self._record_failure(kwargs['host'])

            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    self.logger.error(f"{operation_name} client error: {e}")
                    raise

                last_exception = e
                self.logger.warning(f"{operation_name} server error (attempt {attempt + 1}): {e}")
                if 'host' in kwargs:
                    await self._record_failure(kwargs['host'])

        # All retries exhausted
        self.logger.error(f"{operation_name} failed after {self.retry_policy.max_attempts} attempts")
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"{operation_name} failed after {self.retry_policy.max_attempts} attempts")

    async def enhanced_health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with caching."""
        now = datetime.now()

        # Use cached result if available and fresh
        if (self._last_health_check and
            self._cached_health_status and
            (now - self._last_health_check).total_seconds() < self._health_cache_ttl):
            return self._cached_health_status

        async def _check_host_health(host: str) -> Dict[str, Any]:
            """Check health for a single host."""
            host_result: Dict[str, Any] = {
                "host": host,
                "status": HealthStatus.UNREACHABLE.value,
                "circuit_breaker": self._circuit_breaker.get(host, False),
                "failure_count": self._connection_failures.get(host, 0)
            }

            if self._circuit_breaker.get(host, False):
                host_result["error"] = "Circuit breaker active"
                return host_result

            start_time = time.time()

            try:
                client = await self.get_client(host, "health")

                # Check cluster health
                health_response = await client.get("/_cluster/health")
                elapsed_ms = (time.time() - start_time) * 1000

                if health_response.is_success:
                    health_data = health_response.json()
                    cluster_status = health_data.get("status", "unknown").lower()

                    # Map Elasticsearch status to our enum
                    if cluster_status in ["green", "yellow", "red"]:
                        host_result["status"] = cluster_status
                    else:
                        host_result["status"] = HealthStatus.RED.value

                    host_result.update({
                        "cluster_name": health_data.get("cluster_name"),
                        "number_of_nodes": health_data.get("number_of_nodes"),
                        "number_of_data_nodes": health_data.get("number_of_data_nodes"),
                        "active_primary_shards": health_data.get("active_primary_shards"),
                        "active_shards": health_data.get("active_shards"),
                        "relocating_shards": health_data.get("relocating_shards"),
                        "initializing_shards": health_data.get("initializing_shards"),
                        "unassigned_shards": health_data.get("unassigned_shards"),
                        "elapsed_ms": round(elapsed_ms, 2)
                    })

                    # Additional node info
                    try:
                        nodes_response = await client.get("/_nodes/_local/stats")
                        if nodes_response.is_success:
                            nodes_data = nodes_response.json()
                            if "nodes" in nodes_data:
                                # Get first node stats
                                node_stats = next(iter(nodes_data["nodes"].values()), {})
                                if node_stats:
                                    jvm = node_stats.get("jvm", {})
                                    host_result.update({
                                        "jvm_heap_used_percent": jvm.get("mem", {}).get("heap_used_percent"),
                                        "jvm_uptime": jvm.get("uptime_in_millis"),
                                    })
                    except Exception as e:
                        self.logger.debug(f"Could not fetch node stats for {host}: {e}")

                    await self._record_success(host)
                else:
                    host_result["error"] = f"HTTP {health_response.status_code}: {health_response.text}"
                    await self._record_failure(host)

            except Exception as e:
                host_result["error"] = str(e)
                host_result["elapsed_ms"] = (time.time() - start_time) * 1000
                await self._record_failure(host)

            return host_result

        # Check all hosts
        all_hosts = self.es_config.normalized_hosts()
        results = []

        # Use asyncio.gather to check all hosts concurrently
        host_checks = [_check_host_health(host) for host in all_hosts]
        results = await asyncio.gather(*host_checks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "host": all_hosts[i],
                    "status": HealthStatus.UNREACHABLE.value,
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        # Determine overall status
        statuses = [r.get("status") for r in processed_results]
        overall_status = HealthStatus.UNREACHABLE.value

        if any(s == HealthStatus.GREEN.value for s in statuses):
            overall_status = HealthStatus.GREEN.value
        elif any(s == HealthStatus.YELLOW.value for s in statuses):
            overall_status = HealthStatus.YELLOW.value
        elif any(s == HealthStatus.RED.value for s in statuses):
            overall_status = HealthStatus.RED.value

        health_result = {
            "overall_status": overall_status,
            "healthy_hosts": sum(1 for r in processed_results if r.get("status") in [HealthStatus.GREEN.value, HealthStatus.YELLOW.value]),
            "total_hosts": len(all_hosts),
            "hosts": processed_results,
            "timestamp": now.isoformat(),
            "cache_ttl_seconds": self._health_cache_ttl,
            "circuit_breakers_active": sum(1 for host in all_hosts if self._circuit_breaker.get(host, False))
        }

        # Cache the result
        self._last_health_check = now
        self._cached_health_status = health_result

        return health_result

    async def is_healthy(self, require_green: bool = False) -> bool:
        """Quick health check returning boolean."""
        try:
            health = await self.enhanced_health_check()
            status = health.get("overall_status")

            if require_green:
                return status == HealthStatus.GREEN.value
            else:
                return status in [HealthStatus.GREEN.value, HealthStatus.YELLOW.value]

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    async def wait_for_healthy(
        self,
        timeout: float = 60.0,
        check_interval: float = 2.0,
        require_green: bool = False
    ) -> bool:
        """Wait for cluster to become healthy within timeout."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if await self.is_healthy(require_green=require_green):
                    self.logger.info("Elasticsearch cluster is healthy")
                    return True

                self.logger.debug("Waiting for Elasticsearch cluster to become healthy...")
                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.debug(f"Health check error while waiting: {e}")
                await asyncio.sleep(check_interval)

        self.logger.error(f"Elasticsearch cluster did not become healthy within {timeout}s")
        return False

    async def get_cluster_stats(self) -> Dict[str, Any]:
        """Get comprehensive cluster statistics."""
        async def _get_stats() -> Dict[str, Any]:
            client = await self.get_client(operation_type="health")

            stats = {}

            # Cluster stats
            cluster_stats_response = await client.get("/_cluster/stats")
            if cluster_stats_response.is_success:
                stats["cluster"] = cluster_stats_response.json()

            # Indices stats
            indices_stats_response = await client.get("/_stats")
            if indices_stats_response.is_success:
                stats["indices"] = indices_stats_response.json()

            return stats

        try:
            return await self.execute_with_retry(
                _get_stats,
                "get_cluster_stats"
            )
        except Exception as e:
            self.logger.error(f"Failed to get cluster stats: {e}")
            return {"error": str(e)}

    async def close(self) -> None:
        """Close all managed clients and reset state."""
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()

        # Close clients concurrently
        close_tasks = [client.aclose() for client in clients]
        results = await asyncio.gather(*close_tasks, return_exceptions=True)

        # Log any errors during cleanup
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"Error closing Elasticsearch client {i}: {result}")

        # Reset monitoring state
        self._connection_failures.clear()
        self._circuit_breaker.clear()
        self._last_health_check = None
        self._cached_health_status = None

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection pool status."""
        return {
            "active_clients": len(self._clients),
            "connection_failures": dict(self._connection_failures),
            "circuit_breakers": dict(self._circuit_breaker),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "health_cache_age_seconds": (
                (datetime.now() - self._last_health_check).total_seconds()
                if self._last_health_check else None
            )
        }