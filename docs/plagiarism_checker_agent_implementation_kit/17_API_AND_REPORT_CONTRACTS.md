# API and Report Contracts

## Plagiarism check request

Illustrative contract:

```json
{
  "document_id": "client-doc-123",
  "text": "...",
  "options": {
    "sources": ["pubmed", "europe_pmc"],
    "include_cited_matches": true,
    "include_common_phrases": false
  }
}
```

If file upload already exists, retain current transport and map internally to the same domain model.

## Result

```json
{
  "check_id": "chk_123",
  "engine_version": "2.0",
  "overall_matched_coverage": 18.4,
  "suspicious_coverage": 9.7,
  "quoted_or_cited_coverage": 6.2,
  "common_phrase_coverage": 2.5,
  "matches": [
    {
      "classification": "NEAR_EXACT_COPY",
      "confidence": 0.94,
      "query_span": {
        "start": 100,
        "end": 240
      },
      "source": {
        "provider": "europe_pmc",
        "pmid": "...",
        "doi": "...",
        "title": "..."
      },
      "evidence": {
        "exact_overlap": 0.81,
        "shingle_containment": 0.92,
        "semantic_similarity": 0.89,
        "matched_token_count": 58,
        "citation_present": false,
        "quoted_text": false
      }
    }
  ],
  "warnings": []
}
```

## Contract rules

- retain provenance;
- do not expose raw internal model vectors;
- return evidence sufficient to explain the match;
- distinguish similarity from plagiarism class;
- preserve compatibility with existing API where possible.

## Report wording

Preferred:
- "matched text"
- "similarity evidence"
- "likely paraphrase"
- "exact overlap"
- "cited overlap"

Avoid definitive legal/academic misconduct claims such as:
- "author plagiarized"
- "confirmed plagiarism"

unless the product explicitly has a human adjudication workflow.
