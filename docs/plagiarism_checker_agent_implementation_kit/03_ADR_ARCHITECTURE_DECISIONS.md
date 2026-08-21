# Architecture Decision Records

## ADR-001 — Python remains the core implementation language

**Status:** Accepted

The plagiarism engine remains Python-native.

### Rationale
- existing engine is Python;
- strongest ecosystem for NLP/embeddings;
- avoids unnecessary rewrite risk.

---

## ADR-002 — spaCy is not the semantic similarity engine

**Status:** Accepted

spaCy is used for segmentation and linguistic processing only where needed.

### Consequence
`Doc.similarity()` from a transformer spaCy pipeline must not be used as the primary plagiarism signal.

---

## ADR-003 — Sentence embeddings are retrieval/evidence features

**Status:** Accepted

`all-mpnet-base-v2` may remain the baseline embedding model.

### Consequence
Cosine similarity alone must never classify plagiarism.

---

## ADR-004 — Hybrid retrieval

**Status:** Accepted

Candidate retrieval combines:
- lexical retrieval;
- dense semantic retrieval;
- exact phrase matching where useful.

### Rationale
Lexical retrieval is strong for copying; embeddings are strong for paraphrase.

---

## ADR-005 — Passage-level indexing

**Status:** Accepted

Corpus indexing is performed at passage/paragraph/window level rather than only at document level.

### Rationale
A small copied passage can be hidden inside a large otherwise unrelated document.

---

## ADR-006 — Persistent indexes

**Status:** Accepted

Indexes are built during ingestion/update, not during plagiarism requests.

---

## ADR-007 — Containment matters more than whole-document Jaccard

**Status:** Accepted

For query-passage-to-large-source matching, containment-aware retrieval is preferred.

Options:
- passage-level MinHash;
- MinHash LSH Ensemble;
- explicit containment computation after candidate retrieval.

---

## ADR-008 — Dense ANN index is required

**Status:** Accepted

MinHash/LSH does not replace semantic ANN search.

Initial recommendation:
- FAISS for local/single-node deployments;
- Qdrant when service-based scalable vector search is desired.

---

## ADR-009 — Source acquisition is provider-pluggable

**Status:** Accepted

PubMed and Europe PMC must implement a common provider contract.

Future providers can be added without changing similarity logic.

---

## ADR-010 — Plagiarism score is evidence-based

**Status:** Accepted

The final score/classification is derived from multiple features plus context.

---

## ADR-011 — Benchmarks control threshold changes

**Status:** Accepted

Threshold changes require evaluation against a fixed labeled dataset.

---

## ADR-012 — Rights enforcement occurs before persistence

**Status:** Accepted

Content may not be stored/indexed until rights policy allows it.

---

## ADR-013 — Citations and references are first-class context

**Status:** Accepted

References, quotations, and citation markers must affect classification/scoring.

---

## ADR-014 — Scientific boilerplate must be down-weighted

**Status:** Accepted

Corpus frequency is used to prevent common scientific phrases from inflating plagiarism scores.
