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
