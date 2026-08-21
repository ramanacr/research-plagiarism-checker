# Acceptance Criteria

## Architecture

- [ ] PubMed and Europe PMC implement the provider abstraction.
- [ ] Similarity code has no provider-specific HTTP calls.
- [ ] Source corpus indexes persist between plagiarism requests.
- [ ] Indexing occurs at passage level.
- [ ] Lexical and dense retrieval are independently testable.
- [ ] All indexed passages preserve source provenance.
- [ ] Index/model versions are recorded.

## Accuracy

- [ ] Exact copied passages are detected.
- [ ] Near-exact passages are detected.
- [ ] Semantic paraphrase candidates can be retrieved.
- [ ] High-semantic/low-evidence matches are not automatically labeled plagiarism.
- [ ] Reference-list overlaps do not inflate suspicious score.
- [ ] Quoted/cited content is separately reported.
- [ ] Common scientific phrases are down-weighted.

## Evaluation

- [ ] Labeled benchmark exists.
- [ ] Retrieval Recall@K is measured.
- [ ] Classification precision/recall/F1 are measured.
- [ ] Thresholds are versioned.
- [ ] Regression tests run in CI or an explicitly defined evaluation pipeline.

## Performance

- [ ] No corpus-wide pairwise comparison at query time.
- [ ] No full LSH rebuild per request.
- [ ] No full vector-index rebuild per request.
- [ ] Query latency and memory are measured.
- [ ] Embeddings are batched.

## Reliability

- [ ] Provider failures are isolated.
- [ ] External calls have timeouts.
- [ ] Ingestion is idempotent.
- [ ] Index deletion/update works.
- [ ] Failed ingestion can resume from checkpoint.

## Security/Rights

- [ ] Secrets are not committed.
- [ ] Rights decision precedes content persistence.
- [ ] Raw full text is not logged.
- [ ] User-document retention policy is explicit.
