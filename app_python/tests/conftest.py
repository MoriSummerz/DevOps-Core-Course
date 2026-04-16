"""Pytest configuration and fixtures for testing the FastAPI application."""

import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Point the visits counter at a writable temp location before app import
os.environ.setdefault("VISITS_FILE", str(Path(tempfile.gettempdir()) / "visits-test"))

import pytest
from fastapi.testclient import TestClient

from app import app
from routes.visits.service import VisitsCounter, get_visits_counter


@pytest.fixture
def client(tmp_path):
    """Create a test client for the FastAPI application."""
    counter = VisitsCounter(tmp_path / "visits")
    app.dependency_overrides[get_visits_counter] = lambda: counter
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_visits_counter, None)
