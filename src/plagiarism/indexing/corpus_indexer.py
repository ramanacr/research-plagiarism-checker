"""
Corpus indexer coordinating passage persistence, metadata, and index versioning.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.plagiarism.documents.models import Document, Passage
from src.plagiarism.documents.segmentation import process_document
from src.plagiarism.indexing.lexical.lsh import PersistentLexicalIndex
from src.plagiarism.config.settings import EngineConfig, get_default_config


class CorpusIndexer:
    """
    Coordinates ingestion, passage-level indexing, version tracking, and persistent storage.
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        lexical_index: Optional[PersistentLexicalIndex] = None,
    ):
        self.config = config or get_default_config()
        self.storage_dir = self.config.storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

        self.lexical_index = lexical_index or PersistentLexicalIndex(
            shingle_size=self.config.lexical.shingle_size,
            num_perm=self.config.lexical.minhash_num_perm,
            lsh_threshold=self.config.lexical.lsh_threshold,
            index_version=self.config.lexical.version,
        )

        # Document registry: doc_id -> metadata
        self.document_registry: Dict[str, Dict[str, Any]] = {}
        # Passage registry: passage_id -> Passage
        self.passage_store: Dict[str, Passage] = {}

        self.manifest_path = os.path.join(self.storage_dir, "corpus_manifest.json")
        self.lexical_path = os.path.join(self.storage_dir, "lexical_index.pkl")

    def index_document(
        self,
        document: Document,
        provider: str = "local",
        content_hash: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Indexes all valid passages of a document into the persistent indexes.
        Returns number of passages indexed.
        """
        doc_id = document.document_id
        c_hash = content_hash or hashlib.sha256(document.raw_text.encode("utf-8")).hexdigest()

        # Check incremental: if document already exists with identical content_hash, skip
        if doc_id in self.document_registry:
            if self.document_registry[doc_id].get("content_hash") == c_hash:
                return len([p for p in self.passage_store.values() if p.document_id == doc_id])
            # Content changed: delete old passages first
            self.delete_document(doc_id)

        indexed_count = 0
        for passage in document.passages:
            # Skip references from suspicious index
            self.lexical_index.insert_passage(
                passage_id=passage.passage_id,
                text_or_shingles=passage.normalized_text,
                document_id=doc_id,
                metadata={
                    "title": document.title,
                    "section": passage.section,
                    "section_type": passage.section_type.value,
                    "provider": provider,
                    "is_reference": passage.is_reference,
                    "is_quoted": passage.is_quoted,
                    "token_count": passage.token_count,
                    "start_offset": passage.start_offset,
                    "end_offset": passage.end_offset,
                },
            )
            self.passage_store[passage.passage_id] = passage
            indexed_count += 1

        self.document_registry[doc_id] = {
            "document_id": doc_id,
            "title": document.title,
            "provider": provider,
            "content_hash": c_hash,
            "passage_count": indexed_count,
            "word_count": document.word_count,
            "indexed_at": datetime.utcnow().isoformat() + "Z",
            "extra_metadata": extra_metadata or {},
        }

        return indexed_count

    def index_raw_text(
        self,
        document_id: str,
        text: str,
        title: str = "",
        provider: str = "local",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Helper to process and index raw text."""
        doc = process_document(
            document_id=document_id,
            text=text,
            title=title,
            settings=self.config.segmentation,
            metadata=extra_metadata,
        )
        return self.index_document(doc, provider=provider, extra_metadata=extra_metadata)

    def delete_document(self, document_id: str) -> int:
        """Removes a document and all its passages from registries and indexes."""
        self.document_registry.pop(document_id, None)
        
        # Remove from passage store
        pids_to_remove = [
            pid for pid, p in self.passage_store.items() if p.document_id == document_id
        ]
        for pid in pids_to_remove:
            self.passage_store.pop(pid, None)

        # Remove from lexical index
        return self.lexical_index.delete_document(document_id)

    def get_passage(self, passage_id: str) -> Optional[Passage]:
        """Retrieves a stored Passage by ID."""
        return self.passage_store.get(passage_id)

    def save_all(self) -> None:
        """Persists all indexes and manifests to storage_dir."""
        # 1. Save lexical index
        self.lexical_index.save(self.lexical_path)

        # 2. Save manifest & metadata
        manifest = {
            "engine_version": self.config.engine_version,
            "index_version": self.config.lexical.version,
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "total_documents": len(self.document_registry),
            "total_passages": len(self.passage_store),
            "documents": self.document_registry,
            "passages": {
                pid: p.to_dict() for pid, p in self.passage_store.items()
            }
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def load_all(self) -> None:
        """Loads all persistent indexes and manifests from storage_dir."""
        if os.path.exists(self.lexical_path):
            self.lexical_index = PersistentLexicalIndex.load(self.lexical_path)

        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            self.document_registry = manifest.get("documents", {})
            raw_passages = manifest.get("passages", {})
            for pid, pd in raw_passages.items():
                from src.plagiarism.documents.models import SectionType
                self.passage_store[pid] = Passage(
                    passage_id=pd["passage_id"],
                    document_id=pd["document_id"],
                    section=pd.get("section"),
                    section_type=SectionType(pd.get("section_type", "BODY")),
                    paragraph_index=pd.get("paragraph_index", 0),
                    text=pd.get("text", ""),
                    normalized_text=pd.get("normalized_text", ""),
                    start_offset=pd.get("start_offset", 0),
                    end_offset=pd.get("end_offset", 0),
                    token_count=pd.get("token_count", 0),
                    is_reference=pd.get("is_reference", False),
                    is_quoted=pd.get("is_quoted", False),
                    citation_present=pd.get("citation_present", False),
                )
