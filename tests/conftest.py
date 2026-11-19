"""Ensure the project root is on sys.path when running bare `pytest` and reset cache."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(autouse=True)
def reset_query_cache():
    """Clear query cache before each test to isolate test cases."""
    try:
        from app.cache import query_cache

        query_cache.clear()
    except ImportError:
        pass
    yield
