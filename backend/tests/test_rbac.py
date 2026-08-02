"""Role-based access control on write/admin endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_viewer_cannot_create_task(client: TestClient, viewer_headers: dict[str, str]):
    r = client.post("/api/tasks", headers=viewer_headers, json={"name": "X", "brand": "Darling"})
    assert r.status_code == 403


def test_manager_can_create_task(client: TestClient, manager_headers: dict[str, str]):
    r = client.post(
        "/api/tasks",
        headers=manager_headers,
        json={"name": "Тестовый дисплей", "brand": "Darling", "tt_total": 0},
    )
    assert r.status_code == 201, r.text
    assert r.json()["code"].startswith("RD-")


def test_users_list_is_admin_only(
    client: TestClient, viewer_headers: dict[str, str], admin_headers: dict[str, str]
):
    assert client.get("/api/users", headers=viewer_headers).status_code == 403
    assert client.get("/api/users", headers=admin_headers).status_code == 200
