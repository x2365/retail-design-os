"""Equipment library: create, produce-to-task, and delete (with the
in-use safety check)."""

from __future__ import annotations

from app import models
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


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


def test_delete_equipment_allowed_when_task_closed(
    client: TestClient, manager_headers: dict[str, str], db: Session
):
    """A closed task ("Закрыт") is a finished production run, not
    something "запущенное" (running) — it must not block deletion the way a
    live task does."""
    eq_id = _create_equipment(client, manager_headers)
    r = client.post(f"/api/equipment/{eq_id}/produce", headers=manager_headers, json={})
    assert r.status_code == 201, r.text
    code = r.json()["code"]

    task = db.scalar(select(models.Task).where(models.Task.code == code))
    task.stage = models.TaskStage.CLOSED
    db.commit()

    r = client.delete(f"/api/equipment/{eq_id}", headers=manager_headers)
    assert r.status_code == 204, r.text
