"""
Tests for metrics collection system.

This module tests metrics collectors, counters, gauges, and histograms.
"""

import pytest
from time import sleep
from unittest.mock import Mock, patch

from cars_bot.monitoring.metrics import (
    MetricsCollector,
    MetricStats,
    get_metrics,
    record_error,
    record_event,
    record_timing,
    track_time,
)


class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    def test_collector_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector(enabled=True)
        
        assert collector.enabled is True
        assert collector._counters == {}
        assert collector._gauges == {}
    
    def test_collector_disabled(self):
        """Test that disabled collector doesn't collect metrics."""
        collector = MetricsCollector(enabled=False)
        
        collector.increment_counter("test")
        collector.set_gauge("test", 42)
        
        # Should not collect anything
        assert collector.get_counter("test") == 0
        assert collector.get_gauge("test") is None


class TestCounters:
    """Test counter metrics."""
    
    def test_increment_counter(self):
        """Test incrementing counter."""
        collector = MetricsCollector()
        
        collector.increment_counter("requests")
        collector.increment_counter("requests")
        collector.increment_counter("requests", value=3)
        
        assert collector.get_counter("requests") == 5
    
    def test_counter_with_labels(self):
        """Test counter with labels."""
        collector = MetricsCollector()
        
        collector.increment_counter("errors", labels={"type": "timeout"})
        collector.increment_counter("errors", labels={"type": "connection"})
        collector.increment_counter("errors", labels={"type": "timeout"})
        
        assert collector.get_counter("errors", labels={"type": "timeout"}) == 2
        assert collector.get_counter("errors", labels={"type": "connection"}) == 1
    
    def test_get_nonexistent_counter(self):
        """Test getting counter that doesn't exist."""
        collector = MetricsCollector()
        
        assert collector.get_counter("nonexistent") == 0


class TestGauges:
    """Test gauge metrics."""
    
    def test_set_gauge(self):
        """Test setting gauge value."""
        collector = MetricsCollector()
        
        collector.set_gauge("temperature", 25.5)
        assert collector.get_gauge("temperature") == 25.5
        
        collector.set_gauge("temperature", 30.0)
        assert collector.get_gauge("temperature") == 30.0
    
    def test_gauge_with_labels(self):
        """Test gauge with labels."""
        collector = MetricsCollector()
        
        collector.set_gauge("cpu", 75.0, labels={"core": "1"})
        collector.set_gauge("cpu", 80.0, labels={"core": "2"})
        
        assert collector.get_gauge("cpu", labels={"core": "1"}) == 75.0
        assert collector.get_gauge("cpu", labels={"core": "2"}) == 80.0
    
    def test_get_nonexistent_gauge(self):
        """Test getting gauge that doesn't exist."""
        collector = MetricsCollector()
        
        assert collector.get_gauge("nonexistent") is None


class TestHistograms:
    """Test histogram metrics."""
    
    def test_record_histogram(self):
        """Test recording histogram values."""
        collector = MetricsCollector()
        
        collector.record_histogram("response_time", 0.1)
        collector.record_histogram("response_time", 0.2)
        collector.record_histogram("response_time", 0.15)
        
        stats = collector.get_histogram_stats("response_time")
        
        assert stats.count == 3
        assert stats.min == 0.1
        assert stats.max == 0.2
        assert 0.1 < stats.mean < 0.2
    
    def test_histogram_with_labels(self):
        """Test histogram with labels."""
        collector = MetricsCollector()
        
        collector.record_histogram("latency", 100, labels={"endpoint": "/api"})
        collector.record_histogram("latency", 150, labels={"endpoint": "/api"})
        collector.record_histogram("latency", 200, labels={"endpoint": "/web"})
        
        api_stats = collector.get_histogram_stats("latency", labels={"endpoint": "/api"})
        web_stats = collector.get_histogram_stats("latency", labels={"endpoint": "/web"})
        
        assert api_stats.count == 2
        assert web_stats.count == 1
    
    def test_histogram_size_limit(self):
        """Test histogram size limiting."""
        collector = MetricsCollector()
        
        # Record many values
        for i in range(15000):
            collector.record_histogram("test", float(i))
        
        # Should be limited to 5000 most recent
        stats = collector.get_histogram_stats("test")
        assert stats.count == 5000


class TestTimings:
    """Test timing metrics."""
    
    def test_record_timing(self):
        """Test recording timing."""
        collector = MetricsCollector()
        
        collector.record_timing("task_duration", 0.5)
        collector.record_timing("task_duration", 0.3)
        collector.record_timing("task_duration", 0.4)
        
        stats = collector.get_timing_stats("task_duration")
        
        assert stats.count == 3
        assert stats.min == 0.3
        assert stats.max == 0.5
    
    def test_track_time_context_manager(self):
        """Test track_time context manager."""
        collector = MetricsCollector()
        
        with collector.track_time("operation"):
            sleep(0.01)  # Small delay
        
        stats = collector.get_timing_stats("operation")
        
        assert stats.count == 1
        assert stats.mean >= 0.01  # At least 10ms
    
    def test_timing_size_limit(self):
        """Test timing data size limiting."""
        collector = MetricsCollector()
        
        # Record many timings
        for i in range(15000):
            collector.record_timing("test", 0.001 * i)
        
        # Should be limited
        stats = collector.get_timing_stats("test")
        assert stats.count == 5000


class TestMetricStats:
    """Test MetricStats class."""
    
    def test_stats_from_empty_values(self):
        """Test stats from empty values list."""
        stats = MetricStats.from_values([])
        
        assert stats.count == 0
        assert stats.total == 0.0
    
    def test_stats_from_single_value(self):
        """Test stats from single value."""
        stats = MetricStats.from_values([42.0])
        
        assert stats.count == 1
        assert stats.total == 42.0
        assert stats.min == 42.0
        assert stats.max == 42.0
        assert stats.mean == 42.0
        assert stats.median == 42.0
    
    def test_stats_from_multiple_values(self):
        """Test stats from multiple values."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = MetricStats.from_values(values)
        
        assert stats.count == 5
        assert stats.total == 15.0
        assert stats.min == 1.0
        assert stats.max == 5.0
        assert stats.mean == 3.0
        assert stats.median == 3.0


class TestMetricsExport:
    """Test metrics data export."""
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()
        
        collector.increment_counter("requests", value=10)
        collector.set_gauge("queue_size", 5)
        collector.record_histogram("latency", 0.1)
        collector.record_timing("process_time", 0.5)
        
        all_metrics = collector.get_all_metrics()
        
        assert "timestamp" in all_metrics
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "timings" in all_metrics
        
        assert all_metrics["counters"]["requests"] == 10
        assert all_metrics["gauges"]["queue_size"] == 5.0
    
    def test_get_summary(self):
        """Test getting metrics summary."""
        collector = MetricsCollector()
        
        collector.increment_counter("test")
        collector.set_gauge("test", 1.0)
        collector.record_histogram("test", 1.0)
        collector.record_timing("test", 1.0)
        
        summary = collector.get_summary()
        
        assert "timestamp" in summary
        assert "total_counters" in summary
        assert "total_gauges" in summary
        assert "total_histograms" in summary
        assert "total_timings" in summary
        
        assert summary["total_counters"] >= 1
        assert summary["total_gauges"] >= 1
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()
        
        collector.increment_counter("test")
        collector.set_gauge("test", 1.0)
        
        collector.reset()
        
        assert collector.get_counter("test") == 0
        assert collector.get_gauge("test") is None


class TestGlobalMetrics:
    """Test global metrics functions."""
    
    def test_get_metrics_singleton(self):
        """Test get_metrics returns singleton."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        
        assert metrics1 is metrics2
    
    def test_record_event(self):
        """Test record_event function."""
        metrics = get_metrics()
        initial_count = metrics.get_counter("test_event")
        
        record_event("test_event")
        
        assert metrics.get_counter("test_event") == initial_count + 1
    
    def test_record_event_with_labels(self):
        """Test record_event with labels."""
        metrics = get_metrics()
        
        record_event("action", labels={"type": "test"})
        
        assert metrics.get_counter("action", labels={"type": "test"}) >= 1
    
    def test_record_error(self):
        """Test record_error function."""
        metrics = get_metrics()
        
        record_error("ValueError", "test_component")
        
        # Should increment errors counter with labels
        count = metrics.get_counter(
            "errors",
            labels={"type": "ValueError", "component": "test_component"}
        )
        assert count >= 1
    
    def test_record_timing_function(self):
        """Test record_timing function."""
        metrics = get_metrics()
        
        record_timing("test_operation", 0.123)
        
        stats = metrics.get_timing_stats("test_operation")
        assert stats.count >= 1
    
    def test_track_time_decorator(self):
        """Test track_time context manager."""
        with track_time("test_track"):
            sleep(0.01)
        
        metrics = get_metrics()
        stats = metrics.get_timing_stats("test_track")
        
        assert stats.count >= 1
        assert stats.mean >= 0.01


# =========================================================================
# INTEGRATION TESTS
# =========================================================================


class TestMetricsIntegration:
    """Integration tests for metrics system."""
    
    def test_full_metrics_workflow(self):
        """Test complete metrics collection workflow."""
        collector = MetricsCollector()
        
        # Simulate application metrics
        for i in range(10):
            collector.increment_counter("requests")
            collector.record_histogram("response_time", 0.1 * i)
            
            if i % 3 == 0:
                collector.increment_counter("errors", labels={"type": "timeout"})
        
        collector.set_gauge("active_connections", 25)
        
        with collector.track_time("batch_process"):
            sleep(0.01)
        
        # Get all metrics
        all_metrics = collector.get_all_metrics()
        
        assert all_metrics["counters"]["requests"] == 10
        assert all_metrics["gauges"]["active_connections"] == 25
        
        # Get stats
        response_stats = collector.get_histogram_stats("response_time")
        assert response_stats.count == 10
        
        timing_stats = collector.get_timing_stats("batch_process")
        assert timing_stats.count == 1
    
    def test_metrics_with_labels(self):
        """Test metrics with different label combinations."""
        collector = MetricsCollector()
        
        # Different endpoints
        endpoints = ["/api/users", "/api/posts", "/api/comments"]
        methods = ["GET", "POST", "PUT"]
        
        for endpoint in endpoints:
            for method in methods:
                collector.increment_counter(
                    "http_requests",
                    labels={"endpoint": endpoint, "method": method}
                )
                collector.record_histogram(
                    "http_duration",
                    0.1,
                    labels={"endpoint": endpoint, "method": method}
                )
        
        # Should have 9 different label combinations
        all_metrics = collector.get_all_metrics()
        
        # Each combination should have count of 1
        for endpoint in endpoints:
            for method in methods:
                count = collector.get_counter(
                    "http_requests",
                    labels={"endpoint": endpoint, "method": method}
                )
                assert count == 1



