"""
Ingestion service managing rights-aware document ingestion and checkpointing.
"""

import os
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.plagiarism.documents.models import Document
from src.plagiarism.documents.segmentation import process_document
from src.plagiarism.indexing.corpus_indexer import CorpusIndexer
from src.plagiarism.rights.resolver import RightsResolver
from src.plagiarism.providers.base import SourceRecord, SourceDocument, ScholarlyContentProvider
from src.plagiarism.config.settings import EngineConfig, get_default_config


class IngestionService:
    """
    Coordinates rights verification, passage extraction, and indexing with checkpointing.
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        corpus_indexer: Optional[CorpusIndexer] = None,
        rights_resolver: Optional[RightsResolver] = None,
    ):
        self.config = config or get_default_config()
        self.corpus_indexer = corpus_indexer or CorpusIndexer(config=self.config)
        self.rights_resolver = rights_resolver or RightsResolver(self.config.rights)
        self.checkpoint_path = os.path.join(self.config.storage_dir, "ingestion_checkpoint.json")

    def ingest_source_document(
        self,
        source_doc: SourceDocument,
        provider_name: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluates rights and indexes a single source document.
        """
        # 1. Rights evaluation (ADR-012)
        decision = self.rights_resolver.evaluate_rights(
            rights_id=source_doc.rights_id,
            provider=provider_name or source_doc.provider,
            is_open_access=source_doc.full_text_available,
        )

        if not decision.allowed_to_index:
            return {
                "status": "denied",
                "document_id": source_doc.document_id,
                "reason": f"Rights policy denied indexing: {decision.reason}",
            }

        # 2. Process content into passages
        content = source_doc.full_text or source_doc.abstract or ""
        if not content.strip():
            return {
                "status": "empty",
                "document_id": source_doc.document_id,
                "reason": "No textual content available to index",
            }

        doc = process_document(
            document_id=source_doc.document_id,
            text=content,
            title=source_doc.title,
            settings=self.config.segmentation,
            metadata={
                "provider": source_doc.provider,
                "pmid": source_doc.pmid,
                "pmcid": source_doc.pmcid,
                "doi": source_doc.doi,
                "authors": list(source_doc.authors),
                "journal": source_doc.journal,
                "year": source_doc.publication_year,
            },
        )

        # 3. Index passages
        p_count = self.corpus_indexer.index_document(
            document=doc,
            provider=source_doc.provider,
            content_hash=source_doc.content_hash,
            extra_metadata=doc.metadata,
        )

        return {
            "status": "indexed",
            "document_id": source_doc.document_id,
            "passages_indexed": p_count,
            "rights_policy": decision.reason,
        }

    def bulk_ingest_records(
        self,
        records: List[SourceRecord],
        provider: ScholarlyContentProvider,
    ) -> Dict[str, Any]:
        """
        Bulk ingests a batch of records, saving checkpoints incrementally.
        """
        start = time.time()
        processed = 0
        indexed = 0
        denied = 0

        for rec in records:
            # Checkpoint save
            source_doc = SourceDocument(
                document_id=f"{provider.name}:{rec.source_id}",
                provider=provider.name,
                provider_source_id=rec.source_id,
                doi=rec.doi,
                pmid=rec.pmid,
                pmcid=rec.pmcid,
                title=rec.title,
                abstract=rec.abstract,
                full_text=rec.abstract,
                authors=rec.authors,
                journal=rec.journal,
                publication_year=rec.publication_year,
                rights_id="abstract_fair_use",
            )
            res = self.ingest_source_document(source_doc)
            processed += 1
            if res["status"] == "indexed":
                indexed += 1
            elif res["status"] == "denied":
                denied += 1

        self.corpus_indexer.save_all()
        self._save_checkpoint({"last_processed": datetime.utcnow().isoformat(), "total_processed": processed})

        return {
            "total_processed": processed,
            "total_indexed": indexed,
            "total_denied": denied,
            "elapsed_seconds": round(time.time() - start, 2),
        }

    def _save_checkpoint(self, data: Dict[str, Any]) -> None:
        try:
            with open(self.checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
