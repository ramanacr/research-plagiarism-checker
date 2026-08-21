"""
Dense vector index with FAISS / NumPy storage and metadata mapping.
"""

import os
import pickle
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class VectorIndex:
    """
    Persistent dense vector index supporting similarity search and passage metadata mapping.
    Uses FAISS if available, with a fast vectorized NumPy fallback.
    """

    def __init__(
        self,
        dimension: int = 768,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        index_version: str = "v1",
    ):
        self.dimension = dimension
        self.model_name = model_name
        self.index_version = index_version

        self.passage_ids: List[str] = []
        self.passage_doc_map: Dict[str, str] = {}
        self.passage_metadata: Dict[str, Dict[str, Any]] = {}
        self.vectors: np.ndarray = np.empty((0, dimension), dtype=np.float32)

        self._use_faiss = False
        self._faiss_index = None
        self._init_faiss()

    def _init_faiss(self) -> None:
        """Attempts to initialize FAISS index."""
        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self.dimension)
            self._use_faiss = True
        except ImportError:
            self._use_faiss = False
            self._faiss_index = None

    def insert(
        self,
        passage_id: str,
        vector: np.ndarray,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Inserts a single passage vector."""
        vec = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        # Normalize vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        if passage_id in self.passage_ids:
            self.delete_passage(passage_id)

        self.passage_ids.append(passage_id)
        self.passage_doc_map[passage_id] = document_id
        self.passage_metadata[passage_id] = metadata or {}
        self.vectors = np.vstack([self.vectors, vec]) if len(self.vectors) > 0 else vec

        if self._use_faiss and self._faiss_index is not None:
            self._faiss_index.add(vec)

    def insert_batch(
        self,
        passage_ids: List[str],
        vectors: np.ndarray,
        document_ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Inserts a batch of passage vectors."""
        if not passage_ids or len(vectors) == 0:
            return

        vecs = np.asarray(vectors, dtype=np.float32)
        # Normalize rows
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vecs = vecs / norms

        meta_list = metadatas or [{} for _ in passage_ids]

        for i, pid in enumerate(passage_ids):
            if pid in self.passage_ids:
                self.delete_passage(pid)

        self.passage_ids.extend(passage_ids)
        for i, pid in enumerate(passage_ids):
            self.passage_doc_map[pid] = document_ids[i]
            self.passage_metadata[pid] = meta_list[i]

        self.vectors = np.vstack([self.vectors, vecs]) if len(self.vectors) > 0 else vecs

        if self._use_faiss and self._faiss_index is not None:
            self._rebuild_faiss()

    def delete_passage(self, passage_id: str) -> bool:
        """Removes a passage from the vector index."""
        if passage_id not in self.passage_ids:
            return False

        idx = self.passage_ids.index(passage_id)
        self.passage_ids.pop(idx)
        self.passage_doc_map.pop(passage_id, None)
        self.passage_metadata.pop(passage_id, None)

        if len(self.vectors) > 0:
            self.vectors = np.delete(self.vectors, idx, axis=0)

        if self._use_faiss:
            self._rebuild_faiss()

        return True

    def delete_document(self, document_id: str) -> int:
        """Removes all passages belonging to document_id."""
        to_delete = [
            pid for pid, doc_id in self.passage_doc_map.items() if doc_id == document_id
        ]
        deleted_count = 0
        for pid in to_delete:
            if self.delete_passage(pid):
                deleted_count += 1
        return deleted_count

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 30,
        threshold: float = 0.50,
    ) -> List[Dict[str, Any]]:
        """
        Searches index for passages semantically close to query_vector.
        Returns list of result dicts sorted by similarity descending.
        """
        if len(self.passage_ids) == 0 or len(self.vectors) == 0:
            return []

        q_vec = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        k = min(top_k, len(self.passage_ids))

        if self._use_faiss and self._faiss_index is not None:
            distances, indices = self._faiss_index.search(q_vec, k)
            scores = distances[0]
            idxs = indices[0]
        else:
            # Vectorized dot product cosine similarity
            sims = np.dot(self.vectors, q_vec.T).flatten()
            idxs = np.argsort(sims)[::-1][:k]
            scores = sims[idxs]

        results = []
        for rank, idx in enumerate(idxs):
            if idx < 0 or idx >= len(self.passage_ids):
                continue
            score = float(scores[rank])
            if score >= threshold:
                pid = self.passage_ids[idx]
                results.append({
                    "passage_id": pid,
                    "document_id": self.passage_doc_map.get(pid, ""),
                    "similarity": round(score, 4),
                    "metadata": self.passage_metadata.get(pid, {}),
                })

        return results

    def _rebuild_faiss(self) -> None:
        """Reconstructs the FAISS index from stored vectors."""
        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self.dimension)
            if len(self.vectors) > 0:
                self._faiss_index.add(self.vectors)
        except Exception:
            self._use_faiss = False
            self._faiss_index = None

    def save(self, filepath: str) -> None:
        """Persists vector index and metadata to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        payload = {
            "index_version": self.index_version,
            "dimension": self.dimension,
            "model_name": self.model_name,
            "passage_ids": self.passage_ids,
            "passage_doc_map": self.passage_doc_map,
            "passage_metadata": self.passage_metadata,
            "vectors": self.vectors,
        }
        with open(filepath, "wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load(cls, filepath: str) -> "VectorIndex":
        """Loads vector index and metadata from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Vector index file not found: {filepath}")

        with open(filepath, "rb") as f:
            payload = pickle.load(f)

        idx = cls(
            dimension=payload.get("dimension", 768),
            model_name=payload.get("model_name", "sentence-transformers/all-mpnet-base-v2"),
            index_version=payload.get("index_version", "v1"),
        )
        idx.passage_ids = payload.get("passage_ids", [])
        idx.passage_doc_map = payload.get("passage_doc_map", {})
        idx.passage_metadata = payload.get("passage_metadata", {})
        idx.vectors = payload.get("vectors", np.empty((0, idx.dimension), dtype=np.float32))

        if idx._use_faiss and len(idx.vectors) > 0:
            idx._rebuild_faiss()

        return idx

    @property
    def total_vectors(self) -> int:
        return len(self.passage_ids)
