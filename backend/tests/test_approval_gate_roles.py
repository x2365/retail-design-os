"""Each approval gate (prep-/kp-/sample-approval) has a real-world owner —
brand rep, retail-chain rep, or the manager/admin running the pipeline. Before
this, all three endpoints were manager/admin-only, so the "brand" and
"retailer" roles — despite existing and being documented as "view +
approvals" — couldn't actually approve anything."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_task(client: TestClient, headers: dict[str, str], **overrides) -> str:
    payload = {"name": "gate-role", "brand": "Darling", "brief_data": {"product_name": "x"}}
    payload.update(overrides)
    r = client.post("/api/tasks", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["code"]


def test_brand_role_can_approve_its_own_gates(
    client: TestClient, manager_headers: dict[str, str], brand_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)

    r = client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=brand_headers,
        json={"gate": "brand", "approved": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["prep_brand_approved"] is True

    # not their gate
    r = client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=brand_headers,
        json={"gate": "zya", "approved": True},
    )
    assert r.status_code == 403


def test_retailer_role_can_approve_its_own_gates(
    client: TestClient, manager_headers: dict[str, str], retailer_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)

    r = client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=retailer_headers,
        json={"gate": "zya", "approved": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["prep_zya_approved"] is True

    r = client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=retailer_headers,
        json={"gate": "brand", "approved": True},
    )
    assert r.status_code == 403


def test_brand_and_retailer_together_trigger_prep_auto_advance(
    client: TestClient,
    manager_headers: dict[str, str],
    brand_headers: dict[str, str],
    retailer_headers: dict[str, str],
):
    """Auto-advance out of stage 3 shouldn't care who set each gate."""
    code = _create_task(client, manager_headers)
    client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "brief", "stage": "1"},
        files={"file": ("brief.pdf", b"%PDF", "application/pdf")},
    )
    client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 2})
    client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "sketch", "stage": "2"},
        files={"file": ("d.png", b"x", "image/png")},
    )
    client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 3})

    client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=brand_headers,
        json={"gate": "brand", "approved": True},
    )
    r = client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=retailer_headers,
        json={"gate": "zya", "approved": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 4


def test_kp_director_gate_is_the_brand_role(
    client: TestClient, manager_headers: dict[str, str], brand_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=brand_headers,
        json={"gate": "director", "approved": True},
    )
    assert r.status_code == 200, r.text

    # finance gate is not theirs
    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=brand_headers,
        json={"gate": "manager", "approved": True},
    )
    assert r.status_code == 403


def test_sample_legacy_approve_all_is_manager_only(
    client: TestClient,
    manager_headers: dict[str, str],
    brand_headers: dict[str, str],
    retailer_headers: dict[str, str],
):
    code = _create_task(client, manager_headers)

    r = client.post(f"/api/tasks/{code}/sample-approval", headers=brand_headers, json={})
    assert r.status_code == 403

    r = client.post(f"/api/tasks/{code}/sample-approval", headers=manager_headers, json={})
    assert r.status_code == 200


def test_viewer_cannot_approve_anything(client: TestClient, manager_headers, viewer_headers):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=viewer_headers,
        json={"gate": "brand", "approved": True},
    )
    assert r.status_code == 403
