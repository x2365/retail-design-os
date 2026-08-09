"""The 10-stage state machine: forward-by-one, revert, gated auto-advance,
the corner-only INSTALLATION skip, and the CLOSED preconditions (all
deliveries in, a payment exists, all approvals resolved)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_task(client: TestClient, headers: dict[str, str], **overrides) -> str:
    payload = {
        "name": "gate",
        "brand": "Darling",
        "tt_total": 0,
        "brief_data": {"product_name": "gate"},
    }
    payload.update(overrides)
    r = client.post("/api/tasks", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["code"]


def _upload_brief(client: TestClient, headers: dict[str, str], code: str) -> None:
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "brief", "stage": "1"},
        files={"file": ("brief.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 201, r.text


def test_stage_advances_by_one_but_not_by_skip(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 2})
    assert r.status_code == 422, "should be blocked without an uploaded ТЗ file"

    _upload_brief(client, manager_headers, code)
    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 2})
    assert r.status_code == 200
    assert r.json()["stage"] == 2

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 4})
    assert r.status_code == 422


def test_shipment_fields_are_saved(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.patch(
        f"/api/tasks/{code}",
        headers=manager_headers,
        json={"shipment_order_no": "ORD-1", "shipment_ship_date": "2026-07-01"},
    )
    assert r.status_code == 200
    assert r.json()["shipment_order_no"] == "ORD-1"


def test_waybill_upload_gets_russian_kind_label(
    client: TestClient, manager_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "waybill", "stage": "2"},
        files={"file": ("n.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["kind_label"] == "Накладная"


def _advance_to_shipping(client: TestClient, headers: dict[str, str], code: str) -> None:
    """Walks a task through gates 1-6, landing it at stage 7 ("Отгрузка"),
    the first ungated stage — shared by the corner-skip tests and the
    full close-out flow below."""
    _upload_brief(client, headers, code)
    client.patch(f"/api/tasks/{code}", headers=headers, json={"stage": 2})  # 1->2 (ТЗ заполнено)
    client.post(
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "sketch", "stage": "2"},
        files={"file": ("d.png", b"x", "image/png")},
    )
    client.patch(f"/api/tasks/{code}", headers=headers, json={"stage": 3})  # 2->3 (есть дизайн)
    client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=headers,
        json={"gate": "brand", "approved": True},
    )
    client.post(
        f"/api/tasks/{code}/prep-approval", headers=headers, json={"gate": "zya", "approved": True}
    )  # авто 3->4 (Бюджет и КП)
    client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=headers,
        json={"gate": "manager", "approved": True},
    )
    client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=headers,
        json={"gate": "director", "approved": True},
    )
    client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=headers,
        json={"gate": "network", "approved": True},
    )  # авто 4->5 (Документы)
    client.post(
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "ds", "stage": "5"},
        files={"file": ("ds.pdf", b"%PDF", "application/pdf")},
    )
    client.post(
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "invoice", "stage": "5"},
        files={"file": ("inv.pdf", b"%PDF", "application/pdf")},
    )
    client.patch(f"/api/tasks/{code}", headers=headers, json={"stage": 6})  # 5->6 (ДС+счёт)
    client.post(f"/api/tasks/{code}/sample-approval", headers=headers, json={"approved": True})
    client.patch(f"/api/tasks/{code}", headers=headers, json={"stage": 7})  # 6->7 (образец)


def _advance_through_all_gates(client: TestClient, headers: dict[str, str], code: str) -> None:
    _advance_to_shipping(client, headers, code)
    for s in range(8, 10):
        client.patch(f"/api/tasks/{code}", headers=headers, json={"stage": s})  # 7->8->9


def test_kp_stage_auto_advances_without_network_approval(
    client: TestClient, manager_headers: dict[str, str]
):
    """Network approval belongs to stage 3 (prep_zya) — requiring it again on
    stage 4 (kp_network) was a duplicated, removed gate. manager+director
    alone must both unblock the manual "Далее" transition and trigger the
    stage 4->5 auto-advance."""
    code = _create_task(client, manager_headers)
    _upload_brief(client, manager_headers, code)
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
        headers=manager_headers,
        json={"gate": "brand", "approved": True},
    )
    client.post(
        f"/api/tasks/{code}/prep-approval",
        headers=manager_headers,
        json={"gate": "zya", "approved": True},
    )  # авто 3->4 (Бюджет и КП)

    client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=manager_headers,
        json={"gate": "manager", "approved": True},
    )
    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=manager_headers,
        json={"gate": "director", "approved": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 5, "should auto-advance to stage 5 without a network approval"


def test_closing_without_payment_is_blocked_with_reasons(
    client: TestClient, manager_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    _advance_through_all_gates(client, manager_headers, code)

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 10})
    assert r.status_code == 422

    r = client.get(f"/api/tasks/{code}", headers=manager_headers)
    assert r.json()["stage"] == 9

    r = client.patch(
        f"/api/tasks/{code}/stage-approval",
        headers=manager_headers,
        json={"stage": 9, "approved": True},
    ).json()
    assert r["stage"] == 9
    assert len(r.get("blocked_reasons", [])) > 0


def _produce_task(client: TestClient, headers: dict[str, str], kind: str) -> str:
    """Creates an Equipment(kind=kind) and produces a task from it, so
    task.equipment.kind is set (unlike _create_task, which leaves
    equipment_id unset)."""
    r = client.post(
        "/api/equipment",
        headers=headers,
        json={"brand": "Darling", "name": "Тестовое изделие", "kind": kind},
    )
    assert r.status_code == 201, r.text
    eq_id = r.json()["id"]
    r = client.post(f"/api/equipment/{eq_id}/produce", headers=headers, json={})
    assert r.status_code == 201, r.text
    return r.json()["code"]


def test_install_stage_skipped_for_non_corner_equipment(
    client: TestClient, manager_headers: dict[str, str]
):
    """A non-corner task jumps 7->9 in one PATCH, skipping "Монтаж" (8); an
    explicit target of 8 is rejected; reverting 9->7 still works (revert is
    never blocked, even onto/over a skipped stage)."""
    code = _produce_task(client, manager_headers, "stand")
    _advance_to_shipping(client, manager_headers, code)  # lands at stage 7

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 8})
    assert r.status_code == 422, "Монтаж must not be settable for non-corner equipment"

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 9, "should skip straight over 8"

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 7})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 7, "revert is never blocked, even back past a skipped stage"


def test_install_stage_required_for_corner_equipment(
    client: TestClient, manager_headers: dict[str, str]
):
    """A corner-equipment task must pass through stage 8 — skipping it
    straight from 7 to 9 is rejected like any other multi-step skip."""
    code = _produce_task(client, manager_headers, "corner")
    _advance_to_shipping(client, manager_headers, code)  # lands at stage 7

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 422, "corner equipment must not skip Монтаж"

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 8})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 8

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 9
