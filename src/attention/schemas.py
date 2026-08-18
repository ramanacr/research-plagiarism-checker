import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ResolvedWork(BaseModel):
    title: str
    journal: Optional[str] = None
    publication_date: Optional[datetime.date] = None
    authors: List[str] = Field(default_factory=list)
    pmid: Optional[str] = None
    doi: Optional[str] = None
    pmcid: Optional[str] = None
    openalex_id: Optional[str] = None

class CanonicalWorkInfo(BaseModel):
    title: str
    journal: Optional[str] = None
    publication_date: Optional[str] = None  # YYYY-MM-DD
    authors: List[str] = Field(default_factory=list)

class WorkIdentifiers(BaseModel):
    pmid: Optional[str] = None
    doi: Optional[str] = None
    pmcid: Optional[str] = None
    openalex_id: Optional[str] = None

class AttentionSummaryItem(BaseModel):
    source: str
    evidence_count: int
    coverage_status: str
    last_refreshed_at: Optional[str] = None  # ISO format

class AttentionEvidenceItem(BaseModel):
    evidence_id: str
    source: str
    source_type: str
    url: str
    title: Optional[str] = None
    published_at: Optional[str] = None
    discovered_at: str
    matched_identifier: str
    match_confidence: str

class AttentionDetails(BaseModel):
    summary: List[AttentionSummaryItem] = Field(default_factory=list)
    evidence: List[AttentionEvidenceItem] = Field(default_factory=list)

class SourceCoverageItem(BaseModel):
    source: str
    state: str
    reason: Optional[str] = None

class CoverageDetails(BaseModel):
    refresh_state: str
    next_refresh_after: Optional[str] = None
    sources: List[SourceCoverageItem] = Field(default_factory=list)

class DonutSlice(BaseModel):
    source: str
    color: str
    unique_authors: int
    subscore: float
    percentage: float

class AltmetricDonutDetails(BaseModel):
    total_score: int
    slices: List[DonutSlice] = Field(default_factory=list)

class AltmetricScoreMetrics(BaseModel):
    mendeley_readers: int = 0
    citation_counts: int = 0
    independent_citations: int = 0
    self_citations: int = 0
    total_unique_contributors: int = 0


class AltmetricScoreDetails(BaseModel):
    score: float
    integer_score: int
    donut: AltmetricDonutDetails
    metrics: AltmetricScoreMetrics

class WorkDetailsResponse(BaseModel):
    work_id: str
    status: str
    canonical_work: CanonicalWorkInfo
    identifiers: WorkIdentifiers
    attention: AttentionDetails
    coverage: CoverageDetails
    altmetric_score: Optional[AltmetricScoreDetails] = None

# Analytics schema
class SourceBreakdownItem(BaseModel):
    source: str
    count: int

class TimelineItem(BaseModel):
    timestamp: str  # bucket date
    counts: Dict[str, int]  # source -> count

class WorkAnalyticsResponse(BaseModel):
    work_id: str
    source_breakdown: List[SourceBreakdownItem] = Field(default_factory=list)
    timeline: List[TimelineItem] = Field(default_factory=list)
    evidence: List[AttentionEvidenceItem] = Field(default_factory=list)
    coverage: CoverageDetails
    updated_at: str
    altmetric_score: Optional[AltmetricScoreDetails] = None

