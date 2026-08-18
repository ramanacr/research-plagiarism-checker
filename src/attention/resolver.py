import uuid
import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.schemas import ResolvedWork
from src.attention.providers.base import normalize_doi, normalize_pmid
from src.attention.providers.pubmed import PubMedProvider
from src.attention.providers.europe_pmc import EuropePMCProvider
from src.attention.providers.crossref import CrossrefProvider
from src.attention.providers.openalex import OpenAlexProvider

class IdentifierConflictException(Exception):
    pass

class WorkResolver:
    def __init__(self):
        self.providers = [
            PubMedProvider(),
            EuropePMCProvider(),
            CrossrefProvider(),
            OpenAlexProvider()
        ]

    def _get_existing_work_by_identifier(self, db: Session, scheme: str, val: str) -> Optional[ResearchWork]:
        ident = db.query(WorkIdentifier).filter_by(scheme=scheme, normalized_value=val).first()
        return ident.work if ident else None

    def resolve_work(self, db: Session, pmid: Optional[str] = None, doi: Optional[str] = None) -> ResearchWork:
        norm_pmid = normalize_pmid(pmid) if pmid else None
        norm_doi = normalize_doi(doi) if doi else None

        if not norm_pmid and not norm_doi:
            raise HTTPException(status_code=400, detail="Must provide a valid PMID or DOI.")

        # 1. Check local database cache
        existing_work = None
        if norm_pmid:
            existing_work = self._get_existing_work_by_identifier(db, "pmid", norm_pmid)
        if not existing_work and norm_doi:
            existing_work = self._get_existing_work_by_identifier(db, "doi", norm_doi)

        if existing_work:
            return existing_work

        # 2. Query external identity providers sequentially
        resolved_metadata: Optional[ResolvedWork] = None
        
        # Try PubMed first
        if norm_pmid:
            resolved_metadata = self.providers[0].resolve_pmid(norm_pmid)
        elif norm_doi:
            resolved_metadata = self.providers[0].resolve_doi(norm_doi)

        # Fallback to Europe PMC
        if not resolved_metadata:
            if norm_pmid:
                resolved_metadata = self.providers[1].resolve_pmid(norm_pmid)
            elif norm_doi:
                resolved_metadata = self.providers[1].resolve_doi(norm_doi)

        # Fallback to Crossref (DOIs only)
        if not resolved_metadata and norm_doi:
            resolved_metadata = self.providers[2].resolve_doi(norm_doi)

        # Fallback to OpenAlex
        if not resolved_metadata:
            if norm_pmid:
                resolved_metadata = self.providers[3].resolve_pmid(norm_pmid)
            elif norm_doi:
                resolved_metadata = self.providers[3].resolve_doi(norm_doi)

        if not resolved_metadata:
            raise HTTPException(status_code=404, detail="Publication could not be resolved from any life sciences provider.")

        # Cross-enrich missing identifiers (e.g. if PubMed omitted DOI, query Europe PMC & OpenAlex)
        if norm_pmid and not resolved_metadata.doi:
            try:
                epmc_meta = self.providers[1].resolve_pmid(norm_pmid)
                if epmc_meta:
                    if epmc_meta.doi:
                        resolved_metadata.doi = epmc_meta.doi
                    if epmc_meta.pmcid and not resolved_metadata.pmcid:
                        resolved_metadata.pmcid = epmc_meta.pmcid
            except Exception:
                pass

            if not resolved_metadata.doi:
                try:
                    oa_meta = self.providers[3].resolve_pmid(norm_pmid)
                    if oa_meta:
                        if oa_meta.doi:
                            resolved_metadata.doi = oa_meta.doi
                        if oa_meta.openalex_id and not resolved_metadata.openalex_id:
                            resolved_metadata.openalex_id = oa_meta.openalex_id
                except Exception:
                    pass


        # Re-verify and resolve identifiers returned by the provider
        resolved_ids = {}
        if resolved_metadata.pmid:
            resolved_ids["pmid"] = normalize_pmid(resolved_metadata.pmid)
        if resolved_metadata.doi:
            resolved_ids["doi"] = normalize_doi(resolved_metadata.doi)
        if resolved_metadata.pmcid:
            resolved_ids["pmcid"] = resolved_metadata.pmcid.strip()
        if resolved_metadata.openalex_id:
            resolved_ids["openalex_id"] = resolved_metadata.openalex_id.strip()


        # Check for conflicts against resolved IDs
        matched_works = {}
        for scheme, val in resolved_ids.items():
            work = self._get_existing_work_by_identifier(db, scheme, val)
            if work:
                matched_works[work.id] = work

        if len(matched_works) > 1:
            # Conflict: resolved identifiers map to two different pre-existing works!
            raise HTTPException(
                status_code=409, 
                detail="Conflicting supplied identifiers are discovered during resolution flow."
            )

        if matched_works:
            # We found a single matching work in db. Reuse it and add the new identifiers to it.
            existing_work = list(matched_works.values())[0]
            
            # Save any new identifiers discovered
            for scheme, val in resolved_ids.items():
                existing_ident = db.query(WorkIdentifier).filter_by(work_id=existing_work.id, scheme=scheme, normalized_value=val).first()
                if not existing_ident:
                    new_ident = WorkIdentifier(
                        work_id=existing_work.id,
                        scheme=scheme,
                        normalized_value=val,
                        display_value=val,
                        source="reconciliation"
                    )
                    db.add(new_ident)
            db.commit()
            return existing_work

        # 3. Create a new canonical work entry
        work_id = f"wrk_{uuid.uuid4().hex[:16]}"
        new_work = ResearchWork(
            id=work_id,
            normalized_title=resolved_metadata.title.lower().strip(),
            journal=resolved_metadata.journal,
            publication_date=resolved_metadata.publication_date,
            authors=resolved_metadata.authors
        )
        db.add(new_work)

        # Store identifiers
        for scheme, val in resolved_ids.items():
            new_ident = WorkIdentifier(
                work_id=work_id,
                scheme=scheme,
                normalized_value=val,
                display_value=val,
                source="resolution"
            )
            db.add(new_ident)

        db.commit()
        db.refresh(new_work)
        return new_work
