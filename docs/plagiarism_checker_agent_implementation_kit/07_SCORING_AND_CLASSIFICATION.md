# Scoring and Classification

## Principle

Similarity and plagiarism are not synonyms.

The engine should first generate evidence, then classify that evidence.

## Feature groups

### Lexical
- exact overlap ratio
- longest copied span
- shingle containment
- token overlap
- edit similarity

### Semantic
- embedding cosine
- cross-encoder score

### Context
- citation present
- quote present
- section
- bibliography/reference
- boilerplate/common phrase score

### Provenance
- source type
- source date
- same-author/self-reuse indicator if available

## Initial classification rules

The first production version may use calibrated deterministic rules.

Examples only:

### EXACT_COPY
Strong exact span + high containment + sufficient matched length.

### NEAR_EXACT_COPY
High lexical containment with moderate edit differences.

### LIKELY_PARAPHRASE
Strong semantic/cross-encoder signal + non-trivial lexical relationship + sufficient passage length.

### POSSIBLE_PARAPHRASE
Strong semantic signal but weak lexical evidence.

### COMMON_PHRASE
High corpus frequency and short/standard phrase.

### PROPERLY_QUOTED
Strong overlap where query passage is explicitly quoted and cited.

### CITED_OVERLAP
Strong overlap but inline citation context is present.

### REFERENCE_ONLY
Match occurs only in bibliography/reference material.

## Overall similarity percentage

Do not sum pairwise similarity percentages.

Recommended approach:

1. identify non-overlapping matched spans in the query document;
2. assign each span a contribution according to class;
3. merge overlapping spans;
4. calculate covered query tokens;
5. report:
   - raw matched coverage;
   - suspicious matched coverage;
   - quoted/cited matched coverage separately.

Example report fields:

```text
overall_matched_coverage: 18.4%
suspicious_coverage: 9.7%
quoted_or_cited_coverage: 6.2%
common_phrase_coverage: 2.5%
```

## Threshold management

All thresholds belong in configuration and must include:
- value;
- version;
- benchmark date;
- benchmark dataset version.

Never scatter thresholds as constants across modules.
