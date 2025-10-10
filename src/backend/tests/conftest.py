"""
Test configuration for backend unit tests.

Sets up Python path to allow imports from common.utils.
"""

import sys
from pathlib import Path

# Add backend directory to Python path so tests can import from common.utils
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))



