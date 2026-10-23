"""
TenantConnectionRegistry — multi-tenant, per-user MCP session pool.

Keeps MCP sessions alive across agent requests so the Inspector proxy
bridge does not need to reconnect on every tool call.

Key design:
  - In-memory pool keyed by (tenant_id, user_id, server_name).
    Entries are any session object (ExternalMCPSession or ProxiedStdioSession).
  - Lightweight Cosmos DB persistence of session *metadata* (not the live
    object) so session info survives process restarts and can be used to
    attempt reconnection on recovery.
  - TTL eviction: entries idle > TTL_SECONDS are dropped from memory.
    No close() is called on eviction — cancel-scope ownership rules from
    anyio mean we must not close from a foreign task (see agent_pool.py).

Typical flow:
  1. get() → cache hit → return existing session (fastest path).
  2. get() → cache miss → caller creates session + calls register().
  3. register() stores session in pool and persists metadata to Cosmos.
  4. Background TTL eviction drops stale entries; GC handles cleanup.
  5. On process restart recover_sessions() reads Cosmos metadata so the
     agent framework can trigger reconnection on next call.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Idle time (seconds) before an entry is evicted from the in-memory pool.
_TTL_SECONDS: int = 3600  # 1 hour

# The pool and its last-used timestamps.
_pool: dict[tuple[str, str, str], Any] = {}
_last_used: dict[tuple[str, str, str], float] = {}

# Session metadata persisted to Cosmos (lightweight, no actual session object).
# Schema:  { "tenant_id": str, "user_id": str, "server_name": str,
#            "server_url": str, "transport": str, "registered_at": float }
_metadata: dict[tuple[str, str, str], dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# TTL eviction (memory only — does NOT close sessions)
# ---------------------------------------------------------------------------


def _evict_stale() -> None:
    """Drop pool entries that have exceeded the idle TTL.

    Does NOT call session.close() — anyio cancel scopes are task-local;
    calling close() from a different task raises RuntimeError.  Dropping
    the reference lets Python GC reclaim resources safely.
    """
    now = time.monotonic()
    stale = [k for k, t in _last_used.items() if now - t > _TTL_SECONDS]
    for key in stale:
        _pool.pop(key, None)
        _last_used.pop(key, None)
        # Keep metadata so recovery can still try to reconnect
        logger.info(
            "TenantRegistry: evicted stale session tenant=%s user=%s server=%s "
            "(idle >%ds) — reference dropped, GC handles cleanup",
            key[0][:8],
            key[1][:8],
            key[2],
            _TTL_SECONDS,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class TenantConnectionRegistry:
    """
    Singleton-style registry for (tenant_id, user_id, server_name) sessions.

    All methods are module-level helpers wrapped in a class for a clean API.
    The backing store is module-level to survive across multiple calls within
    the same process without requiring explicit singleton boilerplate.
    """

    # ------------------------------------------------------------------
    # In-memory pool operations
    # ------------------------------------------------------------------

    @staticmethod
    def get(tenant_id: str, user_id: str, server_name: str) -> Any | None:
        """Return the cached session or None if missing / evicted."""
        _evict_stale()
        key = (tenant_id, user_id, server_name)
        session = _pool.get(key)
        if session is not None:
            _last_used[key] = time.monotonic()
            logger.debug(
                "TenantRegistry: cache HIT tenant=%s user=%s server=%s (pool=%d)",
                tenant_id[:8],
                user_id[:8],
                server_name,
                len(_pool),
            )
        return session

    @staticmethod
    def register(
        tenant_id: str,
        user_id: str,
        server_name: str,
        session: Any,
        *,
        server_url: str = "",
        transport: str = "streamable-http",
    ) -> None:
        """Store a live session in the pool and record its metadata.

        Args:
            tenant_id: AAD tenant ID (or "" for anonymous/dev).
            user_id: AAD object ID of the user (or "" for shared sessions).
            server_name: Logical server name matching inspector config.
            session: A live ExternalMCPSession or ProxiedStdioSession object.
            server_url: Server endpoint URL for metadata persistence.
            transport: "streamable-http" | "stdio-via-proxy".
        """
        _evict_stale()
        key = (tenant_id, user_id, server_name)
        _pool[key] = session
        _last_used[key] = time.monotonic()
        _metadata[key] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "server_name": server_name,
            "server_url": server_url,
            "transport": transport,
            "registered_at": time.time(),
        }
        logger.info(
            "TenantRegistry: registered session tenant=%s user=%s server=%s transport=%s (pool=%d)",
            tenant_id[:8],
            user_id[:8],
            server_name,
            transport,
            len(_pool),
        )

    @staticmethod
    def evict(tenant_id: str, user_id: str, server_name: str) -> Any | None:
        """Remove and return a session from the pool (no close()).

        Returns the evicted session object so the caller can close it
        within the correct asyncio task if needed.
        """
        key = (tenant_id, user_id, server_name)
        session = _pool.pop(key, None)
        _last_used.pop(key, None)
        _metadata.pop(key, None)
        if session is not None:
            logger.info(
                "TenantRegistry: explicitly evicted tenant=%s user=%s server=%s",
                tenant_id[:8],
                user_id[:8],
                server_name,
            )
        return session

    @staticmethod
    def list_sessions(tenant_id: str = "", user_id: str = "") -> list[dict[str, Any]]:
        """Return metadata for all matching sessions.

        If tenant_id / user_id are empty they are treated as wildcards.
        """
        _evict_stale()
        results = []
        for key, meta in _metadata.items():
            if tenant_id and key[0] != tenant_id:
                continue
            if user_id and key[1] != user_id:
                continue
            alive = key in _pool
            results.append({**meta, "alive": alive, "last_used": _last_used.get(key)})
        return results

    # ------------------------------------------------------------------
    # Cosmos DB persistence
    # ------------------------------------------------------------------

    @staticmethod
    async def persist(
        tenant_id: str,
        user_id: str,
        server_name: str,
        *,
        server_url: str = "",
        transport: str = "streamable-http",
        cosmos_container=None,
    ) -> None:
        """Persist session metadata to Cosmos DB for crash-recovery.

        Writes a lightweight document (no token, no live object) so the
        framework can attempt reconnection on the next process restart.

        Args:
            cosmos_container: An open azure.cosmos.aio.ContainerProxy.
                              If None, persistence is skipped (dev / test).
        """
        if cosmos_container is None:
            logger.debug("TenantRegistry.persist: no container provided — skipping Cosmos write")
            return

        doc_id = f"session#{tenant_id}#{user_id}#{server_name}"
        doc = {
            "id": doc_id,
            "pk": f"session#{tenant_id}",
            "doc_type": "mcp_session_meta",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "server_name": server_name,
            "server_url": server_url,
            "transport": transport,
            "registered_at": time.time(),
            # 24-hour TTL — auto-deleted by Cosmos if session not renewed
            "ttl": 86400,
        }
        try:
            await cosmos_container.upsert_item(body=doc)
            logger.debug(
                "TenantRegistry.persist: wrote metadata for tenant=%s server=%s",
                tenant_id[:8],
                server_name,
            )
        except Exception as e:
            logger.warning("TenantRegistry.persist: Cosmos write failed for %s: %s", doc_id, e)

    @staticmethod
    async def recover_sessions(
        tenant_id: str,
        cosmos_container=None,
    ) -> list[dict[str, Any]]:
        """Read persisted session metadata from Cosmos for a tenant.

        Returns a list of metadata dicts that the caller can use to
        attempt reconnection (e.g., call connect_mcp_server for each).
        Does NOT create live session objects — that is the caller's job.

        Args:
            tenant_id: Tenant to recover sessions for.
            cosmos_container: An open azure.cosmos.aio.ContainerProxy.
                              If None returns empty list (dev / test).
        """
        if cosmos_container is None:
            return []

        pk = f"session#{tenant_id}"
        query = "SELECT * FROM c WHERE c.doc_type = 'mcp_session_meta' AND c.tenant_id = @tenant_id"
        params = [{"name": "@tenant_id", "value": tenant_id}]
        results = []
        try:
            async for item in cosmos_container.query_items(
                query=query,
                parameters=params,
                partition_key=pk,
            ):
                results.append({
                    "tenant_id": item.get("tenant_id", ""),
                    "user_id": item.get("user_id", ""),
                    "server_name": item.get("server_name", ""),
                    "server_url": item.get("server_url", ""),
                    "transport": item.get("transport", "streamable-http"),
                    "registered_at": item.get("registered_at"),
                })
            logger.info(
                "TenantRegistry.recover_sessions: found %d session(s) for tenant=%s",
                len(results),
                tenant_id[:8],
            )
        except Exception as e:
            logger.warning("TenantRegistry.recover_sessions: Cosmos query failed: %s", e)
        return results

    # ------------------------------------------------------------------
    # Pool statistics (for health-checks / admin endpoints)
    # ------------------------------------------------------------------

    @staticmethod
    def pool_size() -> int:
        """Return the number of live sessions currently in the pool."""
        return len(_pool)

    @staticmethod
    def metadata_count() -> int:
        """Return the number of tracked metadata entries (including evicted)."""
        return len(_metadata)


# Convenience singleton instance
registry = TenantConnectionRegistry()
