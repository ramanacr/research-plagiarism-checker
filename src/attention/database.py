import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import RESEARCH_ATTENTION_DATABASE_URL, RESEARCH_ATTENTION_ENABLED

if RESEARCH_ATTENTION_ENABLED and not RESEARCH_ATTENTION_DATABASE_URL:
    raise ValueError("RESEARCH_ATTENTION_DATABASE_URL must be configured when Research Attention is enabled.")

engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
