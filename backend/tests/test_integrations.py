"""POST /api/internal/1c/payment-status — the receiving side of a future 1С
push (no real 1С is connected; this is the webhook contract it would call).
Service-token auth, no user session — mirrors internal.py's reminders
endpoint. conftest.py sets ONEC_SERVICE_TOKEN=test-1c-token for the suite."""

from __future__ import annotations

from fastapi.testclient import TestClient

TOKEN = "test-1c-token"


def _create_task(client: TestClient, headers: dict[str, str], **overrides) -> str:
    payload = {
        "name": "1c-test",
        "brand": "Darling",
        "brief_data": {"product_name": "x"},
        "deadline": "2026-12-01",
        "launch": "2026-11-15",
    }
    payload.update(overrides)
    r = client.post("/api/tasks", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["code"]


def test_missing_token_is_401(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(
        "/api/internal/1c/payment-status",
        json={"task": code, "status": "paid"},
    )
    assert r.status_code == 401


def test_wrong_token_is_401(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(
        "/api/internal/1c/payment-status",
        headers={"X-Service-Token": "wrong"},
        json={"task": code, "status": "paid"},
    )
    assert r.status_code == 401


def test_disabled_without_configured_token(
    client: TestClient, manager_headers: dict[str, str], monkeypatch
):
    from app.config import get_settings

    code = _create_task(client, manager_headers)
    monkeypatch.setattr(get_settings(), "onec_service_token", "")
    r = client.post(
        "/api/internal/1c/payment-status",
        headers={"X-Service-Token": TOKEN},
        json={"task": code, "status": "paid"},
    )
    assert r.status_code == 403


def test_valid_token_updates_status_and_logs_1c_as_author(
    client: TestClient, manager_headers: dict[str, str], admin_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    r = client.post(
        "/api/internal/1c/payment-status",
        headers={"X-Service-Token": TOKEN},
        json={"task": code, "status": "paid"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["payment_status"] == "paid"

    r = client.get("/api/tasks/" + code, headers=manager_headers)
    assert r.json()["payment_status"] == "paid"

    log = client.get("/api/budget/log", headers=admin_headers, params={"limit": 200}).json()
    hit = next(e for e in log if e["task"] == code and e["field"] == "Статус оплаты")
    assert hit["who"] == "1С (автоматически)"
    assert hit["new"] == "Оплачено"


def test_unknown_task_is_404(client: TestClient):
    r = client.post(
        "/api/internal/1c/payment-status",
        headers={"X-Service-Token": TOKEN},
        json={"task": "RD-999", "status": "paid"},
    )
    assert r.status_code == 404


def test_invalid_status_is_400(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(
        "/api/internal/1c/payment-status",
        headers={"X-Service-Token": TOKEN},
        json={"task": code, "status": "not-a-real-status"},
    )
    assert r.status_code == 400
