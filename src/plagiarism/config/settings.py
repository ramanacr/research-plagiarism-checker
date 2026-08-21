"""
Configuration settings and models for Plagiarism Checker engine.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class SegmentationSettings:
    target_tokens: int = 150
    overlap_tokens: int = 25
    min_passage_tokens: int = 20
    version: str = "v1"


@dataclass(frozen=True)
class LexicalSettings:
    shingle_size: int = 5
    minhash_num_perm: int = 128
    lsh_threshold: float = 0.5
    top_k: int = 30
    containment_threshold: float = 0.20
    version: str = "v1"


@dataclass(frozen=True)
class SemanticSettings:
    model_name: str = "sentence-transformers/all-mpnet-base-v2"
    model_revision: str = "main"
    batch_size: int = 32
    top_k: int = 30
    similarity_threshold: float = 0.75
    index_backend: str = "faiss"
    version: str = "v1"


@dataclass(frozen=True)
class RerankerSettings:
    enabled: bool = False
    model_name: Optional[str] = None
    top_k: int = 15


@dataclass(frozen=True)
class ScoringThresholds:
    threshold_version: str = "v1"
    exact_copy_containment: float = 0.85
    exact_copy_overlap_ratio: float = 0.80
    near_exact_containment: float = 0.65
    near_exact_edit_similarity: float = 0.70
    likely_paraphrase_semantic: float = 0.82
    likely_paraphrase_token_overlap: float = 0.20
    possible_paraphrase_semantic: float = 0.75
    common_phrase_max_tokens: int = 10
    common_phrase_corpus_freq: int = 5
    min_suspicious_tokens: int = 12
    citation_proximity_tokens: int = 50


@dataclass(frozen=True)
class RightsSettings:
    fail_closed: bool = True
    allow_unspecified_licenses: bool = False
    default_retention_days: int = 365


@dataclass(frozen=True)
class FeatureFlags:
    persistent_lexical_index: bool = True
    dense_ann_index: bool = True
    hybrid_retrieval: bool = True
    citation_aware_scoring: bool = True
    boilerplate_suppression: bool = True
    cross_encoder: bool = False


@dataclass
class EngineConfig:
    engine_version: str = "2.0.0"
    storage_dir: str = field(
        default_factory=lambda: os.environ.get(
            "PLAGIARISM_STORAGE_DIR",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scratch", "plagiarism_indexes")
        )
    )
    segmentation: SegmentationSettings = field(default_factory=SegmentationSettings)
    lexical: LexicalSettings = field(default_factory=LexicalSettings)
    semantic: SemanticSettings = field(default_factory=SemanticSettings)
    reranker: RerankerSettings = field(default_factory=RerankerSettings)
    scoring: ScoringThresholds = field(default_factory=ScoringThresholds)
    rights: RightsSettings = field(default_factory=RightsSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    metrics_enabled: bool = True
    log_level: str = "INFO"


_global_config: Optional[EngineConfig] = None


def get_default_config() -> EngineConfig:
    global _global_config
    if _global_config is None:
        _global_config = EngineConfig()
    return _global_config


def set_global_config(config: EngineConfig) -> None:
    global _global_config
    _global_config = config
