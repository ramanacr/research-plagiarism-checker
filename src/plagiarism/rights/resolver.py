"""
Rights resolver evaluating permissions before persistence with fail-closed security.
"""

from typing import Optional, Dict
from src.plagiarism.rights.models import RightsRecord, RightsDecision
from src.plagiarism.rights.policies import STANDARD_POLICIES
from src.plagiarism.config.settings import RightsSettings


class RightsResolver:
    """
    Evaluates copyright, licenses, and rights policies before content persistence.
    Enforces ADR-012: Rights enforcement occurs before persistence.
    """

    def __init__(self, settings: Optional[RightsSettings] = None):
        self.settings = settings or RightsSettings()
        self.policies: Dict[str, RightsRecord] = dict(STANDARD_POLICIES)

    def register_policy(self, rights_record: RightsRecord) -> None:
        """Registers a custom policy."""
        self.policies[rights_record.rights_id] = rights_record

    def evaluate_rights(
        self,
        rights_id: Optional[str],
        provider: str = "",
        is_open_access: bool = False,
    ) -> RightsDecision:
        """
        Evaluates permissions for a piece of content before storage or indexing.
        """
        if is_open_access and not rights_id:
            rights_id = "cc_by"

        policy = self.policies.get(rights_id or "")

        if policy is not None:
            return RightsDecision(
                allowed_to_index=policy.derived_index_allowed,
                allowed_to_store_raw=policy.raw_storage_allowed,
                allowed_to_display_snippet=policy.snippet_display_allowed,
                reason=f"Matched policy '{policy.license_name}'",
                rights_record=policy,
            )

        # Fallback if unknown license
        if self.settings.fail_closed:
            # Default to abstract fair use if from known scholarly provider
            if provider in ["pubmed", "europe_pmc", "crossref", "openalex", "arxiv"]:
                fair_use = self.policies["abstract_fair_use"]
                return RightsDecision(
                    allowed_to_index=fair_use.derived_index_allowed,
                    allowed_to_store_raw=fair_use.raw_storage_allowed,
                    allowed_to_display_snippet=fair_use.snippet_display_allowed,
                    reason="Fail-closed fallback: Scholarly abstract fair use policy applied",
                    rights_record=fair_use,
                )
            else:
                return RightsDecision(
                    allowed_to_index=False,
                    allowed_to_store_raw=False,
                    allowed_to_display_snippet=False,
                    reason="Fail-closed: Unknown rights/license policy denied",
                    rights_record=None,
                )
        else:
            return RightsDecision(
                allowed_to_index=True,
                allowed_to_store_raw=False,
                allowed_to_display_snippet=True,
                reason="Permissive fallback (fail_closed disabled)",
                rights_record=None,
            )
