"""
Metrics collection and monitoring system.

Provides counters, gauges, histograms for tracking application performance
and Google Sheets integration for reporting.
"""

import asyncio
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, median
from threading import Lock
from time import time
from typing import Any, Dict, List, Optional

from loguru import logger

from cars_bot.config import get_settings


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricStats:
    """Statistical summary of metric values."""
    
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    mean: float = 0.0
    median: float = 0.0
    
    @classmethod
    def from_values(cls, values: List[float]) -> "MetricStats":
        """
        Create stats from list of values.
        
        Args:
            values: List of metric values
        
        Returns:
            MetricStats instance
        """
        if not values:
            return cls()
        
        return cls(
            count=len(values),
            total=sum(values),
            min=min(values),
            max=max(values),
            mean=mean(values),
            median=median(values) if len(values) > 1 else values[0],
        )


class MetricsCollector:
    """
    Metrics collector for tracking application performance.
    
    Provides counters, gauges, histograms, and timing metrics.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            enabled: Enable metrics collection
        """
        self.enabled = enabled
        self._lock = Lock()
        
        # Metric storage
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[MetricValue]] = defaultdict(list)
        self._timings: Dict[str, List[float]] = defaultdict(list)
        
        # Metadata
        self._metric_metadata: Dict[str, Dict[str, Any]] = {}
        self._last_reset = datetime.utcnow()
        
        logger.debug("MetricsCollector initialized")
    
    # =========================================================================
    # COUNTERS
    # =========================================================================
    
    def increment_counter(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        Increment a counter metric.
        
        Counters only go up and are used for counting events.
        
        Args:
            name: Metric name
            value: Value to add (default 1)
            labels: Optional labels for metric
        
        Example:
            >>> collector.increment_counter("posts_processed")
            >>> collector.increment_counter("errors", labels={"type": "ai_error"})
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            self._update_metadata(name, "counter", labels)
    
    def get_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Get current counter value.
        
        Args:
            name: Metric name
            labels: Optional labels
        
        Returns:
            Counter value
        """
        with self._lock:
            key = self._make_key(name, labels)
            return self._counters.get(key, 0)
    
    # =========================================================================
    # GAUGES
    # =========================================================================
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        Set a gauge metric.
        
        Gauges can go up and down and represent current state.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels
        
        Example:
            >>> collector.set_gauge("queue_size", 42)
            >>> collector.set_gauge("cpu_usage", 75.5)
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            self._update_metadata(name, "gauge", labels)
    
    def get_gauge(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """
        Get current gauge value.
        
        Args:
            name: Metric name
            labels: Optional labels
        
        Returns:
            Gauge value or None
        """
        with self._lock:
            key = self._make_key(name, labels)
            return self._gauges.get(key)
    
    # =========================================================================
    # HISTOGRAMS
    # =========================================================================
    
    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        Record a histogram value.
        
        Histograms collect multiple values for statistical analysis.
        
        Args:
            name: Metric name
            value: Value to record
            labels: Optional labels
        
        Example:
            >>> collector.record_histogram("response_time", 0.125)
            >>> collector.record_histogram("batch_size", 50)
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, labels)
            metric_value = MetricValue(value=value, labels=labels or {})
            self._histograms[key].append(metric_value)
            self._update_metadata(name, "histogram", labels)
            
            # Limit histogram size to avoid memory issues
            if len(self._histograms[key]) > 10000:
                # Keep most recent 5000 values
                self._histograms[key] = self._histograms[key][-5000:]
    
    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> MetricStats:
        """
        Get statistical summary of histogram.
        
        Args:
            name: Metric name
            labels: Optional labels
        
        Returns:
            MetricStats with count, min, max, mean, median
        """
        with self._lock:
            key = self._make_key(name, labels)
            values = [v.value for v in self._histograms.get(key, [])]
            return MetricStats.from_values(values)
    
    # =========================================================================
    # TIMINGS
    # =========================================================================
    
    def record_timing(
        self,
        name: str,
        duration: float,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        Record timing metric.
        
        Special case of histogram for timing measurements.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            labels: Optional labels
        
        Example:
            >>> start = time()
            >>> # ... do work ...
            >>> collector.record_timing("task_duration", time() - start)
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, labels)
            self._timings[key].append(duration)
            self._update_metadata(name, "timing", labels)
            
            # Limit timing history
            if len(self._timings[key]) > 10000:
                self._timings[key] = self._timings[key][-5000:]
    
    def get_timing_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> MetricStats:
        """
        Get timing statistics.
        
        Args:
            name: Metric name
            labels: Optional labels
        
        Returns:
            MetricStats for timing data
        """
        with self._lock:
            key = self._make_key(name, labels)
            values = self._timings.get(key, [])
            return MetricStats.from_values(values)
    
    @contextmanager
    def track_time(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        Context manager to track execution time.
        
        Args:
            name: Metric name
            labels: Optional labels
        
        Example:
            >>> with collector.track_time("process_message"):
            ...     # Process message
            ...     pass
        """
        start = time()
        try:
            yield
        finally:
            duration = time() - start
            self.record_timing(name, duration, labels)
    
    # =========================================================================
    # DATA EXPORT
    # =========================================================================
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics as a dictionary.
        
        Returns:
            Dictionary with all metrics and their values
        """
        with self._lock:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self._last_reset).total_seconds(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: self.get_histogram_stats(k).count
                    for k in self._histograms.keys()
                },
                "timings": {
                    k: {
                        "count": len(v),
                        "mean": mean(v) if v else 0,
                        "p50": median(v) if v else 0,
                        "p95": self._percentile(v, 0.95) if v else 0,
                        "p99": self._percentile(v, 0.99) if v else 0,
                    }
                    for k, v in self._timings.items()
                },
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of key metrics.
        
        Returns:
            Dictionary with summary metrics
        """
        all_metrics = self.get_all_metrics()
        
        return {
            "timestamp": all_metrics["timestamp"],
            "uptime_seconds": all_metrics["uptime_seconds"],
            "total_counters": len(all_metrics["counters"]),
            "total_gauges": len(all_metrics["gauges"]),
            "total_histograms": len(all_metrics["histograms"]),
            "total_timings": len(all_metrics["timings"]),
        }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timings.clear()
            self._metric_metadata.clear()
            self._last_reset = datetime.utcnow()
            logger.info("Metrics reset")
    
    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create metric key from name and labels."""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _update_metadata(
        self,
        name: str,
        metric_type: str,
        labels: Optional[Dict[str, str]],
    ):
        """Update metric metadata."""
        if name not in self._metric_metadata:
            self._metric_metadata[name] = {
                "type": metric_type,
                "labels": set(),
            }
        
        if labels:
            self._metric_metadata[name]["labels"].update(labels.keys())
    
    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================


_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """
    Get global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    
    Example:
        >>> from cars_bot.monitoring import get_metrics
        >>> metrics = get_metrics()
        >>> metrics.increment_counter("requests")
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        try:
            settings = get_settings()
            enabled = settings.metrics.enabled
        except Exception:
            enabled = True
        
        _metrics_collector = MetricsCollector(enabled=enabled)
    
    return _metrics_collector


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def record_event(name: str, labels: Optional[Dict[str, str]] = None):
    """
    Record an event (increment counter).
    
    Args:
        name: Event name
        labels: Optional labels
    
    Example:
        >>> record_event("post_processed")
        >>> record_event("error", labels={"type": "timeout"})
    """
    get_metrics().increment_counter(name, labels=labels)


def record_error(error_type: str, component: str = "unknown"):
    """
    Record an error event.
    
    Args:
        error_type: Type of error
        component: Component where error occurred
    
    Example:
        >>> record_error("ValueError", "ai_processor")
    """
    get_metrics().increment_counter(
        "errors",
        labels={"type": error_type, "component": component},
    )


def record_timing(name: str, duration: float, labels: Optional[Dict[str, str]] = None):
    """
    Record timing metric.
    
    Args:
        name: Metric name
        duration: Duration in seconds
        labels: Optional labels
    
    Example:
        >>> start = time()
        >>> # ... work ...
        >>> record_timing("task_duration", time() - start)
    """
    get_metrics().record_timing(name, duration, labels)


@contextmanager
def track_time(name: str, labels: Optional[Dict[str, str]] = None):
    """
    Context manager to track execution time.
    
    Args:
        name: Metric name
        labels: Optional labels
    
    Example:
        >>> with track_time("process_message"):
        ...     # Process message
        ...     pass
    """
    with get_metrics().track_time(name, labels):
        yield


__all__ = [
    "MetricsCollector",
    "MetricValue",
    "MetricStats",
    "get_metrics",
    "record_event",
    "record_error",
    "record_timing",
    "track_time",
]



