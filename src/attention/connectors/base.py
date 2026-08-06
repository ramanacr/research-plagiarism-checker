import datetime
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.attention.models import ResearchWork

class ConnectorEvidence(BaseModel):
    external_id: Optional[str] = None
    url: str
    title: Optional[str] = None
    published_at: Optional[datetime.date] = None  # Will use datetime.datetime or datetime.date
    matched_identifier: str
    match_confidence: str  # exact_identifier, canonical_url, probable
    raw_reference_json: Optional[Dict[str, Any]] = None

class ConnectorResult(BaseModel):
    source: str
    state: str  # ready, failed, rate_limited
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    item_count: int = 0

class AttentionConnector(ABC):
    @abstractmethod
    def collect(self, work: ResearchWork) -> ConnectorResult:
        pass
