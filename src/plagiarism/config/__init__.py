"""Configuration package for Plagiarism Checker."""
from src.plagiarism.config.settings import (
    EngineConfig,
    SegmentationSettings,
    LexicalSettings,
    SemanticSettings,
    RerankerSettings,
    ScoringThresholds,
    RightsSettings,
    FeatureFlags,
    get_default_config,
    set_global_config,
)

__all__ = [
    "EngineConfig",
    "SegmentationSettings",
    "LexicalSettings",
    "SemanticSettings",
    "RerankerSettings",
    "ScoringThresholds",
    "RightsSettings",
    "FeatureFlags",
    "get_default_config",
    "set_global_config",
]
