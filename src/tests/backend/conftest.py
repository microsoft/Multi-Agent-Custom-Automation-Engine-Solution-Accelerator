"""Shared test configuration for backend tests.

Pre-imports critical packages to prevent sys.modules pollution from
module-level mocking in individual test files.  Several test files use
``sys.modules.setdefault('models', Mock())`` at module level which, when
collected before other tests, replaces the real ``models`` package with
a Mock and breaks ``from models.plan_models import MPlan`` for all
subsequently-collected test files.

Pre-importing the real package here (conftest.py is loaded before any
test module) ensures ``setdefault()`` becomes a no-op.
"""

import os
import sys

# Ensure src/backend/ is on sys.path so short absolute imports
# (e.g. ``from models.plan_models import MPlan``) resolve correctly.
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Pre-import the real 'models' package so that test files
# which mock 'models' via sys.modules don't poison the
# namespace for all later test files.
import models  # noqa: E402, F401
import models.plan_models  # noqa: E402, F401
import models.messages  # noqa: E402, F401

# Pre-import packages commonly poisoned by module-level sys.modules mocking
import orchestration  # noqa: E402, F401
import orchestration.connection_config  # noqa: E402, F401
import services  # noqa: E402, F401
import agent_framework  # noqa: E402, F401
import common  # noqa: E402, F401

# Pre-import backend.app so test_app.py doesn't fail when other test files
# pollute sys.modules with Mocks during collection.
# NOTE: This caches backend.app and all its transitive imports (including
# agent_framework, orchestration_manager, etc.) with REAL references.
# Tests that rely on sys.modules mocking of those modules must use
# patch() within test methods rather than module-level sys.modules
# assignments to override symbols in already-imported modules.
import backend.app  # noqa: E402, F401
