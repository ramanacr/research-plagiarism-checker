"""
Provider registry and multi-provider query coordinator with failure isolation.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Set
import re

from src.plagiarism.providers.base import (
    ScholarlyContentProvider,
    SourceRecord,
    ProviderHealth,
)
from src.plagiarism.providers.pubmed import PubMedProvider
from src.plagiarism.providers.europe_pmc import EuropePMCProvider


class ProviderRegistry:
    """
    Registry for scholarly content providers.
    Provides registration, health checking, deduplicated search, and failure isolation.
    """

    def __init__(self):
        self._providers: Dict[str, ScholarlyContentProvider] = {}

    def register(self, provider: ScholarlyContentProvider) -> None:
        """Registers a provider instance."""
        self._providers[provider.name] = provider

    def unregister(self, name: str) -> Optional[ScholarlyContentProvider]:
        """Removes a provider by name."""
        return self._providers.pop(name, None)

    def get(self, name: str) -> Optional[ScholarlyContentProvider]:
        """Gets a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """Returns list of registered provider names."""
        return list(self._providers.keys())

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        """Runs health checks on all registered providers concurrently."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception as e:
                results[name] = ProviderHealth(
                    is_healthy=False,
                    provider_name=name,
                    error_message=str(e),
                )
        return results

    async def search_all(
        self,
        query: str,
        limit_per_provider: int = 10,
        provider_names: Optional[List[str]] = None,
    ) -> Tuple[List[SourceRecord], List[str]]:
        """
        Queries all target providers concurrently with failure isolation.
        Returns:
            (deduplicated_records, warnings)
        """
        if not query.strip():
            return [], []

        target_names = provider_names if provider_names is not None else list(self._providers.keys())
        active_providers = [self._providers[name] for name in target_names if name in self._providers]

        if not active_providers:
            return [], [f"No active providers available from requested list: {provider_names}"]

        async def _query_provider(provider: ScholarlyContentProvider) -> Tuple[str, List[SourceRecord], Optional[str]]:
            try:
                records = await provider.search(query, limit=limit_per_provider)
                return provider.name, records, None
            except Exception as e:
                return provider.name, [], f"Provider '{provider.name}' search error: {str(e)}"

        tasks = [_query_provider(p) for p in active_providers]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        all_records: List[SourceRecord] = []
        warnings: List[str] = []

        for p_name, records, err in results:
            if err:
                warnings.append(err)
            else:
                all_records.extend(records)

        deduplicated = self.deduplicate_records(all_records)
        return deduplicated, warnings

    def search_all_sync(
        self,
        query: str,
        limit_per_provider: int = 10,
        provider_names: Optional[List[str]] = None,
    ) -> Tuple[List[SourceRecord], List[str]]:
        """Synchronous wrapper for search_all."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.search_all(query, limit_per_provider, provider_names)).result()
            return loop.run_until_complete(self.search_all(query, limit_per_provider, provider_names))
        except RuntimeError:
            return asyncio.run(self.search_all(query, limit_per_provider, provider_names))

    @staticmethod
    def deduplicate_records(records: List[SourceRecord]) -> List[SourceRecord]:
        """
        Deduplicates records based on:
        1. PMID
        2. DOI
        3. PMCID
        4. Normalized Title
        """
        seen_pmids: Set[str] = set()
        seen_dois: Set[str] = set()
        seen_pmcids: Set[str] = set()
        seen_titles: Set[str] = set()

        deduped: List[SourceRecord] = []

        for rec in records:
            # Check PMID
            if rec.pmid:
                if rec.pmid in seen_pmids:
                    continue
                seen_pmids.add(rec.pmid)

            # Check DOI
            if rec.doi:
                norm_doi = rec.doi.lower().strip()
                if norm_doi in seen_dois:
                    continue
                seen_dois.add(norm_doi)

            # Check PMCID
            if rec.pmcid:
                norm_pmcid = rec.pmcid.upper().strip()
                if norm_pmcid in seen_pmcids:
                    continue
                seen_pmcids.add(norm_pmcid)

            # Check Title
            if rec.title:
                norm_title = re.sub(r"[^a-zA-Z0-9]", "", rec.title).lower()
                if norm_title and norm_title in seen_titles:
                    continue
                if norm_title:
                    seen_titles.add(norm_title)

            deduped.append(rec)

        return deduped


def create_default_registry() -> ProviderRegistry:
    """Instantiates a provider registry loaded with default providers."""
    registry = ProviderRegistry()
    registry.register(PubMedProvider())
    registry.register(EuropePMCProvider())
    return registry
