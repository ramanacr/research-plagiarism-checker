import datetime
import hashlib
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    JSON,
    ForeignKey,
    Boolean,
    Integer,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship
from src.attention.database import Base

class ResearchWork(Base):
    __tablename__ = "research_works"

    id = Column(String(50), primary_key=True)  # e.g., wrk_01J...
    normalized_title = Column(String(1000), nullable=False)
    journal = Column(String(500), nullable=True)
    publication_date = Column(Date, nullable=True)
    authors = Column(JSON, nullable=True)  # list of author names
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    identifiers = relationship("WorkIdentifier", back_populates="work", cascade="all, delete-orphan")
    evidence = relationship("AttentionEvidence", back_populates="work", cascade="all, delete-orphan")
    refreshes = relationship("SourceRefresh", back_populates="work", cascade="all, delete-orphan")
    jobs = relationship("AttentionJob", back_populates="work", cascade="all, delete-orphan")


class WorkIdentifier(Base):
    __tablename__ = "work_identifiers"

    work_id = Column(String(50), ForeignKey("research_works.id", ondelete="CASCADE"), primary_key=True)
    scheme = Column(String(50), primary_key=True)  # e.g., pmid, doi, pmcid, openalex_id
    normalized_value = Column(String(500), primary_key=True)  # unique together with scheme
    display_value = Column(String(500), nullable=False)
    source = Column(String(100), nullable=True)  # identity provider that resolved it
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    work = relationship("ResearchWork", back_populates="identifiers")

    __table_args__ = (
        UniqueConstraint("scheme", "normalized_value", name="uq_identifiers_scheme_value"),
        Index("idx_identifiers_lookup", "scheme", "normalized_value"),
    )


class AttentionEvidence(Base):
    __tablename__ = "attention_evidence"

    id = Column(String(50), primary_key=True)  # e.g., evd_01J...
    work_id = Column(String(50), ForeignKey("research_works.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)  # e.g., wikipedia, news, patent
    source_type = Column(String(50), nullable=False)  # e.g., reference, blog_post
    external_id = Column(String(500), nullable=True)  # external source primary key
    url = Column(String(2048), nullable=False)
    url_hash = Column(String(64), nullable=False)  # SHA-256 hash of URL for unique constraints
    title = Column(String(1000), nullable=True)
    published_at = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    matched_identifier = Column(String(500), nullable=False)  # identifier string that matched
    match_confidence = Column(String(50), nullable=False)  # exact_identifier, canonical_url, probable
    raw_reference_json = Column(JSON, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    work = relationship("ResearchWork", back_populates="evidence")

    __table_args__ = (
        UniqueConstraint("work_id", "source", "external_id", name="uq_evidence_work_source_ext_id"),
        UniqueConstraint("work_id", "source", "url_hash", name="uq_evidence_work_source_url_hash"),
        Index("idx_evidence_source_date", "source", "discovered_at"),
    )

    @staticmethod
    def compute_url_hash(url: str) -> str:
        # Strip query parameters/fragments to prevent duplicate entries for identical URLs
        canonical = url.split("#")[0].split("?")[0].strip().lower()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SourceRefresh(Base):
    __tablename__ = "source_refreshes"

    work_id = Column(String(50), ForeignKey("research_works.id", ondelete="CASCADE"), primary_key=True)
    source = Column(String(50), primary_key=True)  # e.g., wikipedia, news
    state = Column(String(50), default="ready", nullable=False)  # ready, queued, running, failed, etc.
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    next_refresh_at = Column(DateTime, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(String(1000), nullable=True)
    item_count = Column(Integer, default=0, nullable=False)

    work = relationship("ResearchWork", back_populates="refreshes")


class AttentionJob(Base):
    __tablename__ = "attention_jobs"

    id = Column(String(50), primary_key=True)
    work_id = Column(String(50), ForeignKey("research_works.id", ondelete="CASCADE"), nullable=False)
    job_kind = Column(String(50), default="full_refresh", nullable=False)
    state = Column(String(50), default="queued", nullable=False)  # queued, running, completed, failed
    attempt_count = Column(Integer, default=0, nullable=False)
    locked_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    error_details = Column(String(2000), nullable=True)

    work = relationship("ResearchWork", back_populates="jobs")
