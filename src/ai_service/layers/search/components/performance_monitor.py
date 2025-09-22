"""
Performance monitoring and metrics collection for search operations.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..contracts import SearchMetrics


@dataclass
class QueryPerformanceEntry:
    """Single query performance record."""
    timestamp: datetime
    query: str
    search_mode: str
    processing_time_ms: float
    result_count: int
    cache_hit: bool = False
    error: Optional[str] = None


@dataclass
class SearchPerformanceStats:
    """Aggregated search performance statistics."""
    total_requests: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    requests_per_second: float = 0.0
    by_mode: Dict[str, Dict[str, float]] = field(default_factory=dict)


class PerformanceMonitor:
    """Monitors and tracks search performance metrics."""

    def __init__(self, history_limit: int = 10000):
        """Initialize performance monitor."""
        self.history_limit = history_limit

        # Core metrics
        self.metrics = SearchMetrics()

        # Performance history
        self._query_performance: List[QueryPerformanceEntry] = []
        self._performance_lock = asyncio.Lock()

        # Request timing
        self._request_times: List[float] = []
        self._ac_request_times: List[float] = []
        self._vector_request_times: List[float] = []

        # Rate limiting tracking
        self._rate_limiter: Dict[str, List[datetime]] = {}
        self._rate_limit_lock = asyncio.Lock()

    async def record_query_performance(
        self,
        query: str,
        search_mode: str,
        processing_time_ms: float,
        result_count: int,
        cache_hit: bool = False,
        error: Optional[str] = None
    ) -> None:
        """Record query performance metrics."""
        async with self._performance_lock:
            entry = QueryPerformanceEntry(
                timestamp=datetime.now(),
                query=self._sanitize_query_for_logging(query),
                search_mode=search_mode,
                processing_time_ms=processing_time_ms,
                result_count=result_count,
                cache_hit=cache_hit,
                error=error
            )

            self._query_performance.append(entry)

            # Maintain history limit
            if len(self._query_performance) > self.history_limit:
                self._query_performance = self._query_performance[-self.history_limit:]

            # Update core metrics
            self._update_core_metrics(
                success=error is None,
                processing_time_ms=processing_time_ms,
                result_count=result_count
            )

    async def get_performance_stats(
        self,
        time_window_minutes: Optional[int] = None
    ) -> SearchPerformanceStats:
        """Get aggregated performance statistics."""
        async with self._performance_lock:
            # Filter by time window if specified
            entries = self._query_performance
            if time_window_minutes:
                cutoff = datetime.now() - timedelta(minutes=time_window_minutes)
                entries = [e for e in entries if e.timestamp >= cutoff]

            if not entries:
                return SearchPerformanceStats()

            # Calculate basic stats
            total_requests = len(entries)
            processing_times = [e.processing_time_ms for e in entries]
            cache_hits = sum(1 for e in entries if e.cache_hit)
            errors = sum(1 for e in entries if e.error is not None)

            avg_response_time = sum(processing_times) / len(processing_times)

            # Calculate percentiles
            sorted_times = sorted(processing_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))

            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else 0
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else 0

            # Calculate rates
            cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
            error_rate = errors / total_requests if total_requests > 0 else 0

            # Calculate RPS based on time window
            if time_window_minutes and entries:
                earliest = min(e.timestamp for e in entries)
                latest = max(e.timestamp for e in entries)
                duration_seconds = (latest - earliest).total_seconds()
                requests_per_second = total_requests / duration_seconds if duration_seconds > 0 else 0
            else:
                requests_per_second = 0

            # Group by search mode
            by_mode = {}
            for mode in set(e.search_mode for e in entries):
                mode_entries = [e for e in entries if e.search_mode == mode]
                mode_times = [e.processing_time_ms for e in mode_entries]
                mode_cache_hits = sum(1 for e in mode_entries if e.cache_hit)
                mode_errors = sum(1 for e in mode_entries if e.error is not None)

                by_mode[mode] = {
                    "count": len(mode_entries),
                    "avg_response_time_ms": sum(mode_times) / len(mode_times),
                    "cache_hit_rate": mode_cache_hits / len(mode_entries),
                    "error_rate": mode_errors / len(mode_entries)
                }

            return SearchPerformanceStats(
                total_requests=total_requests,
                avg_response_time_ms=avg_response_time,
                p95_response_time_ms=p95_response_time,
                p99_response_time_ms=p99_response_time,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                requests_per_second=requests_per_second,
                by_mode=by_mode
            )

    async def clear_performance_history(self) -> None:
        """Clear all performance history."""
        async with self._performance_lock:
            self._query_performance.clear()
            self._request_times.clear()
            self._ac_request_times.clear()
            self._vector_request_times.clear()

    async def check_rate_limit(
        self,
        client_id: str = "default",
        max_requests_per_minute: int = 100
    ) -> bool:
        """Check if client has exceeded rate limit."""
        async with self._rate_limit_lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)

            # Initialize client entry if not exists
            if client_id not in self._rate_limiter:
                self._rate_limiter[client_id] = []

            # Clean old requests
            self._rate_limiter[client_id] = [
                timestamp for timestamp in self._rate_limiter[client_id]
                if timestamp >= cutoff
            ]

            # Check if under limit
            if len(self._rate_limiter[client_id]) >= max_requests_per_minute:
                return False

            # Record this request
            self._rate_limiter[client_id].append(now)
            return True

    def get_core_metrics(self) -> SearchMetrics:
        """Get core search metrics."""
        return self.metrics

    def update_timing(self, mode: str, duration_ms: float) -> None:
        """Update timing metrics for specific search mode."""
        if mode == "ac":
            self._ac_request_times.append(duration_ms)
            # Keep only recent times for memory efficiency
            if len(self._ac_request_times) > 1000:
                self._ac_request_times = self._ac_request_times[-1000:]
        elif mode == "vector":
            self._vector_request_times.append(duration_ms)
            if len(self._vector_request_times) > 1000:
                self._vector_request_times = self._vector_request_times[-1000:]

        self._request_times.append(duration_ms)
        if len(self._request_times) > 1000:
            self._request_times = self._request_times[-1000:]

    def _update_core_metrics(
        self,
        success: bool,
        processing_time_ms: float,
        result_count: int,
        avg_score: float = 0.0
    ) -> None:
        """Update core metrics."""
        self.metrics.total_requests += 1

        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1

        # Update timing stats
        if self._request_times:
            self.metrics.average_response_time_ms = sum(self._request_times) / len(self._request_times)

        # Update result stats
        self.metrics.total_results_returned += result_count
        if result_count > 0:
            self.metrics.requests_with_results += 1

        # Update score stats if provided
        if avg_score > 0:
            if hasattr(self.metrics, 'average_relevance_score'):
                # Simple running average
                current_avg = getattr(self.metrics, 'average_relevance_score', 0.0)
                count = self.metrics.successful_requests
                new_avg = ((current_avg * (count - 1)) + avg_score) / count
                setattr(self.metrics, 'average_relevance_score', new_avg)

    def _sanitize_query_for_logging(self, query: str) -> str:
        """Sanitize query for safe logging."""
        # Remove potential sensitive information
        if len(query) > 100:
            query = query[:100] + "..."

        # Remove special characters that might cause issues
        import re
        sanitized = re.sub(r'[^\w\s\-\.]', '', query)
        return sanitized.strip()

    async def get_timing_stats(self) -> Dict[str, Any]:
        """Get detailed timing statistics."""
        stats = {
            "overall": self._calculate_timing_stats(self._request_times),
            "ac_search": self._calculate_timing_stats(self._ac_request_times),
            "vector_search": self._calculate_timing_stats(self._vector_request_times)
        }
        return stats

    def _calculate_timing_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate statistics for a list of timing measurements."""
        if not times:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}

        sorted_times = sorted(times)
        count = len(times)

        return {
            "count": count,
            "avg": sum(times) / count,
            "min": min(times),
            "max": max(times),
            "p95": sorted_times[int(0.95 * count)] if count > 0 else 0.0
        }