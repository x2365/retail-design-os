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


def test_new_task_code_never_collides_after_a_deletion(
    client: TestClient, admin_headers: dict[str, str], manager_headers: dict[str, str]
):
    """Regression: _next_code used to be COUNT(*)-based. Deleting the
    earliest task dropped the count, so the next create reused a code that
    still belonged to a later, non-deleted task — hitting the DB's unique
    constraint on tasks.code and crashing with a 500."""
    first = _create_task(client, manager_headers, name="first")
    second = _create_task(client, manager_headers, name="second")
    third = _create_task(client, manager_headers, name="third")
    assert len({first, second, third}) == 3

    r = client.delete(f"/api/tasks/{first}", headers=admin_headers)
    assert r.status_code == 204

    r = client.post(
        "/api/tasks",
        headers=manager_headers,
        json={"name": "fourth", "brand": "Darling", "brief_data": {"product_name": "x"}},
    )
    assert r.status_code == 201, r.text
    fourth = r.json()["code"]
    assert fourth not in {first, second, third}


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
