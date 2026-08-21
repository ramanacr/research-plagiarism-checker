"""
Services package for plagiarism check orchestration and document ingestion.
"""

from src.plagiarism.services.plagiarism_service import PlagiarismService
from src.plagiarism.services.ingestion_service import IngestionService

__all__ = [
    "PlagiarismService",
    "IngestionService",
]
