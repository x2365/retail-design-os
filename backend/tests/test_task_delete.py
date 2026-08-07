"""DELETE /api/tasks/{code} — admin-only, irreversible cleanup of everything
attached to the task (comments, payment, documents, deliveries, nomenclature),
without touching the library card the task may have been produced from."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_task(client: TestClient, headers: dict[str, str], **overrides) -> str:
    payload = {"name": "delete-me", "brand": "Darling", "brief_data": {"product_name": "x"}}
    payload.update(overrides)
    r = client.post("/api/tasks", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["code"]


def test_manager_cannot_delete_task(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.delete(f"/api/tasks/{code}", headers=manager_headers)
    assert r.status_code == 403


def test_admin_deletes_task_and_related_rows(
    client: TestClient, admin_headers: dict[str, str], manager_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)

    r = client.post(
        f"/api/tasks/{code}/comments", headers=manager_headers, json={"text": "hello"}
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/api/payments",
        headers=manager_headers,
        json={
            "task": code,
            "contractor": "ООО Test",
            "currency": "RUB",
            "sample": "0",
            "tirazh": "0",
            "prepaid": "0",
            "balance": "0",
            "status": "",
        },
    )
    assert r.status_code == 201, r.text

    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "brief", "stage": "1"},
        files={"file": ("brief.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 201, r.text

    r = client.delete(f"/api/tasks/{code}", headers=admin_headers)
    assert r.status_code == 204, r.text

    r = client.get(f"/api/tasks/{code}", headers=admin_headers)
    assert r.status_code == 404

    r = client.get("/api/payments", headers=admin_headers)
    assert code not in {p["id"] for p in r.json()}


def test_delete_unknown_task_is_404(client: TestClient, admin_headers: dict[str, str]):
    r = client.delete("/api/tasks/RD-999", headers=admin_headers)
    assert r.status_code == 404


def test_delete_task_keeps_library_card(
    client: TestClient, admin_headers: dict[str, str], manager_headers: dict[str, str]
):
    """A task produced from an Equipment library card must not take the card
    down with it — the card has its own lifecycle (times_produced, re-runs)."""
    r = client.post(
        "/api/equipment",
        headers=manager_headers,
        json={
            "name": "delete-qa-eq",
            "brand": "Darling",
            "kind": "stand",
            "dimensions": "",
            "description": "",
            "est_budget": 0,
            "est_sample": 0,
            "est_tirazh": 0,
            "currency": "RUB",
        },
    )
    eq_id = r.json()["id"]

    r = client.post(
        f"/api/equipment/{eq_id}/produce", headers=manager_headers, json={"team": [], "tt_total": 0}
    )
    assert r.status_code == 201, r.text
    code = r.json()["code"]

    r = client.delete(f"/api/tasks/{code}", headers=admin_headers)
    assert r.status_code == 204

    r = client.get("/api/equipment", headers=admin_headers)
    assert any(e["id"] == eq_id for e in r.json())
