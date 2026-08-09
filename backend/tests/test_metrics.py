"""GET /api/metrics — flow metrics (WIP/Lead Time/Throughput/Rework Rate)
computed purely from existing TaskStageHistory + Task.stage data."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.test_task_stage_flow import _advance_through_all_gates, _create_task


def test_metrics_reflect_wip_lead_time_and_rework(
    client: TestClient, manager_headers: dict[str, str]
):
    # Task 1: stays open at stage 3 — counts toward WIP, not toward lead time.
    open_code = _create_task(client, manager_headers)
    client.post(
        f"/api/tasks/{open_code}/documents",
        headers=manager_headers,
        data={"kind": "brief", "stage": "1"},
        files={"file": ("b.pdf", b"%PDF", "application/pdf")},
    )
    client.patch(f"/api/tasks/{open_code}", headers=manager_headers, json={"stage": 2})
    client.post(
        f"/api/tasks/{open_code}/documents",
        headers=manager_headers,
        data={"kind": "sketch", "stage": "2"},
        files={"file": ("s.png", b"x", "image/png")},
    )
    client.patch(f"/api/tasks/{open_code}", headers=manager_headers, json={"stage": 3})

    # Task 2: walk all the way through, revert once (rework), re-advance,
    # pay, and close — exercises lead time + rework + throughput together.
    closed_code = _create_task(client, manager_headers)
    _advance_through_all_gates(client, manager_headers, closed_code)
    r = client.get(f"/api/tasks/{closed_code}", headers=manager_headers)
    assert r.json()["stage"] == 11

    r = client.patch(f"/api/tasks/{closed_code}", headers=manager_headers, json={"stage": 10})
    assert r.status_code == 200, r.text
    r = client.patch(f"/api/tasks/{closed_code}", headers=manager_headers, json={"stage": 11})
    assert r.status_code == 200, r.text

    client.post(
        "/api/payments",
        headers=manager_headers,
        json={
            "task": closed_code,
            "contractor": "x",
            "currency": "RUB",
            "sample": "0",
            "tirazh": "0",
            "prepaid": "0",
            "balance": "0",
            "status": "",
        },
    )
    r = client.patch(f"/api/tasks/{closed_code}", headers=manager_headers, json={"stage": 12})
    assert r.status_code == 200, r.text

    m = client.get("/api/metrics", headers=manager_headers)
    assert m.status_code == 200, m.text
    body = m.json()

    assert body["wip_by_stage"]["3"] >= 1
    assert "12" not in body["wip_by_stage"]  # closed tasks aren't WIP

    assert body["lead_time_avg_days"] is not None
    assert body["lead_time_avg_days"] >= 0

    assert sum(w["count"] for w in body["throughput_by_week"]) >= 1
    assert len(body["throughput_by_week"]) == 8

    assert body["total_transitions"] >= 1
    assert body["rework_rate"] > 0  # the 11->10 revert must show up


def test_metrics_requires_auth(client: TestClient):
    r = client.get("/api/metrics")
    assert r.status_code == 401
