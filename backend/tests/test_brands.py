"""Brand delete: blocked whenever any task references it.

Unlike Equipment (equipment_id is nullable, ondelete=SET NULL — a deleted
equipment card just detaches from its tasks), Task.brand_id is NOT NULL with
ondelete=RESTRICT: a task keeps its brand forever, closed or not. So a brand
can only be deleted once truly zero tasks (of any stage) reference it — there
is no "close the task first" workaround."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_brand(client: TestClient, headers: dict[str, str], name: str) -> tuple[int, str]:
    r = client.post("/api/brands", headers=headers, json={"name": name, "group": "A"})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["id"], body["name"]


def test_delete_brand_not_in_use(client: TestClient, manager_headers: dict[str, str]):
    brand_id, _ = _create_brand(client, manager_headers, "Тестовый Бренд 1")
    assert client.delete(f"/api/brands/{brand_id}", headers=manager_headers).status_code == 204
    assert client.delete(f"/api/brands/{brand_id}", headers=manager_headers).status_code == 404


def test_delete_brand_blocked_while_any_task_exists(
    client: TestClient, manager_headers: dict[str, str]
):
    brand_id, brand_name = _create_brand(client, manager_headers, "Тестовый Бренд 2")
    r = client.post(
        "/api/tasks",
        headers=manager_headers,
        json={"name": "t", "brand": brand_name, "tt_total": 0, "brief_data": {"product_name": "t"}},
    )
    assert r.status_code == 201, r.text

    r = client.delete(f"/api/brands/{brand_id}", headers=manager_headers)
    assert r.status_code == 409, r.text
    assert "включая архивные" in r.json()["detail"]
