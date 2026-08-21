# Plagiarism Checker Agent — Implementation Kit

This package defines the implementation plan for evolving the current Python plagiarism checker from a PubMed + Europe PMC similarity checker into a scalable, evidence-based plagiarism detection engine.

## Current state

The current engine has already implemented:

- spaCy-based sentence processing.
- `sentence-transformers` with `all-mpnet-base-v2`.
- text shingling.
- MinHash / LSH candidate pre-filtering.
- PubMed and Europe PMC as current scholarly sources.

These are retained where useful, but several architectural corrections are required:

1. spaCy transformer models must not be treated as the semantic plagiarism engine.
2. semantic similarity is only one signal and must not be equated with plagiarism.
3. MinHash/LSH must be persistent and passage-level rather than rebuilt per query.
4. plagiarism detection must use hybrid lexical + semantic retrieval.
5. source discovery, content acquisition, rights handling, indexing, similarity, and scoring must be separate layers.
6. citation/reference handling and scientific-boilerplate suppression are required.
7. all production thresholds must be calibrated on a labeled benchmark.

## Documents

1. `01_CODING_AGENT_INSTRUCTIONS.md`
2. `02_TARGET_ARCHITECTURE.md`
3. `03_ADR_ARCHITECTURE_DECISIONS.md`
4. `04_PYTHON_MODULE_DESIGN.md`
5. `05_INGESTION_AND_INDEXING.md`
6. `06_HYBRID_RETRIEVAL_AND_MATCHING.md`
7. `07_SCORING_AND_CLASSIFICATION.md`
8. `08_SOURCE_PROVIDER_STRATEGY.md`
9. `09_DATA_MODEL_AND_STORAGE.md`
10. `10_CONFIGURATION.md`
11. `11_TESTING_AND_EVALUATION.md`
12. `12_OBSERVABILITY_AND_OPERATIONS.md`
13. `13_SECURITY_AND_CONTENT_RIGHTS.md`
14. `14_IMPLEMENTATION_PHASES.md`
15. `15_ACCEPTANCE_CRITERIA.md`
16. `16_MIGRATION_FROM_CURRENT_ENGINE.md`
17. `17_API_AND_REPORT_CONTRACTS.md`
18. `18_RISK_REGISTER.md`

## Non-negotiable design principle

The system must never reduce plagiarism detection to:

`semantic_similarity >= threshold`

Instead it must produce source-attributed evidence from multiple independent signals and classify that evidence using calibrated logic.
