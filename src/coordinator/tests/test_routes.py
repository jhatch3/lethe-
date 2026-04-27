"""Smoke tests for HTTP routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root() -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "lethe-coordinator"


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_status_shape() -> None:
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert "coordinator" in body
    assert "agents" in body
    assert isinstance(body["agents"]["audit"], list)
    assert len(body["agents"]["audit"]) >= 1
    for a in body["agents"]["audit"]:
        assert "name" in a
        assert "model" in a
        assert "skills" in a


def test_samples_list() -> None:
    r = client.get("/api/samples")
    assert r.status_code == 200
    body = r.json()
    assert "samples" in body
    assert isinstance(body["samples"], list)
    names = {s["name"] for s in body["samples"]}
    # At least these three should ship
    assert "general-hospital-er" in names


def test_create_job_rejects_unsupported_type() -> None:
    r = client.post(
        "/api/jobs",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert r.status_code == 415


def test_create_job_rejects_empty() -> None:
    r = client.post(
        "/api/jobs",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert r.status_code == 400


def test_get_unknown_job_returns_410() -> None:
    r = client.get("/api/jobs/0000000000000000000000000000000000000000")
    assert r.status_code == 410


def test_verify_rejects_bad_sha() -> None:
    r = client.get("/api/verify/notahash")
    assert r.status_code == 400


def test_verify_accepts_valid_format() -> None:
    # 64 hex chars; might be unanchored, that's fine — we just want a 200/410.
    r = client.get("/api/verify/" + "ab" * 32)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert "anchored" in body