import time
import datetime
from sqlalchemy.orm import Session

from src.attention.database import SessionLocal
from src.attention.models import AttentionJob, ResearchWork, SourceRefresh
from src.attention.connectors.registry import ConnectorRegistry
from src.attention.services import save_evidence
from src.config import (

    RESEARCH_ATTENTION_REALTIME_REFRESH_INTERVAL,
    RESEARCH_ATTENTION_DAILY_REFRESH_INTERVAL,
    RESEARCH_ATTENTION_QUARTERLY_REFRESH_INTERVAL,
    RESEARCH_ATTENTION_LEGACY_REFRESH_INTERVAL,
    RESEARCH_ATTENTION_WEEKLY_REFRESH_INTERVAL
)

def get_source_refresh_interval(source: str) -> int:
    """Returns the update frequency interval in seconds based on Table 1."""
    realtime_sources = {"twitter", "news", "scopus", "wikipedia", "web_of_science", "crossref_event"}
    legacy_sources = {"sina_weibo", "citeulike", "pinterest", "linkedin"}
    
    if source in realtime_sources:
        return RESEARCH_ATTENTION_REALTIME_REFRESH_INTERVAL
    elif source == "open_syllabus":
        return RESEARCH_ATTENTION_QUARTERLY_REFRESH_INTERVAL
    elif source in legacy_sources:
        return RESEARCH_ATTENTION_LEGACY_REFRESH_INTERVAL
    else:
        return RESEARCH_ATTENTION_DAILY_REFRESH_INTERVAL

def process_one_job() -> bool:
    """
    Fetches the next queued job, locks it, processes connectors, and saves evidence.
    Returns True if a job was processed, False if queue is empty.
    """
    db = SessionLocal()
    try:
        # Fetch next job ready to run
        job = db.query(AttentionJob).filter(
            AttentionJob.state == "queued",
            AttentionJob.scheduled_at <= datetime.datetime.utcnow()
        ).order_by(AttentionJob.scheduled_at.asc()).first()
        
        if not job:
            return False

        # Lock the job in a transaction
        job.state = "running"
        job.locked_at = datetime.datetime.utcnow()
        db.commit()

        work = db.query(ResearchWork).filter_by(id=job.work_id).first()
        if not work:
            job.state = "failed"
            job.error_details = "Research work record missing."
            db.commit()
            return True

        # Process registered connectors
        registry = ConnectorRegistry()
        for source in registry.get_all_sources():
            if not registry.is_enabled(source):
                continue
            
            refresh = db.query(SourceRefresh).filter_by(work_id=work.id, source=source).first()
            if not refresh:
                refresh = SourceRefresh(work_id=work.id, source=source)
                db.add(refresh)
            
            refresh.state = "running"
            refresh.started_at = datetime.datetime.utcnow()
            db.commit()

            connector = registry.get_connector(source)
            try:
                res = connector.collect(work)
                if res.state == "ready":
                    refresh.state = "ready"
                    refresh.completed_at = datetime.datetime.utcnow()
                    refresh.item_count = len(res.evidence)
                    interval_sec = get_source_refresh_interval(source)
                    refresh.next_refresh_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=interval_sec)
                    refresh.error_code = None
                    refresh.error_message = None
                    
                    # Save retrieved evidence in database
                    save_evidence(db, work.id, res.evidence)
                else:
                    refresh.state = res.state
                    refresh.error_code = res.error_code
                    refresh.error_message = res.error_message
                    refresh.completed_at = datetime.datetime.utcnow()
            except Exception as e:
                refresh.state = "failed"
                refresh.error_code = "UNEXPECTED_CONNECTOR_ERROR"
                refresh.error_message = str(e)
                refresh.completed_at = datetime.datetime.utcnow()
            
            db.commit()


        # Mark job complete
        job.state = "completed"
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        # In case of database/transaction error, mark job failed if possible
        try:
            if 'job' in locals() and job:
                job.state = "failed"
                job.error_details = str(e)
                db.commit()
        except Exception:
            pass
        return False
    finally:
        db.close()

def run_worker_loop():
    """Main worker daemon polling loop."""
    print("[*] Starting Research Attention Job Worker loop...")
    while True:
        try:
            processed = process_one_job()
            if not processed:
                time.sleep(2)
        except KeyboardInterrupt:
            print("[*] Stopping worker...")
            break
        except Exception as e:
            print(f"[!] Worker encountered error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    run_worker_loop()
