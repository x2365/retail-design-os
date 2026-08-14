"""The 10-stage state machine: forward-by-one, revert, gated auto-advance,
the corner-only INSTALLATION skip, and the CLOSED preconditions (all
deliveries in, a payment exists, all approvals resolved)."""

from __future__ import annotations

from app import models
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def _create_task(client: TestClient, headers: dict[str, str], **overrides) -> str:
    payload = {
        "name": "gate",
        "brand": "Darling",
        "tt_total": 0,
        "brief_data": {"product_name": "gate"},
        "deadline": "2026-12-01",
        "launch": "2026-11-15",
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
        files={"file": ("d.png", b"\x89PNG\r\n\x1a\n", "image/png")},
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
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "kp", "stage": "4"},
        files={"file": ("kp.pdf", b"%PDF", "application/pdf")},
    )  # обязателен для выхода с этапа 4 — и авто-создаёт Payment
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


def _upload_shipment_docs(client: TestClient, headers: dict[str, str], code: str) -> None:
    """Накладная + реестр — both required to leave stage 7 (Отгрузка)."""
    client.post(
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "waybill", "stage": "7"},
        files={"file": ("waybill.pdf", b"%PDF", "application/pdf")},
    )
    client.post(
        f"/api/tasks/{code}/documents",
        headers=headers,
        data={"kind": "registry", "stage": "7"},
        files={"file": ("registry.pdf", b"%PDF", "application/pdf")},
    )


def _advance_through_all_gates(client: TestClient, headers: dict[str, str], code: str) -> None:
    _advance_to_shipping(client, headers, code)
    _upload_shipment_docs(client, headers, code)
    for s in range(8, 10):
        client.patch(f"/api/tasks/{code}", headers=headers, json={"stage": s})  # 7->8->9


def test_kp_approval_sets_budget_from_sample_and_tirazh_and_revoke_resets_it(
    client: TestClient, manager_headers: dict[str, str], admin_headers: dict[str, str]
):
    """task.budget is no longer hand-typed on the «Бюджет и КП» stage — it's
    computed as Образец+Тираж the moment both gates (Финансы/Бренд) are
    approved, and reset to 0 if either gets revoked (mirrors the stage
    auto-revert below: an unapproved КП has no locked-in budget)."""
    code = _create_task(client, manager_headers)
    _upload_brief(client, manager_headers, code)
    client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 2})
    client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "sketch", "stage": "2"},
        files={"file": ("d.png", b"\x89PNG\r\n\x1a\n", "image/png")},
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
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "kp", "stage": "4"},
        files={"file": ("kp.pdf", b"%PDF", "application/pdf")},
    )
    r = client.patch(
        f"/api/tasks/{code}",
        headers=admin_headers,  # money fields are admin-only
        json={"sample_cost": 150_000, "tirazh_cost": 250_000},
    )
    assert r.status_code == 200, r.text
    assert r.json()["budget"] == 0, "not approved yet — budget must stay 0"

    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=manager_headers,
        json={"gate": "manager", "approved": True},
    )
    assert r.json()["budget"] == 0, "only one of two gates approved — budget still 0"

    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=manager_headers,
        json={"gate": "director", "approved": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["budget"] == 400_000, "both gates approved — budget = sample_cost + tirazh_cost"

    r = client.post(
        f"/api/tasks/{code}/kp-approval",
        headers=manager_headers,
        json={"gate": "director", "approved": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["budget"] == 0, "revoking either gate must reset budget back to 0"


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
        files={"file": ("d.png", b"\x89PNG\r\n\x1a\n", "image/png")},
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
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "kp", "stage": "4"},
        files={"file": ("kp.pdf", b"%PDF", "application/pdf")},
    )  # обязателен для выхода с этапа 4
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
    client: TestClient, manager_headers: dict[str, str], db: Session
):
    code = _create_task(client, manager_headers)
    _advance_through_all_gates(client, manager_headers, code)

    # Uploading the КП file (now required to leave stage 4) auto-creates a
    # Payment row — delete it so this test can still exercise the close-gate
    # actually blocking on a genuinely missing Payment.
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    db.query(models.Payment).filter(models.Payment.task_id == task.id).delete()
    db.commit()

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
    r = client.post(
        f"/api/equipment/{eq_id}/produce",
        headers=headers,
        json={"deadline": "2026-12-01", "launch": "2026-11-15"},
    )
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
    _upload_shipment_docs(client, manager_headers, code)

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
    _upload_shipment_docs(client, manager_headers, code)

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 422, "corner equipment must not skip Монтаж"

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 8})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 8

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 9


def test_revoking_sample_approval_reverts_stage_back_to_sample(
    client: TestClient, manager_headers: dict[str, str]
):
    """Same rule as revoking a КП approval past stage 4 (see
    approve_kp/prep_approval): revoking a sample gate after the task has
    already moved on to Отгрузка must roll the card back to stage 6, or the
    board keeps showing it as past the sample stage despite the precondition
    (task.sample_approved_at = all three gates) no longer holding."""
    code = _produce_task(client, manager_headers, "stand")
    _advance_to_shipping(client, manager_headers, code)  # lands at stage 7, sample fully approved

    r = client.post(
        f"/api/tasks/{code}/sample-approval",
        headers=manager_headers,
        json={"gate": "brand", "approved": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 6, "revoking one sample gate must revert stage 7 -> 6"
    assert r.json()["sample_brand_approved"] is False

    r = client.get(f"/api/tasks/{code}", headers=manager_headers)
    assert r.json()["stage"] == 6, "revert must be persisted, not just in the response"


def test_shipment_stage_requires_waybill_and_registry(
    client: TestClient, manager_headers: dict[str, str]
):
    """Отгрузка (7) used to have no exit gate at all — "Далее" walked
    straight to Распределение (9, non-corner skips 8) without either
    shipping document, even though the stage's own DocumentList already
    displays both as a checklist. Both must now be uploaded first."""
    code = _produce_task(client, manager_headers, "stand")
    _advance_to_shipping(client, manager_headers, code)  # lands at stage 7

    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 422
    assert "накладная" in r.text and "реестр" in r.text

    client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "waybill", "stage": "7"},
        files={"file": ("waybill.pdf", b"%PDF", "application/pdf")},
    )
    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 422, "накладная alone must not be enough — реестр is still missing"

    client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "registry", "stage": "7"},
        files={"file": ("registry.pdf", b"%PDF", "application/pdf")},
    )
    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 9


def test_deleting_required_document_reverts_stage(
    client: TestClient, manager_headers: dict[str, str]
):
    """Same auto-revert rule as revoking an approval (see
    test_revoking_sample_approval_reverts_stage_back_to_sample), but for the
    document side: deleting the накладная that stage 7 required after the
    task has already advanced past it must roll the card back to 7, not
    leave it sitting on 9 with a now-unmet precondition."""
    code = _produce_task(client, manager_headers, "stand")
    _advance_to_shipping(client, manager_headers, code)  # lands at stage 7
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "waybill", "stage": "7"},
        files={"file": ("waybill.pdf", b"%PDF", "application/pdf")},
    )
    waybill_id = r.json()["id"]
    client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "registry", "stage": "7"},
        files={"file": ("registry.pdf", b"%PDF", "application/pdf")},
    )
    r = client.patch(f"/api/tasks/{code}", headers=manager_headers, json={"stage": 9})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == 9

    r = client.delete(f"/api/documents/{waybill_id}", headers=manager_headers)
    assert r.status_code == 204

    r = client.get(f"/api/tasks/{code}", headers=manager_headers)
    assert r.json()["stage"] == 7, "deleting the required накладная must revert stage 9 -> 7"
