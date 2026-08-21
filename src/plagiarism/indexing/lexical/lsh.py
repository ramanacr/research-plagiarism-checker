"""
Persistent lexical index with MinHash LSH and inverted shingle index.
"""

import os
import json
import pickle
from typing import Dict, List, Set, Tuple, Optional, Any
from datasketch import MinHash, MinHashLSH

from src.plagiarism.indexing.lexical.minhash import MinHashGenerator
from src.plagiarism.indexing.lexical.shingles import (
    generate_shingle_strings,
    compute_shingle_containment,
    compute_shingle_jaccard,
)


class PersistentLexicalIndex:
    """
    Passage-level persistent lexical index combining MinHash LSH and an inverted shingle index.
    Supports persistent serialization, incremental update, and containment retrieval.
    """

    def __init__(
        self,
        shingle_size: int = 5,
        num_perm: int = 128,
        lsh_threshold: float = 0.4,
        index_version: str = "v1",
    ):
        self.shingle_size = shingle_size
        self.num_perm = num_perm
        self.lsh_threshold = lsh_threshold
        self.index_version = index_version
        self.minhash_gen = MinHashGenerator(num_perm=num_perm)

        # In-memory index structures
        self.lsh = MinHashLSH(threshold=self.lsh_threshold, num_perm=self.num_perm)
        self.passage_signatures: Dict[str, MinHash] = {}
        self.passage_shingles: Dict[str, Set[str]] = {}
        self.passage_doc_map: Dict[str, str] = {}
        self.passage_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Inverted index: shingle_str -> Set[passage_id]
        self.inverted_index: Dict[str, Set[str]] = {}

    def insert_passage(
        self,
        passage_id: str,
        text_or_shingles: Any,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Inserts a passage into the persistent lexical index.
        """
        # If already exists, remove first to update cleanly
        if passage_id in self.passage_signatures:
            self.delete_passage(passage_id)

        if isinstance(text_or_shingles, set):
            shingles = text_or_shingles
        else:
            shingles = generate_shingle_strings(str(text_or_shingles), k=self.shingle_size)

        if not shingles:
            return

        m = self.minhash_gen.compute_minhash(shingles)
        self.lsh.insert(passage_id, m)
        self.passage_signatures[passage_id] = m
        self.passage_shingles[passage_id] = shingles
        self.passage_doc_map[passage_id] = document_id
        self.passage_metadata[passage_id] = metadata or {}

        # Update inverted index
        for s in shingles:
            if s not in self.inverted_index:
                self.inverted_index[s] = set()
            self.inverted_index[s].add(passage_id)

    def delete_passage(self, passage_id: str) -> bool:
        """Removes a single passage from the index."""
        if passage_id not in self.passage_signatures:
            return False

        m = self.passage_signatures.pop(passage_id)
        shingles = self.passage_shingles.pop(passage_id, set())
        self.passage_doc_map.pop(passage_id, None)
        self.passage_metadata.pop(passage_id, None)

        try:
            self.lsh.remove(passage_id)
        except Exception:
            pass

        # Update inverted index
        for s in shingles:
            if s in self.inverted_index:
                self.inverted_index[s].discard(passage_id)
                if not self.inverted_index[s]:
                    del self.inverted_index[s]

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

    def query_containment(
        self,
        query_shingles: Set[str],
        top_k: int = 30,
        threshold: float = 0.10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidate passages with high shingle containment.
        Uses inverted index for rapid candidate pruning followed by exact containment calculation.
        """
        if not query_shingles:
            return []

        # Candidate accumulation from inverted index
        candidate_counts: Dict[str, int] = {}
        for s in query_shingles:
            matching_pids = self.inverted_index.get(s, set())
            for pid in matching_pids:
                candidate_counts[pid] = candidate_counts.get(pid, 0) + 1

        results = []
        for pid, count in candidate_counts.items():
            src_shingles = self.passage_shingles.get(pid, set())
            if not src_shingles:
                continue

            containment = count / len(query_shingles)
            jaccard = count / len(query_shingles.union(src_shingles))

            if containment >= threshold or jaccard >= threshold:
                results.append({
                    "passage_id": pid,
                    "document_id": self.passage_doc_map.get(pid, ""),
                    "containment": round(containment, 4),
                    "jaccard": round(jaccard, 4),
                    "matched_shingles": count,
                    "metadata": self.passage_metadata.get(pid, {}),
                })

        # Also query LSH for any fuzzy MinHash candidates not covered by inverted index
        query_m = self.minhash_gen.compute_minhash(query_shingles)
        lsh_matches = self.lsh.query(query_m)
        for pid in lsh_matches:
            if not any(r["passage_id"] == pid for r in results):
                src_shingles = self.passage_shingles.get(pid, set())
                c = compute_shingle_containment(query_shingles, src_shingles)
                j = compute_shingle_jaccard(query_shingles, src_shingles)
                if c >= threshold or j >= threshold:
                    results.append({
                        "passage_id": pid,
                        "document_id": self.passage_doc_map.get(pid, ""),
                        "containment": round(c, 4),
                        "jaccard": round(j, 4),
                        "matched_shingles": len(query_shingles.intersection(src_shingles)),
                        "metadata": self.passage_metadata.get(pid, {}),
                    })

        results.sort(key=lambda x: x["containment"], reverse=True)
        return results[:top_k]

    def save(self, filepath: str) -> None:
        """Saves persistent index state to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        payload = {
            "index_version": self.index_version,
            "shingle_size": self.shingle_size,
            "num_perm": self.num_perm,
            "lsh_threshold": self.lsh_threshold,
            "passage_signatures": {
                pid: self.minhash_gen.serialize_minhash(m)
                for pid, m in self.passage_signatures.items()
            },
            "passage_shingles": self.passage_shingles,
            "passage_doc_map": self.passage_doc_map,
            "passage_metadata": self.passage_metadata,
        }
        with open(filepath, "wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load(cls, filepath: str) -> "PersistentLexicalIndex":
        """Loads persistent index state from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Lexical index file not found: {filepath}")

        with open(filepath, "rb") as f:
            payload = pickle.load(f)

        idx = cls(
            shingle_size=payload.get("shingle_size", 5),
            num_perm=payload.get("num_perm", 128),
            lsh_threshold=payload.get("lsh_threshold", 0.4),
            index_version=payload.get("index_version", "v1"),
        )

        raw_sigs = payload.get("passage_signatures", {})
        idx.passage_shingles = payload.get("passage_shingles", {})
        idx.passage_doc_map = payload.get("passage_doc_map", {})
        idx.passage_metadata = payload.get("passage_metadata", {})

        for pid, raw_m in raw_sigs.items():
            m = idx.minhash_gen.deserialize_minhash(raw_m)
            idx.passage_signatures[pid] = m
            idx.lsh.insert(pid, m)

        # Reconstruct inverted index
        for pid, shingles in idx.passage_shingles.items():
            for s in shingles:
                if s not in idx.inverted_index:
                    idx.inverted_index[s] = set()
                idx.inverted_index[s].add(pid)

        return idx

    @property
    def total_passages(self) -> int:
        return len(self.passage_signatures)

    @property
    def total_documents(self) -> int:
        return len(set(self.passage_doc_map.values()))
