"""
Scientific boilerplate and common academic phrase detection and down-weighting.
"""

import re
from typing import Set, Dict, List, Optional, Tuple
from src.plagiarism.documents.normalize import normalize_for_lexical


COMMON_SCIENTIFIC_BOILERPLATES: Set[str] = {
    "all experiments were performed in triplicate",
    "data are expressed as mean standard deviation",
    "data are presented as mean standard deviation",
    "statistical analysis was performed using",
    "differences were considered statistically significant at",
    "statistically significant difference was defined as",
    "p value less than 0 05 was considered statistically significant",
    "p 0 05 was considered statistically significant",
    "written informed consent was obtained from all participants",
    "the study protocol was approved by the institutional review board",
    "this study was approved by the ethics committee",
    "all procedures performed in studies involving human participants",
    "in accordance with the ethical standards of the institutional",
    "the authors declare that they have no competing interests",
    "the datasets generated during and or analyzed during the current study",
    "are available from the corresponding author on reasonable request",
    "conceived and designed the experiments performed the experiments",
    "analyzed the data contributed reagents materials analysis tools wrote the paper",
    "all authors read and approved the final manuscript",
}


class BoilerplateDetector:
    """
    Detects generic scientific method boilerplate and high-frequency academic phrases.
    """

    def __init__(self, corpus_phrase_frequencies: Optional[Dict[str, int]] = None):
        self.corpus_phrase_frequencies = corpus_phrase_frequencies or {}
        # Pre-normalized boilerplates
        self.boilerplate_patterns = [
            re.compile(re.escape(bp), re.IGNORECASE) for bp in COMMON_SCIENTIFIC_BOILERPLATES
        ]

    def is_boilerplate(self, phrase: str) -> bool:
        """Checks if a phrase matches known standard scientific boilerplate."""
        norm = normalize_for_lexical(phrase)
        if not norm:
            return False

        # Direct dictionary check
        if norm in COMMON_SCIENTIFIC_BOILERPLATES:
            return True

        # Subphrase check
        for pat in self.boilerplate_patterns:
            if pat.search(norm):
                return True

        # Corpus frequency check (if phrase appears in > 10 distinct corpus documents)
        freq = self.corpus_phrase_frequencies.get(norm, 0)
        if freq >= 5:
            return True

        return False

    def compute_boilerplate_score(self, phrase: str) -> float:
        """
        Calculates a boilerplate score in [0.0, 1.0].
        1.0 means pure generic boilerplate.
        """
        if self.is_boilerplate(phrase):
            return 1.0

        norm = normalize_for_lexical(phrase)
        words = norm.split()
        if len(words) < 4:
            # Short phrases are common
            return 0.5

        freq = self.corpus_phrase_frequencies.get(norm, 0)
        if freq > 0:
            return min(1.0, 0.2 * freq)

        return 0.0

    def filter_common_phrases(self, phrases: List[str]) -> Tuple[List[str], List[str]]:
        """
        Splits phrases into (substantive_phrases, boilerplate_phrases).
        """
        substantive = []
        boilerplate = []
        for p in phrases:
            if self.is_boilerplate(p):
                boilerplate.append(p)
            else:
                substantive.append(p)
        return substantive, boilerplate
