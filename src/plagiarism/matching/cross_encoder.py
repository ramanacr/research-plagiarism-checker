"""
Optional cross-encoder candidate reranker for high-precision semantic re-scoring.
"""

from typing import List, Optional, Tuple
from src.plagiarism.documents.models import Passage
from src.plagiarism.retrieval.fusion import CandidateHit
from src.plagiarism.config.settings import RerankerSettings


class CrossEncoderReranker:
    """
    Reranks top candidate hits using a cross-encoder model.
    Only executed on the final filtered candidate set when enabled.
    """

    def __init__(self, settings: Optional[RerankerSettings] = None):
        self.settings = settings or RerankerSettings()
        self.enabled = self.settings.enabled
        self.model_name = self.settings.model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.top_k = self.settings.top_k
        self._model = None

    @property
    def model(self):
        """Lazy loads cross-encoder model."""
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query_passage: Passage,
        candidate_hits: List[CandidateHit],
        source_passages_map: Optional[dict] = None,
        top_k: Optional[int] = None,
    ) -> List[CandidateHit]:
        """
        Scores (query, source) text pairs with the cross-encoder and sorts candidates.
        """
        if not self.enabled or not candidate_hits:
            return candidate_hits

        k = top_k or self.top_k
        pairs = []
        valid_hits = []

        q_text = query_passage.normalized_text

        for hit in candidate_hits:
            s_text = ""
            if source_passages_map and hit.source_passage_id in source_passages_map:
                sp = source_passages_map[hit.source_passage_id]
                s_text = sp.normalized_text if hasattr(sp, "normalized_text") else str(sp)
            else:
                s_text = hit.metadata.get("text", "")

            if s_text:
                pairs.append((q_text, s_text))
                valid_hits.append(hit)

        if not pairs:
            return candidate_hits

        try:
            scores = self.model.predict(pairs)
            for hit, score in zip(valid_hits, scores):
                hit.cross_encoder_score = round(float(score), 4)
                # Boost fusion score with cross-encoder prediction
                hit.fusion_score = round(hit.fusion_score + float(score), 4)

            candidate_hits.sort(key=lambda h: (h.cross_encoder_score or 0.0, h.fusion_score), reverse=True)
        except Exception:
            # Fallback gracefully if model inference fails
            pass

        return candidate_hits[:k]
