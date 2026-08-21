"""
Observability package for logging, metrics, and tracing.
"""

from src.plagiarism.observability.logging import (
    PlagiarismLogger,
    get_correlation_id,
    set_correlation_id,
)
from src.plagiarism.observability.metrics import MetricsCollector, global_metrics
from src.plagiarism.observability.tracing import PipelineTracer

__all__ = [
    "PlagiarismLogger",
    "get_correlation_id",
    "set_correlation_id",
    "MetricsCollector",
    "global_metrics",
    "PipelineTracer",
]
