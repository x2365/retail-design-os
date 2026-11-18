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


# ---- pg_dump/pg_restore wiring (subprocess mocked: the suite runs on SQLite,
# so these pin the two Postgres-only bugs found against a real Postgres 18) ---


class _FakeSnap:
    payload = b"dump-bytes"


class _FakeSession:
    def __init__(self, events: list[str]):
        self.events = events

    def rollback(self) -> None:
        self.events.append("rollback")


def _pretend_postgres(monkeypatch):
    from app.services import snapshot

    monkeypatch.setattr(snapshot, "_require_postgres", lambda: "postgresql://x/y")
    return snapshot


def test_restore_ends_own_transaction_before_pg_restore(monkeypatch):
    """The request's open transaction holds ACCESS SHARE locks (e.g. on
    `users`, read by the auth dependency); `pg_restore --clean` needs ACCESS
    EXCLUSIVE to drop those tables, so without a rollback first it hangs on
    our own session until the timeout."""
    import subprocess

    snapshot = _pretend_postgres(monkeypatch)
    events: list[str] = []
    monkeypatch.setattr(snapshot, "get_snapshot", lambda db: _FakeSnap())

    def fake_run(args, **kw):
        events.append(args[0])
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(snapshot.subprocess, "run", fake_run)
    snapshot.restore_snapshot(_FakeSession(events))  # type: ignore[arg-type]
    assert events == ["rollback", "pg_restore"]


def test_dump_excludes_snapshot_table_and_its_sequence(monkeypatch):
    """pg_dump keeps a serial column's sequence even when its table is
    excluded; restoring that dump with --clean then fails on
    `DROP SEQUENCE data_snapshots_id_seq`."""
    import subprocess

    snapshot = _pretend_postgres(monkeypatch)
    seen: dict[str, list[str]] = {}

    def fake_run(args, **kw):
        seen["args"] = args
        return subprocess.CompletedProcess(args, 1, b"", b"stop here")

    monkeypatch.setattr(snapshot.subprocess, "run", fake_run)
    try:
        snapshot.take_snapshot(None)  # type: ignore[arg-type]
    except RuntimeError:
        pass
    excluded = {
        seen["args"][i + 1] for i, a in enumerate(seen["args"]) if a == "--exclude-table"
    }
    assert {"data_snapshots", "data_snapshots_id_seq", "alembic_version"} <= excluded
