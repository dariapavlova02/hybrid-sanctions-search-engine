"""
Unit tests for MetricsService
"""

import asyncio
import pytest
import time
from unittest.mock import Mock

from ai_service.monitoring.metrics_service import (
    MetricsService,
    MetricType,
    AlertSeverity,
    MetricDefinition,
    Alert,
    MetricTimer,
)


class TestMetricsService:
    """Tests for MetricsService"""

    @pytest.fixture
    def metrics_service(self):
        """Create MetricsService instance"""
        return MetricsService(
            max_metric_history=100,
            alert_cooldown_seconds=60,  # 1 minute
            cleanup_interval_hours=1,  # 1 hour for testing
        )

    def test_service_initialization(self, metrics_service):
        """Test service initialization"""
        assert metrics_service.max_metric_history == 100
        assert metrics_service.alert_cooldown_seconds == 60
        assert len(metrics_service.metric_values) == 0
        assert len(metrics_service.metric_definitions) == 0

    def test_counter_metric(self, metrics_service):
        """Test counter metric operations"""
        # Increment counter
        metrics_service.increment_counter("test.counter")
        assert "test.counter" in metrics_service.metrics
        assert metrics_service.metrics["test.counter"]["value"] == 1
        assert metrics_service.metrics["test.counter"]["type"] == MetricType.COUNTER

        # Increment by custom amount
        metrics_service.increment_counter("test.counter", 5)
        assert metrics_service.metrics["test.counter"]["value"] == 6

        # Reset counter
        metrics_service.reset_counter("test.counter")
        assert metrics_service.metrics["test.counter"]["value"] == 0

    def test_gauge_metric(self, metrics_service):
        """Test gauge metric operations"""
        # Set gauge
        metrics_service.gauge("test.gauge", 42.5)
        assert "test.gauge" in metrics_service.metrics
        assert metrics_service.metrics["test.gauge"]["value"] == 42.5
        assert metrics_service.metrics["test.gauge"]["type"] == MetricType.GAUGE

        # Update gauge with delta
        metrics_service.gauge("test.gauge", -2.5)
        assert metrics_service.metrics["test.gauge"]["value"] == 40.0

        # Set absolute value
        metrics_service.set_gauge("test.gauge", 100)
        assert metrics_service.metrics["test.gauge"]["value"] == 100

    def test_histogram_metric(self, metrics_service):
        """Test histogram metric operations"""
        # Record histogram values
        values = [1, 2, 3, 4, 5, 5, 5, 6, 7, 8, 9, 10]
        for value in values:
            metrics_service.histogram("test.histogram", value)

        metric = metrics_service.metrics["test.histogram"]
        assert metric["type"] == MetricType.HISTOGRAM
        assert metric["count"] == len(values)
        assert metric["sum"] == sum(values)
        assert metric["min"] == min(values)
        assert metric["max"] == max(values)

        # Check percentiles
        percentiles = metric["percentiles"]
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

    def test_timer_metric(self, metrics_service):
        """Test timer metric operations"""
        # Record timing
        metrics_service.record_timing("test.timer", 0.123)

        metric = metrics_service.metrics["test.timer"]
        assert metric["type"] == MetricType.TIMER
        assert metric["count"] == 1
        assert metric["sum"] == 0.123

        # Test timer context manager
        with metrics_service.timer("test.context_timer") as timer:
            time.sleep(0.01)  # Small delay
            assert isinstance(timer, MetricTimer)

        metric = metrics_service.metrics["test.context_timer"]
        assert metric["type"] == MetricType.TIMER
        assert metric["count"] == 1
        assert metric["sum"] > 0

    def test_metric_definitions(self, metrics_service):
        """Test metric definition registration"""
        definition = MetricDefinition(
            name="test.metric",
            description="Test metric for unit tests",
            labels=["environment", "service"],
            alert_threshold=100.0,
            alert_severity=AlertSeverity.WARNING,
        )

        metrics_service.register_metric(definition)
        assert "test.metric" in metrics_service.metric_definitions
        assert metrics_service.metric_definitions["test.metric"] == definition

    def test_alert_system(self, metrics_service):
        """Test alert system functionality"""
        # Register metric with alert threshold
        definition = MetricDefinition(
            name="test.alert_metric",
            description="Test metric with alerts",
            alert_threshold=10.0,
            alert_severity=AlertSeverity.CRITICAL,
        )
        metrics_service.register_metric(definition)

        # Trigger alert
        metrics_service.gauge("test.alert_metric", 15.0)

        # Check active alerts
        active_alerts = metrics_service.get_active_alerts()
        assert len(active_alerts) == 1

        alert = active_alerts[0]
        assert alert.metric_name == "test.alert_metric"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.value == 15.0
        assert alert.threshold == 10.0

    def test_alert_cooldown(self, metrics_service):
        """Test alert cooldown mechanism"""
        # Register metric with alert threshold
        definition = MetricDefinition(
            name="test.cooldown_metric",
            description="Test metric with cooldown",
            alert_threshold=5.0,
            alert_severity=AlertSeverity.WARNING,
        )
        metrics_service.register_metric(definition)

        # Trigger first alert
        metrics_service.gauge("test.cooldown_metric", 10.0)
        active_alerts = metrics_service.get_active_alerts()
        assert len(active_alerts) == 1

        # Trigger second alert immediately (should be filtered by cooldown)
        metrics_service.gauge("test.cooldown_metric", 12.0)
        active_alerts = metrics_service.get_active_alerts()
        assert len(active_alerts) == 1  # Still only one alert due to cooldown

    def test_metric_cleanup(self, metrics_service):
        """Test metric cleanup functionality"""
        # Create some old metrics
        metrics_service.gauge("old.metric", 42)

        # Manually set old timestamp
        old_time = time.time() - 3600  # 1 hour ago
        metrics_service.metrics["old.metric"]["last_updated"] = old_time

        # Add fresh metric
        metrics_service.gauge("fresh.metric", 24)

        # Run cleanup
        metrics_service.cleanup_old_metrics(max_age=1800)  # 30 minutes

        # Old metric should be removed, fresh one should remain
        assert "old.metric" not in metrics_service.metrics
        assert "fresh.metric" in metrics_service.metrics

    def test_performance_report(self, metrics_service):
        """Test performance report generation"""
        # Add various metrics
        metrics_service.increment_counter("requests.total", 100)
        metrics_service.increment_counter("requests.failed", 5)
        metrics_service.gauge("cpu.usage", 75.5)
        metrics_service.histogram("response.time", 0.123)
        metrics_service.histogram("response.time", 0.456)

        report = metrics_service.get_performance_report()

        assert "counters" in report
        assert "gauges" in report
        assert "histograms" in report
        assert "timers" in report
        assert "summary" in report

        # Check counter data
        assert "requests.total" in report["counters"]
        assert report["counters"]["requests.total"]["value"] == 100

        # Check gauge data
        assert "cpu.usage" in report["gauges"]
        assert report["gauges"]["cpu.usage"]["value"] == 75.5

        # Check histogram data
        assert "response.time" in report["histograms"]
        assert report["histograms"]["response.time"]["count"] == 2

    def test_system_health_check(self, metrics_service):
        """Test system health check"""
        # Add metrics that indicate good health
        metrics_service.increment_counter("requests.successful", 95)
        metrics_service.increment_counter("requests.failed", 5)
        metrics_service.gauge("cpu.usage", 45.0)
        metrics_service.gauge("memory.usage", 60.0)

        health = metrics_service.check_system_health()

        assert "status" in health
        assert "metrics" in health
        assert "alerts" in health
        assert "uptime" in health

    def test_metric_export(self, metrics_service):
        """Test metric export functionality"""
        # Add various metrics
        metrics_service.increment_counter("export.test.counter", 42)
        metrics_service.gauge("export.test.gauge", 3.14)
        metrics_service.histogram("export.test.histogram", 0.5)

        # Export all metrics
        exported = metrics_service.export_metrics()

        assert len(exported) == 3

        # Check counter export
        counter_metric = next(m for m in exported if m["name"] == "export.test.counter")
        assert counter_metric["type"] == MetricType.COUNTER.value
        assert counter_metric["value"] == 42

        # Check gauge export
        gauge_metric = next(m for m in exported if m["name"] == "export.test.gauge")
        assert gauge_metric["type"] == MetricType.GAUGE.value
        assert gauge_metric["value"] == 3.14

        # Check histogram export
        histogram_metric = next(m for m in exported if m["name"] == "export.test.histogram")
        assert histogram_metric["type"] == MetricType.HISTOGRAM.value
        assert histogram_metric["count"] == 1

    def test_thread_safety(self, metrics_service):
        """Test thread safety of metrics operations"""
        import threading
        import time

        errors = []
        num_threads = 5
        operations_per_thread = 100

        def metric_operations(thread_id):
            try:
                for i in range(operations_per_thread):
                    metrics_service.increment_counter(f"thread.{thread_id}.counter")
                    metrics_service.gauge(f"thread.{thread_id}.gauge", i)
                    metrics_service.histogram(f"thread.{thread_id}.histogram", i * 0.1)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=metric_operations, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Check no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify metrics were recorded correctly
        for i in range(num_threads):
            counter_name = f"thread.{i}.counter"
            gauge_name = f"thread.{i}.gauge"
            histogram_name = f"thread.{i}.histogram"

            assert counter_name in metrics_service.metrics
            assert metrics_service.metrics[counter_name]["value"] == operations_per_thread

            assert gauge_name in metrics_service.metrics
            assert histogram_name in metrics_service.metrics

    @pytest.mark.asyncio
    async def test_async_operations(self, metrics_service):
        """Test async metric operations"""
        async def async_metric_task(task_id):
            for i in range(10):
                metrics_service.increment_counter(f"async.task.{task_id}")
                metrics_service.histogram("async.operation.time", 0.01 * i)
                await asyncio.sleep(0.001)

        # Run multiple async tasks
        tasks = [async_metric_task(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify metrics were recorded
        for i in range(3):
            counter_name = f"async.task.{i}"
            assert counter_name in metrics_service.metrics
            assert metrics_service.metrics[counter_name]["value"] == 10

        assert "async.operation.time" in metrics_service.metrics
        assert metrics_service.metrics["async.operation.time"]["count"] == 30

    def test_memory_usage_tracking(self, metrics_service):
        """Test memory usage tracking"""
        initial_metrics = len(metrics_service.metrics)

        # Add many metrics
        for i in range(200):
            metrics_service.gauge(f"memory.test.{i}", i)

        # Should respect max_metrics limit
        assert len(metrics_service.metrics) <= metrics_service.max_metrics

    def test_metric_labels(self, metrics_service):
        """Test metric labeling functionality"""
        # Register metric with labels
        definition = MetricDefinition(
            name="labeled.metric",
            description="Test metric with labels",
            labels=["service", "environment"],
        )
        metrics_service.register_metric(definition)

        # Record metric with labels
        labels = {"service": "ai-service", "environment": "test"}
        metrics_service.gauge("labeled.metric", 42.0, labels=labels)

        # Verify labels are stored
        metric = metrics_service.metrics["labeled.metric"]
        assert "labels" in metric
        assert metric["labels"] == labels

    def test_bulk_operations(self, metrics_service):
        """Test bulk metric operations"""
        # Bulk update counters
        counter_updates = {
            "bulk.counter.1": 10,
            "bulk.counter.2": 20,
            "bulk.counter.3": 30,
        }

        for name, value in counter_updates.items():
            metrics_service.increment_counter(name, value)

        # Verify all updates
        for name, expected_value in counter_updates.items():
            assert name in metrics_service.metrics
            assert metrics_service.metrics[name]["value"] == expected_value

    def test_error_handling(self, metrics_service):
        """Test error handling in metrics service"""
        # Test with invalid metric names
        metrics_service.increment_counter("")  # Should handle gracefully
        metrics_service.gauge(None, 42)  # Should handle None

        # Test with invalid values
        metrics_service.histogram("test.histogram", "invalid")  # Should handle non-numeric

        # Service should continue working
        metrics_service.increment_counter("valid.counter")
        assert "valid.counter" in metrics_service.metrics