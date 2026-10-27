import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.core.config import cors_allowed_origins

client = TestClient(app)


def preflight(origin: str):
    return client.options("/v1/score", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
    })


def test_default_origin_is_allowed():
    response = preflight("http://localhost:8000")
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_unlisted_origin_is_not_allowed():
    response = preflight("https://evil.example")
    assert response.headers.get("access-control-allow-origin") is None


def test_origins_are_read_from_env(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_CORS_ORIGINS", "https://app.example.com, https://ops.example.com/")
    assert cors_allowed_origins() == ["https://app.example.com", "https://ops.example.com"]


def test_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("RISK_ENGINE_CORS_ORIGINS", raising=False)
    assert cors_allowed_origins() == ["http://localhost:8000"]


def test_wildcard_is_rejected(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_CORS_ORIGINS", "*")
    with pytest.raises(ValueError):
        cors_allowed_origins()
