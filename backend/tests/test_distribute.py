"""POST /api/tasks/{code}/distribute — the missing link that let every task
close without ever touching a single retail point. Before this, there was no
way anywhere in the app (UI or API) to create a Delivery row, so the
"не все ТТ доставлены" close-gate was permanently vacuous (0 rows -> 0
"not delivered")."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_task(client: TestClient, headers: dict[str, str], **overrides) -> str:
    payload = {"name": "distribute-qa", "brand": "Darling", "brief_data": {"product_name": "x"}}
    payload.update(overrides)
    r = client.post("/api/tasks", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["code"]


def test_distribute_defaults_to_30_points(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(f"/api/tasks/{code}/distribute", headers=manager_headers, json={})
    assert r.status_code == 201, r.text
    rows = r.json()
    assert len(rows) == 30
    assert all(d["status"] == "pending" for d in rows)

    r = client.get(f"/api/tasks/{code}/deliveries", headers=manager_headers)
    assert len(r.json()) == 30


def test_distribute_twice_is_blocked(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    client.post(f"/api/tasks/{code}/distribute", headers=manager_headers, json={})
    r = client.post(f"/api/tasks/{code}/distribute", headers=manager_headers, json={})
    assert r.status_code == 409


def test_distribute_explicit_points(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    pts = client.get(
        "/api/retail-points", headers=manager_headers, params={"page_size": 3}
    ).json()["items"]
    ids = [p["id"] for p in pts]
    r = client.post(
        f"/api/tasks/{code}/distribute",
        headers=manager_headers,
        json={"point_ids": ids, "qty_expected": 2},
    )
    assert r.status_code == 201, r.text
    rows = r.json()
    assert len(rows) == 3
    assert all(d["qty_expected"] == 2 for d in rows)


def test_distribute_unknown_point_id_is_404(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/distribute",
        headers=manager_headers,
        json={"point_ids": [999999]},
    )
    assert r.status_code == 404


def test_viewer_cannot_distribute(client: TestClient, manager_headers, viewer_headers):
    code = _create_task(client, manager_headers)
    r = client.post(f"/api/tasks/{code}/distribute", headers=viewer_headers, json={})
    assert r.status_code == 403


def test_close_gate_now_real_after_distribute(client: TestClient, manager_headers: dict[str, str]):
    """Once distributed, closing must actually require every point delivered
    — this used to be unreachable because Delivery rows never existed."""
    code = _create_task(client, manager_headers)
    client.post(
        f"/api/tasks/{code}/distribute",
        headers=manager_headers,
        json={"count": 2},
    )
    client.post(
        "/api/payments",
        headers=manager_headers,
        json={
            "task": code,
            "contractor": "x",
            "currency": "RUB",
            "sample": "0",
            "tirazh": "0",
            "prepaid": "0",
            "balance": "0",
            "status": "",
        },
    )
    # walk to stage 11 the same way test_task_stage_flow's _advance_through_all_gates does
    from tests.test_task_stage_flow import _advance_through_all_gates

    _advance_through_all_gates(client, manager_headers, code)

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 12})
    assert r.status_code == 422
    assert "не все ТТ доставлены" in r.json()["detail"]

    deliveries = client.get(f"/api/tasks/{code}/deliveries", headers=manager_headers).json()
    for d in deliveries:
        client.patch(
            f"/api/deliveries/{d['id']}", headers=manager_headers, json={"status": "delivered"}
        )

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 12})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 12
