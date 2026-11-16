"""CORS must never advertise a wildcard origin together with credentials.

`allow_origins=["*"]` + `allow_credentials=True` made every response say
`Access-Control-Allow-Origin: *` and `Access-Control-Allow-Credentials: true`
— a pair browsers must reject — and echoed any preflight origin, including
attacker-controlled ones. These tests pin the fixed behaviour.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, cors_origins

ALLOWED = "http://localhost:5173"
FOREIGN = "https://evil.example"


def _cors(headers):
    return {
        k.lower(): v
        for k, v in headers.items()
        if k.lower().startswith("access-control") or k.lower() == "vary"
    }


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


# ------------------------------------------------------------- config plumbing

def test_wildcard_is_dropped_from_configured_origins():
    settings = Settings(_env_file=None, cors_origins="*, https://app.example.com")

    assert cors_origins(settings) == ["https://app.example.com"]


def test_origins_are_read_from_settings_and_trimmed():
    settings = Settings(
        _env_file=None,
        cors_origins="https://a.example ,  https://b.example",
    )

    assert cors_origins(settings) == ["https://a.example", "https://b.example"]


def test_default_origins_are_dev_only_not_a_wildcard():
    settings = Settings(_env_file=None)

    configured = cors_origins(settings)
    assert configured, "the dev server origin must be allowed by default"
    assert "*" not in configured
    assert all(o.startswith("http://localhost") or o.startswith("http://127.0.0.1")
               for o in configured)


# ------------------------------------------------------------- simple requests

def test_allowed_origin_is_echoed_with_credentials(client):
    response = client.get("/api/health", headers={"Origin": ALLOWED})

    assert response.status_code == 200
    headers = _cors(response.headers)
    assert headers["access-control-allow-origin"] == ALLOWED
    assert headers["access-control-allow-credentials"] == "true"
    assert "origin" in headers.get("vary", "").lower()


def test_foreign_origin_gets_no_cors_grant(client):
    response = client.get("/api/health", headers={"Origin": FOREIGN})

    headers = _cors(response.headers)
    # The grant is Access-Control-Allow-Origin; Starlette emits
    # Allow-Credentials unconditionally, which grants nothing on its own.
    assert "access-control-allow-origin" not in headers


def test_wildcard_is_never_sent_with_credentials(client):
    # The regression that broke production browser calls.
    for origin in (ALLOWED, FOREIGN, "null"):
        response = client.get("/api/health", headers={"Origin": origin})
        headers = _cors(response.headers)
        allowed_origin = headers.get("access-control-allow-origin")
        assert allowed_origin != "*"
        # A grant, when present, names the exact caller — never everyone.
        if allowed_origin is not None:
            assert allowed_origin == origin


# ----------------------------------------------------------------- preflight

def test_preflight_from_allowed_origin_succeeds(client):
    response = client.options(
        "/api/workflows",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    headers = _cors(response.headers)
    assert headers["access-control-allow-origin"] == ALLOWED
    assert headers["access-control-allow-credentials"] == "true"
    assert "POST" in headers["access-control-allow-methods"]


def test_preflight_from_foreign_origin_is_refused(client):
    response = client.options(
        "/api/workflows",
        headers={"Origin": FOREIGN, "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 400
    headers = _cors(response.headers)
    assert "access-control-allow-origin" not in headers
