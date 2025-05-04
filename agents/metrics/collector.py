# agents/metrics/collector.py
import logging
import time
from typing import Dict, Any, Optional
from collections import defaultdict

# Using standard library defaultdict for simple in-memory collection for now.
# Could be replaced with Prometheus client or other library later.

logger = logging.getLogger("agent.metrics.collector")


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._timers: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total_time": 0.0, "count": 0, "start_time": None}
        )
        logger.info("MetricsCollector initialized.")

    def increment_counter(
        self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None
    ):
        # Tags are ignored in this simple version
        key = name
        self._counters[key] += value
        logger.debug(f"Counter incremented: {key} by {value}")

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        # Tags are ignored
        key = name
        self._gauges[key] = value
        logger.debug(f"Gauge set: {key} = {value}")

    def start_timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        key = name
        if self._timers[key]["start_time"] is not None:
            logger.warning(f"Timer '{key}' started again before stopping.")
        self._timers[key]["start_time"] = time.monotonic()
        logger.debug(f"Timer started: {key}")

    def stop_timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        key = name
        timer = self._timers[key]
        if timer["start_time"] is None:
            logger.warning(f"Timer '{key}' stopped without being started.")
            return

        elapsed = time.monotonic() - timer["start_time"]
        timer["total_time"] += elapsed
        timer["count"] += 1
        timer["start_time"] = None
        logger.debug(f"Timer stopped: {key}, elapsed: {elapsed:.4f}s")

    def get_metrics(self) -> Dict[str, Any]:
        """Return collected metrics."""
        timers_summary = {}
        for name, data in self._timers.items():
            timers_summary[name] = {
                "total_time_seconds": data["total_time"],
                "count": data["count"],
                "average_seconds": (
                    data["total_time"] / data["count"] if data["count"] > 0 else 0
                ),
            }

        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timers": timers_summary,
        }


# Global instance (or use dependency injection)
metrics_collector = MetricsCollector()

# Example usage:
# from agents.metrics.collector import metrics_collector
# metrics_collector.increment_counter("messages_sent")
# metrics_collector.start_timer("llm_request_duration")
# # ... perform LLM request ...
# metrics_collector.stop_timer("llm_request_duration")
