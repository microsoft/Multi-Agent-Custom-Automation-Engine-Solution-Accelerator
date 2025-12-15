"""Magentic AI agents for V4 backend."""

# Import modules to ensure coverage detection
try:
    from . import foundry_agent
    from . import magentic_agent_factory
    from . import proxy_agent
    from . import common
    from . import models
except ImportError:
    pass