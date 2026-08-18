import uuid
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.attention.models import ResearchWork, WorkIdentifier, AttentionEvidence, SourceRefresh, AttentionJob
from src.attention.connectors.registry import ConnectorRegistry

def save_evidence(db: Session, work_id: str, results: List[Dict[str, Any]]):
    """
    Saves external evidence, ensuring deduplication at URL or external ID level.
    Only exact_identifier and canonical_url matches are set as active=True.
    """
    for item in results:
        url = item.get("url")
        if not url:
            continue
        url_hash = AttentionEvidence.compute_url_hash(url)
        
        confidence = item.get("match_confidence", "probable")
        active = confidence in ("exact_identifier", "canonical_url")
        
        ext_id = item.get("external_id")
        existing = None
        if ext_id:
            existing = db.query(AttentionEvidence).filter_by(
                work_id=work_id, 
                source=item.get("source"), 
                external_id=ext_id
            ).first()
        if not existing:
            existing = db.query(AttentionEvidence).filter_by(
                work_id=work_id, 
                source=item.get("source"), 
                url_hash=url_hash
            ).first()

        if existing:
            # Deduplicate by updating the existing entry
            existing.active = active
            existing.match_confidence = confidence
            existing.title = item.get("title", existing.title)
            existing.url = url
            existing.url_hash = url_hash
            existing.raw_reference_json = item.get("raw_reference_json", existing.raw_reference_json)
        else:
            evidence_id = f"evd_{uuid.uuid4().hex[:16]}"
            new_evidence = AttentionEvidence(
                id=evidence_id,
                work_id=work_id,
                source=item.get("source"),
                source_type=item.get("source_type"),
                external_id=ext_id,
                url=url,
                url_hash=url_hash,
                title=item.get("title"),
                published_at=item.get("published_at"),
                matched_identifier=item.get("matched_identifier"),
                match_confidence=confidence,
                raw_reference_json=item.get("raw_reference_json"),
                active=active
            )
            db.add(new_evidence)
    db.commit()

def get_work_details(db: Session, work_id: str) -> Dict[str, Any]:
    """
    Assembles the standard canonical lookup details response for a resolved work.
    """
    work = db.query(ResearchWork).filter_by(id=work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Canonical work record not found.")

    # Format identifiers
    idents_dict = {"pmid": None, "doi": None, "pmcid": None, "openalex_id": None}
    for ident in work.identifiers:
        if ident.scheme in idents_dict:
            idents_dict[ident.scheme] = ident.normalized_value

    summary = []
    evidence_items = []
    
    registry = ConnectorRegistry()
    all_sources = registry.get_all_sources()

    for source in all_sources:
        # Summary counts are derived strictly from active evidence
        count = db.query(AttentionEvidence).filter_by(
            work_id=work.id, 
            source=source, 
            active=True
        ).count()
        
        refresh = db.query(SourceRefresh).filter_by(work_id=work.id, source=source).first()
        
        state = "ready"
        last_refreshed = None
        if not registry.is_enabled(source):
            state = "not_configured"
        elif refresh:
            state = refresh.state
            if refresh.completed_at:
                last_refreshed = refresh.completed_at.isoformat() + "Z"

        summary.append({
            "source": source,
            "evidence_count": count,
            "coverage_status": "complete_for_connector_scope" if state == "ready" else state,
            "last_refreshed_at": last_refreshed
        })

    # Fetch active evidence items
    active_evidences = db.query(AttentionEvidence).filter_by(
        work_id=work.id, 
        active=True
    ).order_by(AttentionEvidence.discovered_at.desc()).all()
    
    for ev in active_evidences:
        evidence_items.append({
            "evidence_id": ev.id,
            "source": ev.source,
            "source_type": ev.source_type,
            "url": ev.url,
            "title": ev.title,
            "published_at": ev.published_at.isoformat() + "Z" if ev.published_at else None,
            "discovered_at": ev.discovered_at.isoformat() + "Z",
            "matched_identifier": ev.matched_identifier,
            "match_confidence": ev.match_confidence
        })

    # Detail status of connectors
    sources_coverage = []
    next_refresh_after = None
    for source in all_sources:
        refresh = db.query(SourceRefresh).filter_by(work_id=work.id, source=source).first()
        state = "ready"
        reason = None
        if not registry.is_enabled(source):
            state = "not_configured"
            reason = "Provider credential not configured"
        elif refresh:
            state = refresh.state
            if refresh.error_message:
                reason = refresh.error_message
            if refresh.next_refresh_at:
                next_refresh_after = refresh.next_refresh_at.isoformat() + "Z"
                
        sources_coverage.append({
            "source": source,
            "state": state,
            "reason": reason
        })

    # Formulate overall sync state
    refresh_states = [sc["state"] for sc in sources_coverage if sc["state"] != "not_configured"]
    overall_state = "ready"
    if "running" in refresh_states:
        overall_state = "running"
    elif "queued" in refresh_states:
        overall_state = "queued"
    elif "failed" in refresh_states:
        overall_state = "failed"

    # Calculate Research Attention Score and Donut breakdown
    from src.attention.scoring import AttentionScoreCalculator
    evidence_dicts_for_scoring = []
    for ev in active_evidences:
        evidence_dicts_for_scoring.append({
            "source": ev.source,
            "source_type": ev.source_type,
            "external_id": ev.external_id,
            "url": ev.url,
            "title": ev.title,
            "published_at": ev.published_at,
            "matched_identifier": ev.matched_identifier,
            "match_confidence": ev.match_confidence,
            "raw_reference_json": ev.raw_reference_json,
            "active": ev.active
        })
    score_details = AttentionScoreCalculator.calculate_score(evidence_dicts_for_scoring)

    return {
        "work_id": work.id,
        "status": "ready" if overall_state == "ready" else "queued",
        "canonical_work": {
            "title": work.normalized_title,
            "journal": work.journal,
            "publication_date": work.publication_date.isoformat() if work.publication_date else None,
            "authors": work.authors or []
        },
        "identifiers": idents_dict,
        "attention": {
            "summary": summary,
            "evidence": evidence_items
        },
        "coverage": {
            "refresh_state": overall_state,
            "next_refresh_after": next_refresh_after,
            "sources": sources_coverage
        },
        "attention_score": score_details,
        "altmetric_score": score_details
    }


