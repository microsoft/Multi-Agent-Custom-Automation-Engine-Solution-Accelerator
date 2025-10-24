"""
Azure AI Search integration for reasoning agents (no agent framework  dependency).

This module provides:
- ReasoningSearch: lightweight wrapper around Azure Cognitive Search (Azure AI Search)
- Async initialization and async search with executor offloading

Design goals:
- Fast to call from other async agent components
- Graceful degradation if configuration is incomplete
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from af.magentic_agents.models.agent_models import SearchConfig


class ReasoningSearch:
    """
    Handles Azure AI Search (Cognitive Search) queries for retrieval / RAG augmentation.
    """

    def __init__(
        self,
        search_config: Optional[SearchConfig] = None,
        *,
        max_executor_workers: int = 4,
    ) -> None:
        self.search_config = search_config
        self.search_client: Optional[SearchClient] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_executor_workers
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the search client. Safe to call multiple times.
        Returns:
            bool: True if initialized, False if config missing or failed.
        """
        if self._initialized:
            return True

        if (
            not self.search_config
            or not self.search_config.endpoint
            or not self.search_config.index_name
            or not self.search_config.api_key
        ):
            # Incomplete config => treat as disabled
            return False

        try:
            self.search_client = SearchClient(
                endpoint=self.search_config.endpoint,
                credential=AzureKeyCredential(self.search_config.api_key),
                index_name=self.search_config.index_name,
            )
            # Dedicated executor for blocking search calls
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="reasoning_search",
            )
            self._initialized = True
            return True
        except Exception:
            # Swallow initialization errors (callers can check is_available)
            self.search_client = None
            self._initialized = False
            return False

    def is_available(self) -> bool:
        """Return True if search is properly initialized and usable."""
        return self._initialized and self.search_client is not None

    async def search_documents(self, query: str, limit: int = 3) -> List[str]:
        """
        Perform a simple full‑text search and return the 'content' field of matching docs.

        Args:
            query: Natural language or keyword query.
            limit: Max number of documents.

        Returns:
            List of strings (each a document content snippet). Empty if none or unavailable.
        """
        if not self.is_available():
            return []

        limit = max(1, min(limit, 50))  # basic safety bounds

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                self._executor,
                lambda: self._run_search_sync(query=query, limit=limit),
            )
        except Exception:
            return []

    async def search_raw(self, query: str, limit: int = 3):
        """
        Raw search returning native SDK result iterator (materialized to list).
        Provided for more advanced callers needing metadata.

        Returns:
            list of raw SDK result objects (dict-like).
        """
        if not self.is_available():
            return []

        limit = max(1, min(limit, 50))

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                self._executor, lambda: self._run_search_sync(query, limit, raw=True)
            )
        except Exception:
            return []

    def _run_search_sync(self, query: str, limit: int, raw: bool = False):
        """
        Internal synchronous search (executed inside ThreadPoolExecutor).
        """
        if not self.search_client:
            return [] if not raw else []

        results_iter = self.search_client.search(
            search_text=query,
            query_type="simple",
            select=["content"],
            top=limit,
        )

        contents: List[str] = []
        raw_items: List = []
        for item in results_iter:
            try:
                if raw:
                    raw_items.append(item)
                else:
                    contents.append(f"{item['content']}")
            except Exception:
                continue

        return raw_items if raw else contents

    async def close(self) -> None:
        """
        Close internal resources (executor). Idempotent.
        """
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
        self.search_client = None
        self._initialized = False


# Factory (keeps old name, but no 'af' parameter needed anymore)
async def create_reasoning_search(
    search_config: Optional[SearchConfig],
) -> ReasoningSearch:
    """
    Factory to create and initialize a ReasoningSearch instance.

    Args:
        search_config: Search configuration (may be None to produce a no-op instance)

    Returns:
        Initialized ReasoningSearch (is_available() indicates readiness).
    """
    search = ReasoningSearch(search_config)
    await search.initialize()
    return search