"""Delivery installation tracking (PATCH /deliveries/{id} `installed` flag).

Stage 7 "Отгрузка" (delivery arriving) and stage 8 "Монтаж" are distinct
real-world events:
goods can arrive at a retail point before anyone has actually installed
them. Installation may only be recorded once the delivery itself is
confirmed (`status == delivered`)."""

from __future__ import annotations

from app import models
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def _create_task(client: TestClient, headers: dict[str, str]) -> str:
    r = client.post(
        "/api/tasks",
        headers=headers,
        json={
            "name": "delivery-test",
            "brand": "Darling",
            "tt_total": 0,
            "brief_data": {"product_name": "delivery-test"},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["code"]


def _make_delivery(db: Session, code: str) -> int:
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    point = db.scalar(select(models.RetailPoint).limit(1))
    d = models.Delivery(task_id=task.id, retail_point_id=point.id, qty_expected=5)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d.id


def test_cannot_mark_installed_before_delivered(
    client: TestClient, manager_headers: dict[str, str], db: Session
):
    code = _create_task(client, manager_headers)
    delivery_id = _make_delivery(db, code)

    r = client.patch(
        f"/api/deliveries/{delivery_id}", headers=manager_headers, json={"installed": True}
    )
    assert r.status_code == 422

    r = client.patch(
        f"/api/deliveries/{delivery_id}", headers=manager_headers, json={"status": "delivered"}
    )
    assert r.status_code == 200

    r = client.patch(
        f"/api/deliveries/{delivery_id}", headers=manager_headers, json={"installed": True}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["installed_at"] is not None
    assert body["installed_by"]


def test_unmarking_installed_clears_fields(
    client: TestClient, manager_headers: dict[str, str], db: Session
):
    code = _create_task(client, manager_headers)
    delivery_id = _make_delivery(db, code)
    client.patch(
        f"/api/deliveries/{delivery_id}", headers=manager_headers, json={"status": "delivered"}
    )
    client.patch(
        f"/api/deliveries/{delivery_id}", headers=manager_headers, json={"installed": True}
    )

    r = client.patch(
        f"/api/deliveries/{delivery_id}", headers=manager_headers, json={"installed": False}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["installed_at"] is None
    assert body["installed_by"] == ""
