import pytest
from src.attention.scoring import AttentionScoreCalculator, SOURCE_WEIGHTS, DONUT_COLORS

def test_empty_evidence_scoring():
    res = AttentionScoreCalculator.calculate_score([])
    assert res["score"] == 0.0
    assert res["integer_score"] == 0
    assert res["donut"]["slices"] == []
    assert res["metrics"]["mendeley_readers"] == 0
    assert res["metrics"]["citation_counts"] == 0


def test_source_weights_and_volume_author_deduplication():
    # Table 2: Volume rule: Only 1 mention from each person per source is counted.
    evidence = [
        # Author 1 tweets twice -> should count as 1 tweet (weight 1.0)
        {
            "source": "twitter",
            "source_type": "tweet",
            "url": "https://twitter.com/user1/status/1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "user1", "id": "1"},
            "active": True
        },
        {
            "source": "twitter",
            "source_type": "tweet",
            "url": "https://twitter.com/user1/status/2",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "user1", "id": "2"},
            "active": True
        },
        # Author 2 tweets once -> should count as 1 tweet (weight 1.0)
        {
            "source": "twitter",
            "source_type": "tweet",
            "url": "https://twitter.com/user2/status/3",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "user2", "id": "3"},
            "active": True
        },
        # News article -> weight 8.0
        {
            "source": "news",
            "source_type": "news_article",
            "url": "https://nytimes.com/article1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "NYT Journalist", "id": "nyt_1"},
            "active": True
        },
        # Policy document -> weight 3.0
        {
            "source": "policy_documents",
            "source_type": "policy_reference",
            "url": "https://who.int/policy/doc1.pdf",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "WHO Policy Group", "id": "who_1"},
            "active": True
        },
        # Blog post -> weight 5.0
        {
            "source": "blogs",
            "source_type": "blog_post",
            "url": "https://scienceblog.org/post1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "Blogger1", "id": "b1"},
            "active": True
        },
        # Facebook post -> weight 0.25
        {
            "source": "facebook",
            "source_type": "post",
            "url": "https://facebook.com/post1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "FBUser1", "id": "fb_1"},
            "active": True
        },
        # Reddit post -> weight 0.25
        {
            "source": "reddit",
            "source_type": "post",
            "url": "https://reddit.com/r/science/post1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "Redditor1", "id": "rd_1"},
            "active": True
        },
        # Mendeley -> separate readership count (weight 0.0)
        {
            "source": "mendeley",
            "source_type": "readership",
            "url": "https://mendeley.com/doc1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"reader_count": 42},
            "active": True
        },
        # Scopus -> separate citation count (weight 0.0)
        {
            "source": "scopus",
            "source_type": "citation_record",
            "url": "https://scopus.com/doc1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"citation_count": 15},
            "active": True
        }
    ]

    res = AltmetricScoreCalculator.calculate_score(evidence)
    # Total score = 2 * 1.0 (Twitter) + 8.0 (News) + 3.0 (Policy) + 5.0 (Blogs) + 0.25 (Facebook) + 0.25 (Reddit)
    # = 2.0 + 8.0 + 3.0 + 5.0 + 0.25 + 0.25 = 18.5
    assert res["score"] == 18.5
    assert res["integer_score"] == 19  # rounded up
    assert res["metrics"]["mendeley_readers"] == 42
    assert res["metrics"]["citation_counts"] == 15

    # Check donut breakdown
    slices = res["donut"]["slices"]
    sources_in_donut = {s["source"]: s for s in slices}
    assert "news" in sources_in_donut
    assert sources_in_donut["news"]["color"] == DONUT_COLORS["news"]
    assert sources_in_donut["news"]["subscore"] == 8.0
    assert sources_in_donut["twitter"]["unique_authors"] == 2
    assert sources_in_donut["twitter"]["subscore"] == 2.0
    assert "mendeley" not in sources_in_donut  # 0.0 weight sources omitted from score donut

def test_inactive_evidence_is_ignored():
    evidence = [
        {
            "source": "news",
            "source_type": "news_article",
            "url": "https://news.org/1",
            "matched_identifier": "doi:10.1000/1",
            "match_confidence": "exact_identifier",
            "raw_reference_json": {"author": "Author1"},
            "active": False  # Inactive
        }
    ]
    res = AltmetricScoreCalculator.calculate_score(evidence)
    assert res["score"] == 0.0
    assert res["integer_score"] == 0
