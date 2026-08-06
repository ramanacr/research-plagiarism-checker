import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.resolver import WorkResolver
from src.attention.schemas import ResolvedWork
from src.config import RESEARCH_ATTENTION_DATABASE_URL
import datetime

class TestWorkResolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()
        self.resolver = WorkResolver()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch("src.attention.providers.pubmed.PubMedProvider.resolve_pmid")
    def test_resolve_by_pmid_success(self, mock_resolve_pmid):
        mock_resolve_pmid.return_value = ResolvedWork(
            title="Ranibizumab in Retinopathy",
            journal="Retina",
            publication_date=datetime.date(2023, 5, 10),
            authors=["Alice Linz"],
            pmid="12345678",
            doi="10.1000/example"
        )
        
        work = self.resolver.resolve_work(self.session, pmid="12345678")
        
        self.assertIsNotNone(work)
        self.assertEqual(work.normalized_title, "ranibizumab in retinopathy")
        
        idents = self.session.query(WorkIdentifier).filter_by(work_id=work.id).all()
        self.assertEqual(len(idents), 2)

        # Calling again should hit db cache and NOT trigger provider call
        mock_resolve_pmid.reset_mock()
        work_cached = self.resolver.resolve_work(self.session, pmid="12345678")
        self.assertEqual(work_cached.id, work.id)
        mock_resolve_pmid.assert_not_called()

    @patch("src.attention.providers.pubmed.PubMedProvider.resolve_pmid")
    @patch("src.attention.providers.europe_pmc.EuropePMCProvider.resolve_pmid")
    def test_fallback_providers(self, mock_epmc, mock_pubmed):
        # PubMed fails, Europe PMC succeeds
        mock_pubmed.return_value = None
        mock_epmc.return_value = ResolvedWork(
            title="Ranibizumab EPMC",
            journal="Euro Retina",
            publication_date=datetime.date(2024, 1, 1),
            authors=["Jane Smith"],
            pmid="12345678"
        )
        
        work = self.resolver.resolve_work(self.session, pmid="12345678")
        self.assertIsNotNone(work)
        self.assertEqual(work.normalized_title, "ranibizumab epmc")

    def test_conflict_throws_409(self):
        # Create work A with PMID 12345678
        work_a = ResearchWork(id="wrk_a", normalized_title="title a")
        self.session.add(work_a)
        self.session.add(WorkIdentifier(work_id="wrk_a", scheme="pmid", normalized_value="12345678", display_value="12345678"))
        
        # Create work B with DOI 10.1000/conflict
        work_b = ResearchWork(id="wrk_b", normalized_title="title b")
        self.session.add(work_b)
        self.session.add(WorkIdentifier(work_id="wrk_b", scheme="doi", normalized_value="10.1000/conflict", display_value="10.1000/conflict"))
        self.session.commit()

        # Mock PubMed to return both PMID 12345678 AND DOI 10.1000/conflict (which conflicts!)
        # We query for an uncached pmid "99999999"
        with patch("src.attention.providers.pubmed.PubMedProvider.resolve_pmid") as mock_resolve:
            mock_resolve.return_value = ResolvedWork(
                title="Conflicting Work",
                pmid="12345678",
                doi="10.1000/conflict"
            )
            
            with self.assertRaises(HTTPException) as ctx:
                self.resolver.resolve_work(self.session, pmid="99999999")
            self.assertEqual(ctx.exception.status_code, 409)

if __name__ == "__main__":
    unittest.main()
