"""
Predefined copyright and licensing policy profiles for content rights management.
"""

from typing import Dict
from src.plagiarism.rights.models import RightsRecord

STANDARD_POLICIES: Dict[str, RightsRecord] = {
    "cc_by": RightsRecord(
        rights_id="cc_by",
        provider="standard",
        license_name="Creative Commons Attribution (CC-BY)",
        license_uri="https://creativecommons.org/licenses/by/4.0/",
        commercial_use_allowed=True,
        text_mining_allowed=True,
        raw_storage_allowed=True,
        derived_index_allowed=True,
        snippet_display_allowed=True,
        retention_days=3650,
    ),
    "cc0": RightsRecord(
        rights_id="cc0",
        provider="standard",
        license_name="Public Domain (CC0)",
        license_uri="https://creativecommons.org/publicdomain/zero/1.0/",
        commercial_use_allowed=True,
        text_mining_allowed=True,
        raw_storage_allowed=True,
        derived_index_allowed=True,
        snippet_display_allowed=True,
        retention_days=3650,
    ),
    "abstract_fair_use": RightsRecord(
        rights_id="abstract_fair_use",
        provider="standard",
        license_name="Scholarly Abstract Fair Use",
        commercial_use_allowed=False,
        text_mining_allowed=True,
        raw_storage_allowed=False,
        derived_index_allowed=True,
        snippet_display_allowed=True,
        retention_days=365,
    ),
    "all_rights_reserved": RightsRecord(
        rights_id="all_rights_reserved",
        provider="standard",
        license_name="All Rights Reserved (Commercial)",
        commercial_use_allowed=False,
        text_mining_allowed=False,
        raw_storage_allowed=False,
        derived_index_allowed=False,
        snippet_display_allowed=False,
        retention_days=0,
    ),
}
