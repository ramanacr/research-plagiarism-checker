"""
Qdrant vector database adapter interface.
"""

from typing import Dict, List, Optional, Any
import numpy as np


class QdrantVectorIndex:
    """
    Adapter for remote/local Qdrant vector search deployments.
    """

    def __init__(
        self,
        collection_name: str = "plagiarism_passages",
        host: str = "localhost",
        port: int = 6333,
        dimension: int = 768,
    ):
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.dimension = dimension
        self.client = None

    def connect(self) -> bool:
        """Attempts connection to Qdrant."""
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(host=self.host, port=self.port)
            return True
        except Exception:
            return False

    def insert(
        self,
        passage_id: str,
        vector: np.ndarray,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Inserts vector and payload into Qdrant if connected."""
        if not self.client:
            return
        payload = metadata or {}
        payload["document_id"] = document_id
        payload["passage_id"] = passage_id
        # Qdrant upsert logic
        try:
            from qdrant_client.http.models import PointStruct
            point = PointStruct(id=hash(passage_id) & 0x7FFFFFFFFFFFFFFF, vector=vector.tolist(), payload=payload)
            self.client.upsert(collection_name=self.collection_name, points=[point])
        except Exception:
            pass

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 30,
        threshold: float = 0.50,
    ) -> List[Dict[str, Any]]:
        """Queries Qdrant for nearest neighbors."""
        if not self.client:
            return []
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                limit=top_k,
                score_threshold=threshold,
            )
            return [
                {
                    "passage_id": hit.payload.get("passage_id", ""),
                    "document_id": hit.payload.get("document_id", ""),
                    "similarity": round(float(hit.score), 4),
                    "metadata": hit.payload,
                }
                for hit in results
            ]
        except Exception:
            return []
