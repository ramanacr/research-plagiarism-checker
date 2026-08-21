# Testing and Evaluation

## Required test layers

### Unit tests
Cover:
- normalization;
- segmentation;
- shingling;
- containment;
- scoring math;
- citation handling;
- boilerplate weighting;
- provider parsing.

### Provider integration tests
Use mocked HTTP for deterministic CI.
Optionally run limited live contract checks outside normal CI.

### Index integration tests
Verify:
- insert;
- search;
- update;
- delete;
- version isolation;
- metadata integrity.

### End-to-end tests
Input manuscript → report.

## Labeled benchmark

Create a versioned benchmark with categories:

1. exact copy
2. light paraphrase
3. heavy paraphrase
4. legitimate quotation
5. cited overlap
6. common scientific phrase
7. methods boilerplate
8. unrelated passages
9. self-reuse
10. translated plagiarism — future if multilingual support exists

## Metrics

Measure at minimum:
- precision
- recall
- F1
- false-positive rate
- false-negative rate
- PR-AUC where useful
- retrieval Recall@K
- MRR / nDCG for retrieval evaluation
- latency p50/p95
- memory usage

## Two-stage evaluation

### Retrieval
Question:
"Did the correct source passage appear in the candidate set?"

Primary metric:
Recall@K.

### Classification
Question:
"Was the candidate correctly categorized?"

Primary metrics:
precision/recall/F1 by class.

## Regression gate

No scoring/retrieval change may merge if:
- benchmark recall materially regresses;
- false positives materially increase;
- latency/memory exceeds agreed budget without approval.

Store benchmark results as artifacts.

## Synthetic test generation

Synthetic examples may supplement the benchmark but must not replace human-reviewed examples.

## Threshold calibration

Thresholds must be derived using validation data and then frozen for test evaluation.

Avoid tuning and evaluating on the same examples.
