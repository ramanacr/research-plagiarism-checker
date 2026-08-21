# Python Module Design

Suggested target package layout:

```text
src/
  plagiarism/
    __init__.py

    config/
      settings.py
      models.py

    providers/
      base.py
      registry.py
      pubmed.py
      europe_pmc.py
      future/

    rights/
      models.py
      resolver.py
      policies.py

    documents/
      models.py
      normalize.py
      structure.py
      references.py
      quotes.py
      segmentation.py

    indexing/
      lexical/
        shingles.py
        minhash.py
        lsh.py
      vector/
        embedder.py
        faiss_index.py
        qdrant_index.py
      corpus_indexer.py

    retrieval/
      lexical.py
      semantic.py
      exact.py
      fusion.py

    matching/
      exact.py
      lexical.py
      semantic.py
      cross_encoder.py
      features.py

    scoring/
      models.py
      boilerplate.py
      citations.py
      classifier.py
      aggregate.py

    reporting/
      models.py
      builder.py

    services/
      plagiarism_service.py
      ingestion_service.py

    observability/
      logging.py
      metrics.py
      tracing.py
```

## Provider contract

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

class ScholarlyContentProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list["SourceRecord"]:
        ...

    @abstractmethod
    async def get_metadata(self, source_id: str) -> Optional["SourceRecord"]:
        ...

    @abstractmethod
    async def get_full_text(self, source_id: str) -> Optional["SourceDocument"]:
        ...

    @abstractmethod
    async def health_check(self) -> "ProviderHealth":
        ...
```

## Core domain objects

```python
@dataclass(frozen=True)
class SourceRecord:
    provider: str
    source_id: str
    doi: str | None
    pmid: str | None
    pmcid: str | None
    title: str
    abstract: str | None
    authors: tuple[str, ...]
    publication_year: int | None

@dataclass
class Passage:
    passage_id: str
    document_id: str
    section: str | None
    paragraph_index: int
    text: str
    normalized_text: str
    start_offset: int
    end_offset: int
    token_count: int

@dataclass
class MatchEvidence:
    query_passage_id: str
    source_passage_id: str
    exact_overlap: float
    shingle_containment: float
    jaccard_similarity: float
    semantic_similarity: float
    cross_encoder_score: float | None
    rare_phrase_weight: float
    matched_token_count: int
    citation_present: bool
    quoted_text: bool
    boilerplate_score: float
```

## Service boundary

`PlagiarismService` should orchestrate:
1. query document processing;
2. retrieval;
3. detailed matching;
4. scoring;
5. report construction.

It must not know provider HTTP details.
