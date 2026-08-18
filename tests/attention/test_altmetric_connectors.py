import pytest
from unittest.mock import patch, MagicMock
from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.connectors.twitter import TwitterConnector
from src.attention.connectors.facebook import FacebookConnector
from src.attention.connectors.policy_documents import PolicyDocumentsConnector
from src.attention.connectors.news import NewsConnector
from src.attention.connectors.blogs import BlogsConnector
from src.attention.connectors.mendeley import MendeleyConnector
from src.attention.connectors.scopus import ScopusConnector
from src.attention.connectors.publons import PublonsConnector
from src.attention.connectors.reddit import RedditConnector
from src.attention.connectors.stackoverflow import StackOverflowConnector
from src.attention.connectors.f1000 import F1000Connector
from src.attention.connectors.google_plus import GooglePlusConnector
from src.attention.connectors.youtube import YouTubeConnector
from src.attention.connectors.open_syllabus import OpenSyllabusConnector
from src.attention.connectors.web_of_science import WebOfScienceConnector
from src.attention.connectors.legacy_sources import (
    SinaWeiboConnector,
    CiteULikeConnector,
    PinterestConnector,
    LinkedInConnector
)
from src.attention.connectors.registry import ConnectorRegistry

@pytest.fixture
def mock_work():
    work = ResearchWork(id="wrk_test1", normalized_title="Sample Title")
    ident_doi = WorkIdentifier(work_id="wrk_test1", scheme="doi", normalized_value="10.1000/182", display_value="10.1000/182")
    ident_pmid = WorkIdentifier(work_id="wrk_test1", scheme="pmid", normalized_value="12345678", display_value="12345678")
    work.identifiers = [ident_doi, ident_pmid]
    return work

@pytest.fixture
def mock_empty_work():
    work = ResearchWork(id="wrk_test2", normalized_title="Empty Identifiers Work")
    work.identifiers = []
    return work

def test_registry_contains_all_table_1_sources():
    registry = ConnectorRegistry()
    sources = registry.get_all_sources()
    
    # Table 1 Active Sources
    assert "twitter" in sources
    assert "facebook" in sources
    assert "policy_documents" in sources
    assert "news" in sources
    assert "blogs" in sources
    assert "mendeley" in sources
    assert "scopus" in sources
    assert "pubpeer" in sources
    assert "publons" in sources
    assert "reddit" in sources
    assert "wikipedia" in sources
    assert "stackoverflow" in sources
    assert "f1000" in sources
    assert "google_plus" in sources
    assert "youtube" in sources
    assert "open_syllabus" in sources
    assert "web_of_science" in sources

    # Table 1 Footnote Discontinued Sources
    assert "sina_weibo" in sources
    assert "citeulike" in sources
    assert "pinterest" in sources
    assert "linkedin" in sources

def test_connectors_handle_empty_work(mock_empty_work):
    connectors = [
        TwitterConnector(),
        FacebookConnector(),
        PolicyDocumentsConnector(),
        NewsConnector(),
        BlogsConnector(),
        MendeleyConnector(),
        ScopusConnector(),
        PublonsConnector(),
        RedditConnector(),
        StackOverflowConnector(),
        F1000Connector(),
        GooglePlusConnector(),
        YouTubeConnector(),
        OpenSyllabusConnector(),
        WebOfScienceConnector(),
        SinaWeiboConnector(),
        CiteULikeConnector(),
        PinterestConnector(),
        LinkedInConnector()
    ]
    for conn in connectors:
        res = conn.collect(mock_empty_work)
        assert res.state == "ready"
        assert res.item_count == 0
        assert res.evidence == []

@patch("requests.get")
def test_twitter_connector(mock_get, mock_work):
    conn = TwitterConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "123456",
                "text": "Check out this paper: 10.1000/182",
                "author_id": "999",
                "created_at": "2026-08-01T12:00:00Z"
            }
        ]
    }
    mock_get.return_value = mock_resp

    with patch("src.config.TWITTER_BEARER_TOKEN", "fake_token"):
        res = conn.collect(mock_work)
        assert res.source == "twitter"
        assert res.state == "ready"
        assert res.item_count == 1
        assert res.evidence[0]["matched_identifier"] == "doi:10.1000/182"
        assert res.evidence[0]["external_id"] == "123456"

@patch("requests.get")
def test_policy_documents_connector(mock_get, mock_work):
    conn = PolicyDocumentsConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "id": "pol_1",
                "title": "WHO Clinical Guideline",
                "publication_date": "2026-07-01",
                "primary_location": {
                    "landing_page_url": "https://who.int/policy/report.pdf"
                }
            }
        ]
    }
    mock_get.return_value = mock_resp

    res = conn.collect(mock_work)
    assert res.source == "policy_documents"
    assert res.state == "ready"
    assert res.item_count == 1
    assert res.evidence[0]["external_id"] == "pol_1"
    assert res.evidence[0]["source_type"] == "policy_reference"

@patch("requests.get")
def test_mendeley_connector(mock_get, mock_work):
    conn = MendeleyConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": "mendeley_doc_1",
            "reader_count": 85,
            "link": "https://www.mendeley.com/catalogue/sample-doc/"
        }
    ]
    mock_get.return_value = mock_resp

    res = conn.collect(mock_work)
    assert res.source == "mendeley"
    assert res.state == "ready"
    assert res.item_count == 1
    assert res.evidence[0]["source_type"] == "readership"
    assert res.evidence[0]["raw_reference_json"]["reader_count"] == 85

@patch("requests.get")
def test_reddit_connector(mock_get, mock_work):
    conn = RedditConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "reddit_post_1",
                        "title": "Interesting findings in 10.1000/182",
                        "permalink": "/r/science/comments/123/interesting/",
                        "created_utc": 1722500000
                    }
                }
            ]
        }
    }
    mock_get.return_value = mock_resp

    res = conn.collect(mock_work)
    assert res.source == "reddit"
    assert res.state == "ready"
    assert res.item_count == 1
    assert res.evidence[0]["source_type"] == "post"
    assert res.evidence[0]["external_id"] == "reddit_post_1"
