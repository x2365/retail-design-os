"""Demo data reset point endpoints (routers/internal.py's /internal/snapshot/*
and /internal/run-snapshot-reset). The actual pg_dump/pg_restore round-trip
needs a real PostgreSQL server (services/snapshot.py refuses to run against
SQLite, which is what the test suite uses) — these tests cover the parts
that don't: auth gating (admin-only for the UI-facing endpoints, service
token for the cron-facing one, mirroring run-reminders/1С) and that the
SQLite guard surfaces as a clean 500, not an unhandled crash."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_snapshot_endpoints_require_admin(client: TestClient, manager_headers: dict[str, str]):
    assert client.get("/api/internal/snapshot", headers=manager_headers).status_code == 403
    assert client.post("/api/internal/snapshot/take", headers=manager_headers).status_code == 403
    assert (
        client.post("/api/internal/snapshot/restore", headers=manager_headers).status_code == 403
    )


def test_no_snapshot_yet_reports_null(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/internal/snapshot", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"taken_at": None, "size_bytes": 0}


def test_take_snapshot_on_sqlite_is_a_clean_500_not_a_crash(
    client: TestClient, admin_headers: dict[str, str]
):
    r = client.post("/api/internal/snapshot/take", headers=admin_headers)
    assert r.status_code == 500, r.text
    assert "PostgreSQL" in r.json()["detail"]


def test_restore_without_snapshot_or_on_sqlite_is_a_clean_500(
    client: TestClient, admin_headers: dict[str, str]
):
    r = client.post("/api/internal/snapshot/restore", headers=admin_headers)
    assert r.status_code == 500, r.text
    assert "PostgreSQL" in r.json()["detail"]


def test_run_snapshot_reset_disabled_by_default(client: TestClient):
    r = client.post(
        "/api/internal/run-snapshot-reset", headers={"X-Service-Token": "whatever"}
    )
    assert r.status_code == 403


def test_run_snapshot_reset_wrong_token(client: TestClient, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "snapshot_reset_service_token", "the-real-token")
    r = client.post("/api/internal/run-snapshot-reset", headers={"X-Service-Token": "wrong"})
    assert r.status_code == 401


def test_run_snapshot_reset_valid_token_but_sqlite_is_a_clean_500(
    client: TestClient, monkeypatch
):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "snapshot_reset_service_token", "the-real-token")
    r = client.post(
        "/api/internal/run-snapshot-reset", headers={"X-Service-Token": "the-real-token"}
    )
    assert r.status_code == 500, r.text
    assert "PostgreSQL" in r.json()["detail"]
