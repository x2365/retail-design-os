"""Helpers that turn ORM rows into API response payloads."""

from __future__ import annotations

import datetime as dt
import json

from . import models, schemas

_ZERO = {"tt_total": 0, "tt_ok": 0, "tt_partial": 0, "tt_miss": 0}


def _fmt_date(d: dt.date | None) -> str | None:
    return d.strftime("%d.%m.%y") if d else None


def _days_left(d: dt.date | None) -> int | None:
    if not d:
        return None
    end = d.date() if isinstance(d, dt.datetime) else d
    return (end - dt.date.today()).days


def stage_history_to_out(h: models.TaskStageHistory) -> schemas.StageHistoryOut:
    from .models import STAGE_LABELS, TaskStage

    def lbl(s):
        return STAGE_LABELS[TaskStage(s)] if s else None

    return schemas.StageHistoryOut(
        id=h.id,
        from_stage=h.from_stage,
        from_stage_label=lbl(h.from_stage),
        to_stage=h.to_stage,
        to_stage_label=lbl(h.to_stage),
        user=h.user.full_name if h.user else None,
        comment=h.comment,
        at=h.created_at.isoformat() if h.created_at else "",
    )


def task_to_out(task: models.Task, counts: dict | None = None) -> schemas.TaskOut:
    c = counts or _ZERO
    return schemas.TaskOut(
        code=task.code,
        name=task.name,
        brand=task.brand.name,
        group=task.brand.group.code,
        stage=task.stage,
        urgent=task.urgent,
        currency=task.currency,
        created_at=(task.created_at.isoformat() if task.created_at else None),
        production_cost=task.production_cost,
        budget=task.budget,
        sample_cost=task.sample_cost,
        tirazh_cost=task.tirazh_cost,
        prepaid=task.prepaid,
        tt_total=c["tt_total"],
        tt_ok=c["tt_ok"],
        tt_partial=c["tt_partial"],
        tt_miss=c["tt_miss"],
        days_left=task.days_left,
        progress_pct=task.progress_pct,
        stage_name=task.stage_name,
        stage_code=task.stage_code,
        deadline=_fmt_date(task.deadline_tt),
        launch=_fmt_date(task.launch_date),
        team=[m.name for m in task.members],
        team_detail=[
            {"name": m.name, "email": m.email or "", "telegram": m.telegram or ""}
            for m in task.members
        ],
        stage_approvals={str(r.stage): bool(r.approved) for r in task.stage_approval_rows},
        shipment_order_no=task.shipment_order_no or "",
        shipment_ship_date=_fmt_date(task.shipment_ship_date),
        shipment_acceptance_date=_fmt_date(task.shipment_acceptance_date),
        payment_status=task.payment_status or "unpaid",
        article=task.article or "",
        dimensions=task.dimensions or "",
        packaging_primary=task.packaging_primary or "",
        packaging_secondary=task.packaging_secondary or "",
        rc_arrival=_fmt_date(task.rc_arrival_date),
        brief_data=(json.loads(task.brief_data) if task.brief_data else {}),
        shk_data=(json.loads(task.shk_data) if task.shk_data else {}),
        stage_responsible=(json.loads(task.stage_responsible) if task.stage_responsible else {}),
        prep_brand_approved=bool(task.prep_brand_approved_at),
        prep_brand_by=task.prep_brand_approved_by or "",
        design_iteration=task.design_iteration or 1,
        prep_zya_approved=bool(task.prep_zya_approved_at),
        prep_zya_by=task.prep_zya_approved_by or "",
        kp_contractor=task.kp_contractor or "",
        kp_manager_approved=bool(task.kp_manager_approved_at),
        kp_manager_by=task.kp_manager_approved_by or "",
        kp_director_approved=bool(task.kp_director_approved_at),
        kp_director_by=task.kp_director_approved_by or "",
        kp_network_approved=bool(task.kp_network_approved_at),
        kp_network_by=task.kp_network_approved_by or "",
        sample_status=task.sample_status or "unpaid",
        sample_deadline=_fmt_date(task.sample_deadline),
        sample_received=bool(task.sample_received),
        sample_received_date=_fmt_date(task.sample_received_date),
        sample_qc_approved=bool(task.sample_qc_approved_at),
        sample_qc_by=task.sample_qc_approved_by or "",
        sample_brand_approved=bool(task.sample_brand_approved_at),
        sample_brand_by=task.sample_brand_approved_by or "",
        sample_network_approved=bool(task.sample_network_approved_at),
        sample_network_by=task.sample_network_approved_by or "",
        sample_approved=bool(task.sample_approved_at),
        sample_approved_by=task.sample_approved_by or "",
        production_end=_fmt_date(task.production_end_date),
        production_days_left=_days_left(task.production_end_date),
    )


def approval_to_out(a: models.Approval) -> dict:
    return {
        "id": a.id,
        "from_name": a.from_name,
        "role": a.role,
        "summary": a.summary,
        "type": a.type,
        "avatar": a.avatar,
        "color": a.color,
        "status": a.status.value,
        "comment": a.comment,
        "task": a.task.code if a.task else None,
    }


def _fmt_money_kop(kop: int | None, currency: str = "RUB") -> str:
    """Копейки → '1 234 ₽' (или '—' если пусто)."""
    if not kop:
        return "0 ₽" if kop == 0 else "—"
    sym = {"RUB": "₽", "USD": "$", "EUR": "€", "CNY": "¥"}.get(currency or "RUB", "₽")
    rub = round(kop / 100)
    return f"{rub:,}".replace(",", " ") + f" {sym}"


def payment_to_out(p: models.Payment) -> dict:
    t = p.task
    cur = p.currency or t.currency or "RUB"
    # источник истины по суммам — финансы задачи (вводятся на «Бюджет и КП»), в копейках
    sample = t.sample_cost or 0
    tirazh = t.tirazh_cost or 0
    prepaid = t.prepaid or 0
    total = t.budget or (sample + tirazh)
    balance = max(0, total - prepaid)
    # статус: ручной payment_status имеет приоритет, иначе — по фактическим цифрам
    ps = (t.payment_status or "").lower()
    PS_LABELS = {
        "registry": "Отправлен в реестр",
        "queued": "Заведён на оплату",
        "prepaid": "Предоплачен",
        "paid": "Оплачено",
    }
    if ps in PS_LABELS:
        status = PS_LABELS[ps]
    elif total > 0 and prepaid >= total:
        status = "Оплачено"
    elif prepaid > 0:
        status = "Предоплачен"
    else:
        status = "Ожидает оплаты"
    return {
        "id": t.code,
        "brand": t.brand.name,
        "name": t.name,
        "contractor": (t.kp_contractor or p.contractor or "—"),
        "kp_date": _fmt_date(p.kp_date),
        "sample": _fmt_money_kop(sample, cur),
        "tirazh": _fmt_money_kop(tirazh, cur),
        "prepaid": _fmt_money_kop(prepaid, cur),
        "balance": _fmt_money_kop(balance, cur),
        "currency": cur,
        "status": status,
    }


def task_to_tt(task: models.Task, counts: dict) -> dict:
    return {
        "task": task.code,
        "brand": task.brand.name,
        "name": task.name,
        "tt_total": counts["tt_total"],
        "tt_ok": counts["tt_ok"],
        "tt_partial": counts["tt_partial"],
        "tt_miss": counts["tt_miss"],
        "days_left": task.days_left,
    }


def delivery_to_out(d: models.Delivery) -> dict:
    from .models import SHIPMENT_REGION_LABELS

    return {
        "id": d.id,
        "task": d.task.code,
        "point_code": d.retail_point.code,
        "point_name": d.retail_point.name,
        "city": d.retail_point.city,
        "status": d.status.value,
        "region": d.region.value,
        "region_label": SHIPMENT_REGION_LABELS.get(d.region, d.region.value),
        "qty_expected": d.qty_expected,
        "qty_received": d.qty_received,
        "confirmed_at": d.confirmed_at.isoformat() if d.confirmed_at else None,
        "note": d.note,
        "installed_at": d.installed_at.isoformat() if d.installed_at else None,
        "installed_by": d.installed_by,
    }


def nomenclature_to_out(n: models.NomenclatureItem) -> dict:
    from .models import NOMENCLATURE_STATUS_LABELS

    return {
        "id": n.id,
        "task": n.task.code,
        "sku": n.sku,
        "barcode": n.barcode,
        "name": n.name,
        "qty": n.qty,
        "status": n.status.value,
        "status_label": NOMENCLATURE_STATUS_LABELS.get(n.status, n.status.value),
    }


def contractor_to_out(c: models.Contractor) -> dict:
    """Сериализует подрядчика, разбирая details (JSON-строку) в словарь."""
    details = {}
    if getattr(c, "details", None):
        try:
            details = json.loads(c.details)
        except Exception:
            details = {}
    return {
        "id": c.id,
        "name": c.name,
        "contact": c.contact or "",
        "details": details,
        "is_active": bool(c.is_active),
    }
