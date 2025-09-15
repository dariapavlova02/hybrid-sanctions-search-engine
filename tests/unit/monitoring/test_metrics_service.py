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
    
    def _register_test_metric(self, metrics_service, name, metric_type, description="Test metric"):
        """Helper to register a test metric"""
        metric_def = MetricDefinition(name, metric_type, description)
        metrics_service.register_metric(metric_def)

    def test_service_initialization(self, metrics_service):
        """Test service initialization"""
        assert metrics_service.max_metric_history == 100
        assert metrics_service.alert_cooldown_seconds == 60
        assert len(metrics_service.metric_values) == 0
        assert len(metrics_service.metric_definitions) > 0  # Has predefined metrics

    def test_counter_metric(self, metrics_service):
        """Test counter metric operations"""
        # Register metric first
        from src.ai_service.monitoring.metrics_service import MetricDefinition, MetricType
        metric_def = MetricDefinition("test.counter", MetricType.COUNTER, "Test counter metric")
        metrics_service.register_metric(metric_def)
        
        # Increment counter
        metrics_service.increment_counter("test.counter")
        assert "test.counter" in metrics_service.metrics
        assert metrics_service.metrics["test.counter"]["value"] == 1
        assert metrics_service.metrics["test.counter"]["type"] == "counter"

        # Increment by custom amount
        metrics_service.increment_counter("test.counter", 5)
        assert metrics_service.metrics["test.counter"]["value"] == 5

    def test_set_gauge_metric(self, metrics_service):
        """Test set_gauge metric operations"""
        # Register metric first
        from src.ai_service.monitoring.metrics_service import MetricDefinition, MetricType
        metric_def = MetricDefinition("test.set_gauge", MetricType.GAUGE, "Test gauge metric")
        metrics_service.register_metric(metric_def)
        
        # Set set_gauge
        metrics_service.set_gauge("test.set_gauge", 42.5)
        assert "test.set_gauge" in metrics_service.metrics
        assert metrics_service.metrics["test.set_gauge"]["value"] == 42.5
        assert metrics_service.metrics["test.set_gauge"]["type"] == "gauge"

        # Update set_gauge with delta (not supported, use set_gauge)
        metrics_service.set_gauge("test.set_gauge", 40.0)
        assert metrics_service.metrics["test.set_gauge"]["value"] == 40.0

        # Set absolute value
        metrics_service.set_gauge("test.set_gauge", 100)
        assert metrics_service.metrics["test.set_gauge"]["value"] == 100

    def test_record_histogram_metric(self, metrics_service):
        """Test record_histogram metric operations"""
        # Register metric first
        from src.ai_service.monitoring.metrics_service import MetricDefinition, MetricType
        metric_def = MetricDefinition("test.record_histogram", MetricType.HISTOGRAM, "Test histogram metric")
        metrics_service.register_metric(metric_def)
        
        # Record record_histogram values
        values = [1, 2, 3, 4, 5, 5, 5, 6, 7, 8, 9, 10]
        for value in values:
            metrics_service.record_histogram("test.record_histogram", value)

        metric = metrics_service.metrics["test.record_histogram"]
        assert metric["type"] == "histogram"
        assert metric["value"] == 10  # Last recorded value

    def test_timer_metric(self, metrics_service):
        """Test timer metric operations"""
        # Register metric first
        from src.ai_service.monitoring.metrics_service import MetricDefinition, MetricType
        metric_def = MetricDefinition("test.timer", MetricType.HISTOGRAM, "Test timer metric")
        metrics_service.register_metric(metric_def)
        
        # Record timing
        metrics_service.record_timer("test.timer", 0.123)

        metric = metrics_service.metrics["test.timer"]
        assert metric["type"] == "histogram"
        assert metric["value"] == 0.123

        # Test timer context manager
        metric_def2 = MetricDefinition("test.context_timer", MetricType.HISTOGRAM, "Test context timer metric")
        metrics_service.register_metric(metric_def2)
        
        with metrics_service.timer("test.context_timer") as timer:
            time.sleep(0.01)  # Small delay
            assert isinstance(timer, MetricTimer)

        metric = metrics_service.metrics["test.context_timer"]
        assert metric["type"] == "histogram"
        assert metric["value"] > 0

    def test_metric_definitions(self, metrics_service):
        """Test metric definition registration"""
        definition = MetricDefinition(
            name="test.metric",
            metric_type=MetricType.COUNTER,
            description="Test metric for unit tests",
            labels={"environment", "service"},
        )

        metrics_service.register_metric(definition)
        assert "test.metric" in metrics_service.metric_definitions
        assert metrics_service.metric_definitions["test.metric"] == definition

    def test_alert_system(self, metrics_service):
        """Test alert system functionality"""
        from src.ai_service.monitoring.metrics_service import AlertSeverity
        
        # Register metric with alert threshold
        definition = MetricDefinition(
            name="test.alert_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric with alerts",
        )
        metrics_service.register_metric(definition)
        
        # Add alert rule
        metrics_service.add_alert_rule(
            metric_name="test.alert_metric",
            threshold=10.0,
            condition="gt",
            severity=AlertSeverity.CRITICAL,
            message_template="Alert: value {value} is greater than threshold {threshold}"
        )

        # Trigger alert
        metrics_service.set_gauge("test.alert_metric", 15.0)

        # Check active alerts
        active_alerts = metrics_service.get_active_alerts()
        assert len(active_alerts) == 1

        alert = active_alerts[0]
        assert alert.metric_name == "test.alert_metric"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.metric_value == 15.0
        assert alert.threshold == 10.0

    def test_alert_cooldown(self, metrics_service):
        """Test alert cooldown mechanism"""
        # Register metric with alert threshold
        definition = MetricDefinition(
            name="test.cooldown_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric with cooldown",
        )
        metrics_service.register_metric(definition)

        # Add alert rule
        metrics_service.add_alert_rule(
            metric_name="test.cooldown_metric",
            threshold=5.0,
            condition="gt",
            severity="warning",
            message_template="Value {value} exceeds threshold {threshold}"
        )

        # Trigger first alert
        metrics_service.set_gauge("test.cooldown_metric", 10.0)
        active_alerts = metrics_service.get_active_alerts()
        assert len(active_alerts) == 1

        # Trigger second alert immediately (should be filtered by cooldown)
        metrics_service.set_gauge("test.cooldown_metric", 12.0)
        active_alerts = metrics_service.get_active_alerts()
        assert len(active_alerts) == 1  # Still only one alert due to cooldown

    def test_metric_cleanup(self, metrics_service):
        """Test metric cleanup functionality"""
        # Register metrics first
        old_definition = MetricDefinition(
            name="old.metric",
            metric_type=MetricType.GAUGE,
            description="Old test metric",
        )
        fresh_definition = MetricDefinition(
            name="fresh.metric",
            metric_type=MetricType.GAUGE,
            description="Fresh test metric",
        )
        metrics_service.register_metric(old_definition)
        metrics_service.register_metric(fresh_definition)

        # Create some old metrics
        metrics_service.set_gauge("old.metric", 42)

        # Manually set old timestamp in metric_values
        old_time = time.time() - 3600  # 1 hour ago
        if "old.metric" in metrics_service.metric_values:
            for value in metrics_service.metric_values["old.metric"]:
                value.timestamp = old_time

        # Add fresh metric
        metrics_service.set_gauge("fresh.metric", 24)

        # Run cleanup
        metrics_service.cleanup_old_metrics(max_age_hours=1)  # 1 hour

        # Old metric should be removed, fresh one should remain
        assert "old.metric" not in metrics_service.metrics
        assert "fresh.metric" in metrics_service.metrics

    def test_performance_report(self, metrics_service):
        """Test performance report generation"""
        # Register metrics that the performance report expects
        request_definition = MetricDefinition(
            name="request_count",
            metric_type=MetricType.COUNTER,
            description="Request count",
        )
        error_definition = MetricDefinition(
            name="error_count",
            metric_type=MetricType.COUNTER,
            description="Error count",
        )
        duration_definition = MetricDefinition(
            name="request_duration",
            metric_type=MetricType.HISTOGRAM,
            description="Request duration",
        )
        embeddings_definition = MetricDefinition(
            name="embeddings_generated",
            metric_type=MetricType.COUNTER,
            description="Embeddings generated",
        )
        similarity_definition = MetricDefinition(
            name="similarity_searches",
            metric_type=MetricType.COUNTER,
            description="Similarity searches",
        )
        patterns_definition = MetricDefinition(
            name="pattern_matches",
            metric_type=MetricType.COUNTER,
            description="Pattern matches",
        )
        metrics_service.register_metric(request_definition)
        metrics_service.register_metric(error_definition)
        metrics_service.register_metric(duration_definition)
        metrics_service.register_metric(embeddings_definition)
        metrics_service.register_metric(similarity_definition)
        metrics_service.register_metric(patterns_definition)

        # Add various metrics
        metrics_service.increment_counter("request_count", 100)
        metrics_service.increment_counter("error_count", 5)
        metrics_service.record_histogram("request_duration", 0.123)
        metrics_service.record_histogram("request_duration", 0.456)
        metrics_service.increment_counter("embeddings_generated", 50)
        metrics_service.increment_counter("similarity_searches", 25)
        metrics_service.increment_counter("pattern_matches", 10)

        # Test basic report structure
        report = metrics_service.get_performance_report()

        assert "report_timestamp" in report
        assert "time_window_hours" in report
        assert "performance_summary" in report
        assert "service_metrics" in report
        assert "alerts_summary" in report
        assert "system_health" in report

        # Check performance summary
        assert "requests_processed" in report["performance_summary"]
        assert "avg_request_duration" in report["performance_summary"]
        assert "error_rate" in report["performance_summary"]
        assert "throughput_per_second" in report["performance_summary"]

        # Check service metrics
        assert "embeddings_generated" in report["service_metrics"]
        assert "similarity_searches" in report["service_metrics"]
        assert "pattern_matches" in report["service_metrics"]

        # Check alerts summary
        assert "active_critical" in report["alerts_summary"]
        assert "active_total" in report["alerts_summary"]

    def test_system_health_check(self, metrics_service):
        """Test system health check"""
        # Register metrics first to avoid warnings
        metrics_service.register_metric(MetricDefinition("requests.successful", MetricType.COUNTER, "Successful requests", set()))
        metrics_service.register_metric(MetricDefinition("requests.failed", MetricType.COUNTER, "Failed requests", set()))
        metrics_service.register_metric(MetricDefinition("cpu.usage", MetricType.GAUGE, "CPU usage", set()))
        metrics_service.register_metric(MetricDefinition("memory.usage", MetricType.GAUGE, "Memory usage", set()))
        
        # Add metrics that indicate good health
        metrics_service.increment_counter("requests.successful", 95)
        metrics_service.increment_counter("requests.failed", 5)
        metrics_service.set_gauge("cpu.usage", 45.0)
        metrics_service.set_gauge("memory.usage", 60.0)

        health = metrics_service.get_system_health()

        assert "status" in health
        assert "metrics_collected" in health
        assert "active_alerts" in health
        assert "uptime_seconds" in health

    def test_metric_export(self, metrics_service):
        """Test metric export functionality"""
        # Register metrics first to avoid warnings
        metrics_service.register_metric(MetricDefinition("export.test.counter", MetricType.COUNTER, "Test counter", set()))
        metrics_service.register_metric(MetricDefinition("export.test.set_gauge", MetricType.GAUGE, "Test gauge", set()))
        metrics_service.register_metric(MetricDefinition("export.test.record_histogram", MetricType.HISTOGRAM, "Test histogram", set()))
        
        # Add various metrics
        metrics_service.increment_counter("export.test.counter", 42)
        metrics_service.set_gauge("export.test.set_gauge", 3.14)
        metrics_service.record_histogram("export.test.record_histogram", 0.5)

        # Export all metrics as dictionary
        exported = metrics_service.export_metrics(format="dict")

        # Check that we have the expected structure
        assert "timestamp" in exported
        assert "service_uptime" in exported
        assert "metrics" in exported
        assert "alerts" in exported
        assert "system_health" in exported

        # Check that our test metrics are in the export
        metrics = exported["metrics"]
        assert "export.test.counter" in metrics
        assert "export.test.set_gauge" in metrics
        assert "export.test.record_histogram" in metrics

    def test_thread_safety(self, metrics_service):
        """Test thread safety of metrics operations"""
        import threading
        import time

        errors = []
        num_threads = 5
        operations_per_thread = 100

        # Register metrics first to avoid warnings
        for i in range(num_threads):
            metrics_service.register_metric(MetricDefinition(f"thread.{i}.counter", MetricType.COUNTER, f"Thread {i} counter", set()))
            metrics_service.register_metric(MetricDefinition(f"thread.{i}.set_gauge", MetricType.GAUGE, f"Thread {i} gauge", set()))
            metrics_service.register_metric(MetricDefinition(f"thread.{i}.record_histogram", MetricType.HISTOGRAM, f"Thread {i} histogram", set()))

        def metric_operations(thread_id):
            try:
                for i in range(operations_per_thread):
                    metrics_service.increment_counter(f"thread.{thread_id}.counter", 1)
                    metrics_service.set_gauge(f"thread.{thread_id}.set_gauge", i)
                    metrics_service.record_histogram(f"thread.{thread_id}.record_histogram", i * 0.1)
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
            set_gauge_name = f"thread.{i}.set_gauge"
            record_histogram_name = f"thread.{i}.record_histogram"

            # Check that metrics exist
            assert counter_name in metrics_service.metrics
            assert set_gauge_name in metrics_service.metrics
            assert record_histogram_name in metrics_service.metrics

            # For counters, check the sum of all values
            counter_summary = metrics_service.get_metric_summary(counter_name, 300)
            assert counter_summary["sum"] == operations_per_thread

    @pytest.mark.asyncio
    async def test_async_operations(self, metrics_service):
        """Test async metric operations"""
        # Register metrics first to avoid warnings
        for i in range(3):
            metrics_service.register_metric(MetricDefinition(f"async.task.{i}", MetricType.COUNTER, f"Async task {i}", set()))
        metrics_service.register_metric(MetricDefinition("async.operation.time", MetricType.HISTOGRAM, "Async operation time", set()))
        
        async def async_metric_task(task_id):
            for i in range(10):
                metrics_service.increment_counter(f"async.task.{task_id}", 1)
                metrics_service.record_histogram("async.operation.time", 0.01 * i)
                await asyncio.sleep(0.001)

        # Run multiple async tasks
        tasks = [async_metric_task(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify metrics were recorded
        for i in range(3):
            counter_name = f"async.task.{i}"
            assert counter_name in metrics_service.metrics
            # Check the sum of all values for counters
            counter_summary = metrics_service.get_metric_summary(counter_name, 300)
            assert counter_summary["sum"] == 10

        assert "async.operation.time" in metrics_service.metrics
        histogram_summary = metrics_service.get_metric_summary("async.operation.time", 300)
        assert histogram_summary["count"] == 30

    def test_memory_usage_tracking(self, metrics_service):
        """Test memory usage tracking"""
        initial_metrics = len(metrics_service.metrics)

        # Add many metrics
        for i in range(200):
            metrics_service.set_gauge(f"memory.test.{i}", i)

        # Should respect max_metric_history limit
        assert len(metrics_service.metrics) <= metrics_service.max_metric_history

    def test_metric_labels(self, metrics_service):
        """Test metric labeling functionality"""
        # Register metric with labels
        definition = MetricDefinition(
            name="labeled.metric",
            metric_type=MetricType.COUNTER,
            description="Test metric with labels",
            labels={"service", "environment"},
        )
        metrics_service.register_metric(definition)

        # Record metric with labels
        labels = {"service": "ai-service", "environment": "test"}
        metrics_service.set_gauge("labeled.metric", 42.0, labels=labels)

        # Verify labels are stored
        metric = metrics_service.metrics["labeled.metric"]
        assert "labels" in metric
        assert metric["labels"] == labels

    def test_bulk_operations(self, metrics_service):
        """Test bulk metric operations"""
        # Register metrics first to avoid warnings
        counter_updates = {
            "bulk.counter.1": 10,
            "bulk.counter.2": 20,
            "bulk.counter.3": 30,
        }

        for name in counter_updates.keys():
            metrics_service.register_metric(MetricDefinition(name, MetricType.COUNTER, f"Bulk counter {name}", set()))

        for name, value in counter_updates.items():
            metrics_service.increment_counter(name, value)

        # Verify all updates
        for name, expected_value in counter_updates.items():
            assert name in metrics_service.metrics
            # Check the sum of all values for counters
            counter_summary = metrics_service.get_metric_summary(name, 300)
            assert counter_summary["sum"] == expected_value

    def test_error_handling(self, metrics_service):
        """Test error handling in metrics service"""
        # Register valid metric first
        metrics_service.register_metric(MetricDefinition("valid.counter", MetricType.COUNTER, "Valid counter", set()))
        
        # Test with invalid metric names
        metrics_service.increment_counter("")  # Should handle gracefully
        metrics_service.set_gauge(None, 42)  # Should handle None

        # Test with invalid values
        metrics_service.record_histogram("test.record_histogram", "invalid")  # Should handle non-numeric

        # Service should continue working
        metrics_service.increment_counter("valid.counter")
        assert "valid.counter" in metrics_service.metrics