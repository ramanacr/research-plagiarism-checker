from abc import ABC, abstractmethod
from typing import Optional
import re
from src.attention.schemas import ResolvedWork

class IdentityProvider(ABC):
    @abstractmethod
    def resolve_pmid(self, pmid: str) -> Optional[ResolvedWork]:
        pass

    @abstractmethod
    def resolve_doi(self, doi: str) -> Optional[ResolvedWork]:
        pass

def normalize_pmid(value: str) -> Optional[str]:
    if not value:
        return None
    # Keep only digits
    cleaned = "".join(c for c in value if c.isdigit())
    return cleaned if cleaned else None

def normalize_doi(value: str) -> Optional[str]:
    if not value:
        return None
    # Lowercase and strip whitespace
    cleaned = value.strip().lower()
    # Remove resolver prefixes: http(s)://doi.org/, http(s)://dx.doi.org/, and doi:
    cleaned = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', cleaned)
    # Strip any trailing dots, commas, slashes
    cleaned = re.sub(r'[.,;/]$', '', cleaned)
    # Validate standard DOI prefix "10."
    if not cleaned.startswith("10.") or "/" not in cleaned:
        return None
    return cleaned
