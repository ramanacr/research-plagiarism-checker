import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional

from src.attention.database import get_db
from src.attention.schemas import WorkDetailsResponse, WorkAnalyticsResponse

router = APIRouter(prefix="/api/v1/research-attention", tags=["research-attention"])

def verify_internal_key(x_research_attention_key: str = Header(None)):
    from src.config import RESEARCH_ATTENTION_INTERNAL_API_KEY
    if not x_research_attention_key or x_research_attention_key != RESEARCH_ATTENTION_INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal API key.")

def _queue_refresh_job(db: Session, work_id: str):
    from src.attention.models import AttentionJob, SourceRefresh
    from src.attention.connectors.registry import ConnectorRegistry

    # Check if a queued or running job already exists for this work
    existing_job = db.query(AttentionJob).filter(
        AttentionJob.work_id == work_id,
        AttentionJob.state.in_(["queued", "running"])
    ).first()
    
    if not existing_job:
        job = AttentionJob(
            id=f"job_{uuid.uuid4().hex[:16]}",
            work_id=work_id,
            job_kind="full_refresh",
            state="queued",
            scheduled_at=datetime.datetime.utcnow()
        )
        db.add(job)
        
        # Also set SourceRefresh records to "queued" state
        registry = ConnectorRegistry()
        for source in registry.get_all_sources():
            if registry.is_enabled(source):
                refresh = db.query(SourceRefresh).filter_by(work_id=work_id, source=source).first()
                if not refresh:
                    refresh = SourceRefresh(
                        work_id=work_id,
                        source=source,
                        state="queued"
                    )
                    db.add(refresh)
                else:
                    refresh.state = "queued"
        db.commit()

@router.get("/works/pmid/{pmid}", response_model=WorkDetailsResponse)
def get_work_by_pmid(pmid: str, db: Session = Depends(get_db)):
    from src.attention.resolver import WorkResolver
    from src.attention.models import SourceRefresh
    from src.attention.services import get_work_details
    
    resolver = WorkResolver()
    work = resolver.resolve_work(db, pmid=pmid)
    refreshes_exist = db.query(SourceRefresh).filter_by(work_id=work.id).first()
    if not refreshes_exist:
        _queue_refresh_job(db, work.id)
    return get_work_details(db, work.id)

@router.get("/works/doi/{doi:path}", response_model=WorkDetailsResponse)
def get_work_by_doi(doi: str, db: Session = Depends(get_db)):
    from src.attention.resolver import WorkResolver
    from src.attention.models import SourceRefresh
    from src.attention.services import get_work_details

    resolver = WorkResolver()
    work = resolver.resolve_work(db, doi=doi)
    refreshes_exist = db.query(SourceRefresh).filter_by(work_id=work.id).first()
    if not refreshes_exist:
        _queue_refresh_job(db, work.id)
    return get_work_details(db, work.id)

@router.get("/works/{work_id}", response_model=WorkDetailsResponse)
def get_work_by_id(work_id: str, db: Session = Depends(get_db)):
    from src.attention.models import ResearchWork
    from src.attention.services import get_work_details

    work = db.query(ResearchWork).filter_by(id=work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Canonical work record not found.")
    return get_work_details(db, work_id)

@router.post("/works/{work_id}/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh_work_attention(work_id: str, db: Session = Depends(get_db), key: None = Depends(verify_internal_key)):
    from src.attention.models import ResearchWork

    work = db.query(ResearchWork).filter_by(id=work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Canonical work record not found.")
    
    _queue_refresh_job(db, work_id)
    return {"status": "queued", "work_id": work_id}

@router.get("/works/{work_id}/analytics", response_model=WorkAnalyticsResponse)
def get_work_analytics(work_id: str, db: Session = Depends(get_db)):
    from src.attention.models import ResearchWork, AttentionEvidence
    from src.attention.services import get_work_details
    
    work = db.query(ResearchWork).filter_by(id=work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Canonical work record not found.")
        
    # Fetch all active evidence
    active_ev = db.query(AttentionEvidence).filter_by(work_id=work_id, active=True).all()
    
    # 1. Calculate source breakdown
    counts_dict = {}
    for ev in active_ev:
        counts_dict[ev.source] = counts_dict.get(ev.source, 0) + 1
    source_breakdown = [{"source": k, "count": v} for k, v in counts_dict.items()]
    
    # 2. Calculate monthly timeline buckets
    timeline_buckets = {}
    for ev in active_ev:
        date_val = ev.published_at or ev.discovered_at.date()
        bucket = date_val.strftime("%Y-%m")
        if bucket not in timeline_buckets:
            timeline_buckets[bucket] = {}
        timeline_buckets[bucket][ev.source] = timeline_buckets[bucket].get(ev.source, 0) + 1
        
    timeline = []
    for bucket in sorted(timeline_buckets.keys()):
        timeline.append({
            "timestamp": bucket,
            "counts": timeline_buckets[bucket]
        })
        
    # 3. Retrieve base details response
    details = get_work_details(db, work_id)
    
    return {
        "work_id": work_id,
        "source_breakdown": source_breakdown,
        "timeline": timeline,
        "evidence": details["attention"]["evidence"],
        "coverage": details["coverage"],
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "altmetric_score": details.get("altmetric_score")
    }

