"""Tests run against a throw-away SQLite file, never against the real PostgreSQL."""
import os
import pathlib

TEST_DB = pathlib.Path(__file__).parent / "test.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample():
    return {"title": "Laptop will not boot", "description": "Black screen after login", "priority": "high", "requester": "priya@example.com"}
