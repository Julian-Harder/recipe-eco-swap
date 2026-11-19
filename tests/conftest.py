"""Shared test setup: make src/ importable and load the data files once per test run."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from foods import load_foods  # noqa: E402
from match import load_categories  # noqa: E402
from swaps import load_swaps  # noqa: E402


@pytest.fixture(scope="session")
def foods():
    return load_foods()


@pytest.fixture(scope="session")
def categories():
    return load_categories()


@pytest.fixture(scope="session")
def swaps():
    return load_swaps()
