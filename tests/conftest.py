from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentic_url_shortener.config import Settings
from agentic_url_shortener.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
        workspace_root=tmp_path / "runs",
        provider="mock",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    with TestClient(create_app(settings)) as test_client:
        yield test_client

