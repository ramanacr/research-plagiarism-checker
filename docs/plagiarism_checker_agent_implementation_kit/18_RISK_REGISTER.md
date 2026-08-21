# Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Semantic similarity treated as plagiarism | High false positives | Multi-signal classification |
| Query-time index rebuild | Severe scalability failure | Persistent indexes |
| Whole-document similarity only | Missed local plagiarism | Passage-level indexing |
| Jaccard on very unequal text sizes | False negatives | Containment-aware retrieval |
| Common scientific phrases | False positives | Corpus-frequency weighting |
| References included | Inflated similarity | Structural exclusion/marking |
| Embedding model change mixes vectors | Corrupt retrieval | Versioned indexes |
| Provider outage | Incomplete checks | Provider isolation + warnings |
| Rights unclear | Legal/commercial exposure | Fail-closed rights layer |
| Raw content logged | Security/copyright issue | Structured metadata-only logs |
| Uncalibrated thresholds | Unreliable results | Labeled benchmark |
| Corpus growth hurts latency | Poor UX/cost | ANN + LSH + profiling |
| Cross-encoder overuse | Excessive latency | Candidate-only reranking |
| Duplicate sources | Duplicate evidence | DOI/PMID/PMCID canonicalization |
| Old source versions remain indexed | Stale evidence | Content hash + replacement |
