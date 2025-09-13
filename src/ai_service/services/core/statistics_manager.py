"""
Statistics Manager
Centralized statistics tracking and reporting for AI services.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils import get_logger


@dataclass
class ProcessingStats:
    """Statistics for text processing operations"""
    
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    smart_filter_skipped: int = 0
    smart_filter_processed: int = 0
    
    # Stage-specific timings
    stage_timings: Dict[str, List[float]] = field(default_factory=dict)
    
    def update_processing(self, processing_time: float, success: bool) -> None:
        """Update processing statistics"""
        
        self.total_processed += 1
        self.total_time += processing_time
        
        if success:
            self.successful += 1
        else:
            self.failed += 1
        
        # Update average time
        if self.total_processed > 0:
            self.average_time = self.total_time / self.total_processed
    
    def update_cache_stats(self, hit: bool) -> None:
        """Update cache statistics"""
        
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def update_smart_filter_stats(self, processed: bool) -> None:
        """Update smart filter statistics"""
        
        if processed:
            self.smart_filter_processed += 1
        else:
            self.smart_filter_skipped += 1
    
    def record_stage_timing(self, stage_name: str, duration: float) -> None:
        """Record timing for a processing stage"""
        
        if stage_name not in self.stage_timings:
            self.stage_timings[stage_name] = []
        
        self.stage_timings[stage_name].append(duration)
    
    def get_stage_averages(self) -> Dict[str, float]:
        """Get average timing for each stage"""
        
        averages = {}
        for stage_name, timings in self.stage_timings.items():
            if timings:
                averages[stage_name] = sum(timings) / len(timings)
            else:
                averages[stage_name] = 0.0
        
        return averages
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return self.successful / self.total_processed if self.total_processed > 0 else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_cache_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0


@dataclass
class ServiceHealthStats:
    """Health statistics for individual services"""
    
    service_name: str
    status: str = "inactive"  # inactive, active, error, shutdown
    initialization_time: Optional[datetime] = None
    last_operation_time: Optional[datetime] = None
    operation_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    def record_operation(self, success: bool, error_message: Optional[str] = None) -> None:
        """Record a service operation"""
        
        self.last_operation_time = datetime.now()
        self.operation_count += 1
        
        if not success:
            self.error_count += 1
            self.last_error = error_message
            self.last_error_time = datetime.now()
            
            # Update status to error if too many failures
            if self.error_count > 10:
                self.status = "error"


class StatisticsManager:
    """
    Centralized manager for all statistics tracking and reporting
    """
    
    def __init__(self):
        """Initialize statistics manager"""
        
        self.logger = get_logger(__name__)
        
        # Main processing statistics
        self.processing_stats = ProcessingStats()
        
        # Service health tracking
        self.service_health: Dict[str, ServiceHealthStats] = {}
        
        # Memory logging controls (optional diagnostic feature)
        self._memlog_interval = self._get_memlog_interval()
        self._processed_since_memlog = 0
        
        self.logger.info("Statistics manager initialized")
    
    def _get_memlog_interval(self) -> int:
        """Get memory logging interval from environment"""
        
        try:
            return int(os.getenv("AI_SERVICE_MEMLOG_INTERVAL", "0"))
        except Exception:
            return 0
    
    def register_service(self, service_name: str, status: str = "active") -> None:
        """Register a service for health tracking"""
        
        self.service_health[service_name] = ServiceHealthStats(
            service_name=service_name,
            status=status,
            initialization_time=datetime.now()
        )
        
        self.logger.debug(f"Registered service: {service_name}")
    
    def update_service_status(self, service_name: str, status: str) -> None:
        """Update service status"""
        
        if service_name in self.service_health:
            self.service_health[service_name].status = status
            self.logger.debug(f"Updated {service_name} status to: {status}")
    
    def record_service_operation(
        self, service_name: str, success: bool, error_message: Optional[str] = None
    ) -> None:
        """Record a service operation"""
        
        if service_name not in self.service_health:
            self.register_service(service_name)
        
        self.service_health[service_name].record_operation(success, error_message)
    
    def update_processing_stats(self, processing_time: float, success: bool) -> None:
        """Update main processing statistics"""
        
        self.processing_stats.update_processing(processing_time, success)
        
        # Optional memory logging
        if self._memlog_interval > 0:
            self._processed_since_memlog += 1
            if self._processed_since_memlog % self._memlog_interval == 0:
                self._log_memory_snapshot()
    
    def update_cache_stats(self, hit: bool) -> None:
        """Update cache statistics"""
        
        self.processing_stats.update_cache_stats(hit)
    
    def update_smart_filter_stats(self, processed: bool) -> None:
        """Update smart filter statistics"""
        
        self.processing_stats.update_smart_filter_stats(processed)
    
    def record_stage_timings(self, stage_timings: Dict[str, float]) -> None:
        """Record timings for processing stages"""
        
        for stage_name, duration in stage_timings.items():
            self.processing_stats.record_stage_timing(stage_name, duration)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all services"""
        
        return {
            "processing": {
                "total_processed": self.processing_stats.total_processed,
                "successful": self.processing_stats.successful,
                "failed": self.processing_stats.failed,
                "success_rate": self.processing_stats.success_rate,
                "average_processing_time": self.processing_stats.average_time,
                "total_time": self.processing_stats.total_time,
            },
            "cache": {
                "hits": self.processing_stats.cache_hits,
                "misses": self.processing_stats.cache_misses,
                "hit_rate": self.processing_stats.cache_hit_rate,
            },
            "smart_filter": {
                "processed": self.processing_stats.smart_filter_processed,
                "skipped": self.processing_stats.smart_filter_skipped,
                "total_analyzed": (
                    self.processing_stats.smart_filter_processed +
                    self.processing_stats.smart_filter_skipped
                ),
                "skip_rate": (
                    self.processing_stats.smart_filter_skipped /
                    max(1, self.processing_stats.smart_filter_processed + self.processing_stats.smart_filter_skipped)
                ),
            },
            "services": {
                name: {
                    "status": health.status,
                    "operation_count": health.operation_count,
                    "error_count": health.error_count,
                    "error_rate": health.error_count / max(1, health.operation_count),
                    "last_operation": health.last_operation_time.isoformat() if health.last_operation_time else None,
                    "last_error": health.last_error,
                }
                for name, health in self.service_health.items()
            },
            "stage_performance": self.processing_stats.get_stage_averages(),
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for monitoring"""
        
        total_services = len(self.service_health)
        active_services = sum(1 for s in self.service_health.values() if s.status == "active")
        error_services = sum(1 for s in self.service_health.values() if s.status == "error")
        
        return {
            "overall_health": "healthy" if error_services == 0 else "degraded" if error_services < total_services else "unhealthy",
            "total_services": total_services,
            "active_services": active_services,
            "error_services": error_services,
            "processing_success_rate": self.processing_stats.success_rate,
            "cache_hit_rate": self.processing_stats.cache_hit_rate,
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report"""
        
        stage_averages = self.processing_stats.get_stage_averages()
        
        return {
            "overall_performance": {
                "total_requests": self.processing_stats.total_processed,
                "average_response_time": self.processing_stats.average_time,
                "success_rate": self.processing_stats.success_rate,
                "throughput_per_second": (
                    self.processing_stats.total_processed / max(1, self.processing_stats.total_time)
                    if self.processing_stats.total_time > 0 else 0
                ),
            },
            "stage_performance": stage_averages,
            "bottleneck_analysis": self._analyze_bottlenecks(stage_averages),
            "cache_efficiency": {
                "hit_rate": self.processing_stats.cache_hit_rate,
                "total_requests": self.processing_stats.cache_hits + self.processing_stats.cache_misses,
            },
        }
    
    def _analyze_bottlenecks(self, stage_averages: Dict[str, float]) -> Dict[str, Any]:
        """Analyze performance bottlenecks"""
        
        if not stage_averages:
            return {"analysis": "No stage timing data available"}
        
        # Find slowest stage
        slowest_stage = max(stage_averages.items(), key=lambda x: x[1])
        total_stage_time = sum(stage_averages.values())
        
        bottlenecks = []
        
        # Identify stages taking more than 30% of total time
        for stage_name, avg_time in stage_averages.items():
            if total_stage_time > 0:
                percentage = (avg_time / total_stage_time) * 100
                if percentage > 30:
                    bottlenecks.append({
                        "stage": stage_name,
                        "average_time": avg_time,
                        "percentage_of_total": percentage
                    })
        
        return {
            "slowest_stage": {
                "name": slowest_stage[0],
                "average_time": slowest_stage[1]
            },
            "bottleneck_stages": bottlenecks,
            "total_stage_time": total_stage_time
        }
    
    def reset_stats(self) -> None:
        """Reset all statistics"""
        
        self.processing_stats = ProcessingStats()
        
        # Keep service registrations but reset operation counts
        for service_health in self.service_health.values():
            service_health.operation_count = 0
            service_health.error_count = 0
            service_health.last_error = None
            service_health.last_error_time = None
        
        self._processed_since_memlog = 0
        
        self.logger.info("Statistics reset completed")
    
    def _log_memory_snapshot(self) -> None:
        """Log lightweight memory snapshot for diagnostics"""
        
        try:
            rss_mb = None
            try:
                import psutil
                
                process = psutil.Process()
                rss_mb = process.memory_info().rss / (1024 * 1024)
            except ImportError:
                pass
            
            snapshot = {
                "rss_mb": round(rss_mb, 2) if rss_mb is not None else None,
                "total_processed": self.processing_stats.total_processed,
                "success_rate": self.processing_stats.success_rate,
                "cache_hit_rate": self.processing_stats.cache_hit_rate,
            }
            
            self.logger.info(f"Memory snapshot: {snapshot}")
            
        except Exception as e:
            # Never fail the pipeline due to diagnostics
            self.logger.debug(f"Memory snapshot failed: {e}")
    
    def export_stats_to_dict(self) -> Dict[str, Any]:
        """Export all statistics to a dictionary for serialization"""
        
        return {
            "timestamp": datetime.now().isoformat(),
            "processing_stats": {
                "total_processed": self.processing_stats.total_processed,
                "successful": self.processing_stats.successful,
                "failed": self.processing_stats.failed,
                "total_time": self.processing_stats.total_time,
                "average_time": self.processing_stats.average_time,
                "cache_hits": self.processing_stats.cache_hits,
                "cache_misses": self.processing_stats.cache_misses,
                "smart_filter_processed": self.processing_stats.smart_filter_processed,
                "smart_filter_skipped": self.processing_stats.smart_filter_skipped,
                "stage_timings": self.processing_stats.stage_timings,
            },
            "service_health": {
                name: {
                    "service_name": health.service_name,
                    "status": health.status,
                    "initialization_time": health.initialization_time.isoformat() if health.initialization_time else None,
                    "last_operation_time": health.last_operation_time.isoformat() if health.last_operation_time else None,
                    "operation_count": health.operation_count,
                    "error_count": health.error_count,
                    "last_error": health.last_error,
                    "last_error_time": health.last_error_time.isoformat() if health.last_error_time else None,
                }
                for name, health in self.service_health.items()
            },
        }