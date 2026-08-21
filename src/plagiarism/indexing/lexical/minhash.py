"""
MinHash signature generator and serialization utilities.
"""

from typing import Set, Optional, List, Tuple
from datasketch import MinHash
import numpy as np


class MinHashGenerator:
    """
    Generates and serializes MinHash signatures for text shingles.
    """

    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm

    def compute_minhash(self, shingle_strings: Set[str]) -> MinHash:
        """
        Computes a MinHash signature from a set of shingle strings.
        """
        m = MinHash(num_perm=self.num_perm)
        for s in shingle_strings:
            m.update(s.encode("utf-8"))
        return m

    def serialize_minhash(self, m: MinHash) -> bytes:
        """Serializes MinHash hashvalues array to bytes."""
        return np.ascontiguousarray(m.hashvalues, dtype=np.uint32).tobytes()

    def deserialize_minhash(self, raw_bytes: bytes, scheme: str = "affine32") -> MinHash:
        """Deserializes bytes into a MinHash object."""
        hashvalues = np.frombuffer(raw_bytes, dtype=np.uint32)
        try:
            return MinHash(num_perm=len(hashvalues), hashvalues=hashvalues, scheme=scheme)
        except TypeError:
            # Older datasketch without scheme argument
            return MinHash(num_perm=len(hashvalues), hashvalues=hashvalues)

    @staticmethod
    def estimate_jaccard(m1: MinHash, m2: MinHash) -> float:
        """Estimates Jaccard similarity between two MinHash signatures."""
        return m1.jaccard(m2)
