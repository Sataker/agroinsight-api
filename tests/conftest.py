import os

# Isolate from the host environment before the app reads its settings.
os.environ["ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    # No lifespan: tests must not start the scheduler or touch the database.
    return TestClient(app)
