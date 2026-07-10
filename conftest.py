"""Repo-root pytest configuration (intentionally minimal).

The previous content inserted a broken sys.path entry (undefined Path/sys, a
path resolving outside the repo to the deprecated v4/magentic_agents layout)
and defined an unused agent_env_vars fixture. Removed as dead code — real
per-suite configuration lives in src/tests/backend/conftest.py,
src/tests/backend/auth/conftest.py, and src/tests/mcp_server/conftest.py.
"""