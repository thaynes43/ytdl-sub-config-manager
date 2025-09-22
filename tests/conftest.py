"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add src to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import after path setup
from core.logging import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Set up logging for all tests."""
    setup_logging(level="ERROR")  # Reduce noise during tests


@pytest.fixture
def project_root_dir():
    """Provide the project root directory path."""
    return project_root


@pytest.fixture
def example_subscriptions_file():
    """Provide path to the example subscriptions file."""
    subs_file = project_root / "subscriptions.example.yaml"
    if not subs_file.exists():
        pytest.skip("subscriptions.example.yaml not found in project root")
    return str(subs_file)
