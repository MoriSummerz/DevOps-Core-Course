"""Pytest configuration and fixtures for testing the FastAPI application."""

import sys
from pathlib import Path

# Add the parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client
