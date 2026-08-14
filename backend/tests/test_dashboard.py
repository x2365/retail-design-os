"""Dashboard KPIs and seeded reference data."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_kpis_reflect_seeded_reference_data(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/dashboard/kpis", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # seed() no longer creates any brands (removed self-healing that kept
    # resurrecting deleted placeholder brands on every deploy) — the one
    # brand here ("Darling") is created by conftest.py's client fixture
    # purely so the test suite has a brand to attach tasks to.
    assert body["brands_count"] == 1
    assert body["active_tasks"] == 0  # no products seeded, only reference data


def test_tasks_list_starts_empty(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/tasks", headers=admin_headers, params={"page_size": 200})
    assert r.json()["total"] == 0


def test_retail_points_are_seeded_with_generic_names(
    client: TestClient, admin_headers: dict[str, str]
):
    """Point names must stay generic ("Магазин №N") — not a real retailer
    name (this used to bake "Золотое Яблоко" into every seeded point)."""
    r = client.get("/api/retail-points", headers=admin_headers, params={"page_size": 5})
    body = r.json()
    assert body["total"] == 90
    names = " ".join(p["name"] for p in body["items"])
    assert "Золотое Яблоко" not in names
    assert "Магазин №1" in names


def test_budget_spent_reflects_kp_approved_sample_and_tirazh(
    client: TestClient, admin_headers: dict[str, str]
):
    """task.budget is no longer hand-typed — it's Образец+Тираж, set the
    moment both КП gates (Финансы/Бренд) are approved. "освоено" (budget_spent)
    must be what that sum feeds — not the unreachable production_cost column,
    which has no edit UI and would otherwise leave the dashboard/groups KPIs
    frozen."""
    r = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={"name": "budget-kpi", "brand": "Darling", "brief_data": {"product_name": "x"}},
    )
    assert r.status_code == 201, r.text
    code = r.json()["code"]

    r = client.patch(
        f"/api/tasks/{code}",
        headers=admin_headers,
        json={"sample_cost": 200_000, "tirazh_cost": 300_000},
    )
    assert r.status_code == 200, r.text

    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=admin_headers,
        json={"gate": "manager", "approved": True},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=admin_headers,
        json={"gate": "director", "approved": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["budget"] == 500_000, "budget must become sample_cost + tirazh_cost"

    r = client.get("/api/dashboard/kpis", headers=admin_headers)
    assert r.json()["budget_spent"] >= 500_000

    r = client.get("/api/groups", headers=admin_headers)
    darling_group = next(g for g in r.json() if g["code"] == "A")
    assert darling_group["budget_spent"] >= 500_000
