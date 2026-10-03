import importlib
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def health_app(monkeypatch):
    monkeypatch.setenv("WORKER_DATABASE_URL", "sqlite://")
    module = importlib.import_module("liqi_data.main")
    engine = MagicMock()
    monkeypatch.setattr(module, "engine", engine)
    return module.app, engine


def test_health_checks_database(health_app):
    app, engine = health_app
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "up"}
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.assert_called_once()
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"


def test_health_returns_unavailable_on_database_error(health_app):
    app, engine = health_app
    engine.connect.side_effect = SQLAlchemyError("database unavailable")
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "db": "down"}
