"""Every deletion across the app (task/brand/equipment/retail point/document)
must leave a trace in the same audit_log already used for budget edits — a
deleted record shouldn't just vanish without who/when/what."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _log_entries(client: TestClient, headers: dict[str, str]) -> list[dict]:
    r = client.get("/api/budget/log", headers=headers, params={"limit": 200})
    assert r.status_code == 200, r.text
    return r.json()


def test_task_delete_is_logged(client: TestClient, admin_headers: dict[str, str]):
    r = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={"name": "audit-me", "brand": "Darling", "brief_data": {"product_name": "x"}},
    )
    code = r.json()["code"]
    client.delete(f"/api/tasks/{code}", headers=admin_headers)

    entries = _log_entries(client, admin_headers)
    hit = next(e for e in entries if e["entity_type"] == "task" and e["task"] == code)
    assert hit["field"] == "Удаление"
    assert code in hit["old"]
    assert hit["who"] == "Администратор"


def test_brand_delete_is_logged(client: TestClient, admin_headers: dict[str, str]):
    client.post("/api/brands", headers=admin_headers, json={"name": "AuditBrand", "group": "A"})
    r = client.get("/api/brands", headers=admin_headers)
    brand = next(b for b in r.json() if b["name"] == "AuditBrand")
    client.delete(f"/api/brands/{brand['id']}", headers=admin_headers)

    entries = _log_entries(client, admin_headers)
    hit = next(e for e in entries if e["entity_type"] == "brand" and e["task"] == "AuditBrand")
    assert hit["field"] == "Удаление"


def test_equipment_delete_is_logged(client: TestClient, admin_headers: dict[str, str]):
    r = client.post(
        "/api/equipment",
        headers=admin_headers,
        json={
            "name": "audit-eq",
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
    client.delete(f"/api/equipment/{eq_id}", headers=admin_headers)

    entries = _log_entries(client, admin_headers)
    hit = next(e for e in entries if e["entity_type"] == "equipment" and e["task"] == str(eq_id))
    assert "audit-eq" in hit["old"]
