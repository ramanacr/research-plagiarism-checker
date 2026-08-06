import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier, SourceRefresh, AttentionEvidence
from src.attention.services import get_work_details
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestRefreshState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        self.session.query(SourceRefresh).delete()
        self.session.query(AttentionEvidence).delete()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()

        # Create work
        self.work = ResearchWork(
            id="wrk_test123",
            normalized_title="test title",
            authors=[]
        )
        self.session.add(self.work)
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_get_work_details_refresh_states(self):
        # 1. No refresh records -> ready/queued (since Wikipedia is enabled but hasn't run)
        details = get_work_details(self.session, "wrk_test123")
        self.assertEqual(details["coverage"]["refresh_state"], "ready")
        
        # 2. Add running refresh for Wikipedia
        refresh = SourceRefresh(
            work_id="wrk_test123",
            source="wikipedia",
            state="running",
            started_at=datetime.datetime.utcnow()
        )
        self.session.add(refresh)
        self.session.commit()
        
        details2 = get_work_details(self.session, "wrk_test123")
        self.assertEqual(details2["coverage"]["refresh_state"], "running")

        # 3. Fail the refresh
        refresh.state = "failed"
        refresh.error_message = "API timeout"
        self.session.commit()
        
        details3 = get_work_details(self.session, "wrk_test123")
        self.assertEqual(details3["coverage"]["refresh_state"], "failed")
        self.assertEqual(details3["coverage"]["sources"][0]["reason"], "API timeout")

if __name__ == "__main__":
    unittest.main()
