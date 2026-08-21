"""
Metrics collection and runtime telemetry for plagiarism checks.
"""

import time
from typing import Dict, List, Any
import numpy as np


class MetricsCollector:
    """
    In-memory metrics collector for recording latency, match counts, and throughput.
    """

    def __init__(self):
        self.latencies: List[float] = []
        self.match_counts: Dict[str, int] = {}
        self.total_checks: int = 0
        self.total_passages_indexed: int = 0

    def record_check(self, latency_seconds: float, match_class_counts: Dict[str, int]) -> None:
        self.total_checks += 1
        self.latencies.append(latency_seconds)
        for cls, count in match_class_counts.items():
            self.match_counts[cls] = self.match_counts.get(cls, 0) + count

    def get_summary(self) -> Dict[str, Any]:
        if not self.latencies:
            return {
                "total_checks": self.total_checks,
                "latency_p50_s": 0.0,
                "latency_p95_s": 0.0,
                "match_counts": self.match_counts,
            }
        return {
            "total_checks": self.total_checks,
            "latency_p50_s": round(float(np.percentile(self.latencies, 50)), 3),
            "latency_p95_s": round(float(np.percentile(self.latencies, 95)), 3),
            "total_matches_flagged": sum(self.match_counts.values()),
            "match_counts": self.match_counts,
        }


global_metrics = MetricsCollector()
