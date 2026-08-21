"""
Lightweight span tracer for pipeline execution stages.
"""

import time
from contextlib import contextmanager
from typing import Iterator, Dict, Any, List


class PipelineTracer:
    """
    Traces execution stages of the plagiarism pipeline.
    """

    def __init__(self):
        self.spans: List[Dict[str, Any]] = []

    @contextmanager
    def trace_stage(self, stage_name: str) -> Iterator[None]:
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            self.spans.append({
                "stage": stage_name,
                "duration_ms": round(elapsed * 1000, 2),
            })

    def get_timeline(self) -> List[Dict[str, Any]]:
        return list(self.spans)
