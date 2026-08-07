"""Dashboard KPIs and seeded reference data."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_kpis_reflect_seeded_reference_data(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/dashboard/kpis", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["brands_count"] == 13
    assert body["active_tasks"] == 0  # no products seeded, only reference data


def test_tasks_list_starts_empty(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/tasks", headers=admin_headers, params={"page_size": 200})
    assert r.json()["total"] == 0


def test_retail_points_are_seeded_and_renamed(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/retail-points", headers=admin_headers, params={"page_size": 5})
    body = r.json()
    assert body["total"] == 90
    names = " ".join(p["name"] for p in body["items"])
    assert "Золотое Яблоко" in names


def test_budget_spent_reflects_task_budget_edits(client: TestClient, admin_headers: dict[str, str]):
    """The "Бюджет" field editable on the «Бюджет и КП» stage (task.budget) must
    be what "освоено" sums — not the unreachable production_cost column, which
    has no edit UI and would otherwise leave the dashboard/groups KPIs frozen."""
    r = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={"name": "budget-kpi", "brand": "Darling", "brief_data": {"product_name": "x"}},
    )
    assert r.status_code == 201, r.text
    code = r.json()["code"]

    r = client.patch(f"/api/tasks/{code}", headers=admin_headers, json={"budget": 500_000})
    assert r.status_code == 200, r.text

    r = client.get("/api/dashboard/kpis", headers=admin_headers)
    assert r.json()["budget_spent"] >= 500_000

    r = client.get("/api/groups", headers=admin_headers)
    darling_group = next(g for g in r.json() if g["code"] == "A")
    assert darling_group["budget_spent"] >= 500_000
