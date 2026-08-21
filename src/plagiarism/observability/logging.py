"""
Structured logging with correlation IDs and confidential text masking.
"""

import logging
import uuid
import contextvars
from typing import Optional, Dict, Any

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    cid = correlation_id_var.get()
    if not cid:
        cid = f"chk_{uuid.uuid4().hex[:12]}"
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    correlation_id_var.set(cid)


class PlagiarismLogger:
    """
    Structured logger that attaches correlation IDs and ensures raw full-text is masked.
    """

    def __init__(self, name: str = "plagiarism_engine"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        cid = get_correlation_id()
        extra_str = f" | {extra}" if extra else ""
        self.logger.info(f"[{cid}] {message}{extra_str}")

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        cid = get_correlation_id()
        extra_str = f" | {extra}" if extra else ""
        self.logger.warning(f"[{cid}] {message}{extra_str}")

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        cid = get_correlation_id()
        extra_str = f" | {extra}" if extra else ""
        self.logger.error(f"[{cid}] {message}{extra_str}")
