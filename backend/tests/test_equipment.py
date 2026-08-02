"""Equipment library: create, produce-to-task, and delete (with the
in-use safety check)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_equipment(client: TestClient, headers: dict[str, str]) -> int:
    r = client.post(
        "/api/equipment",
        headers=headers,
        json={"brand": "Darling", "name": "Тестовый стенд", "kind": "stand"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_delete_equipment_not_in_use(client: TestClient, manager_headers: dict[str, str]):
    eq_id = _create_equipment(client, manager_headers)
    assert client.delete(f"/api/equipment/{eq_id}", headers=manager_headers).status_code == 204
    assert client.delete(f"/api/equipment/{eq_id}", headers=manager_headers).status_code == 404


def test_delete_equipment_blocked_when_produced(
    client: TestClient, manager_headers: dict[str, str]
):
    eq_id = _create_equipment(client, manager_headers)
    r = client.post(f"/api/equipment/{eq_id}/produce", headers=manager_headers, json={})
    assert r.status_code == 201, r.text

    r = client.delete(f"/api/equipment/{eq_id}", headers=manager_headers)
    assert r.status_code == 409, r.text
