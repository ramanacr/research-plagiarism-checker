"""
Domain models for content rights, licenses, and persistence policies.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass(frozen=True)
class RightsRecord:
    rights_id: str
    provider: str
    license_uri: Optional[str] = None
    license_name: str = "Unknown"
    commercial_use_allowed: bool = False
    text_mining_allowed: bool = True
    raw_storage_allowed: bool = False
    derived_index_allowed: bool = True
    snippet_display_allowed: bool = True
    retention_days: int = 365
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None


@dataclass(frozen=True)
class RightsDecision:
    allowed_to_index: bool
    allowed_to_store_raw: bool
    allowed_to_display_snippet: bool
    reason: str
    rights_record: Optional[RightsRecord] = None
