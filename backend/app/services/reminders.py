"""Движок напоминаний ответственным за этап.

Поток: build_due_notifications() считает «просроченные» по правилам и пишет
строки в notifications (идемпотентно через dedup_key) → dispatch_pending()
рассылает их по включённым каналам (email/telegram), иначе dry-run в лог.

Запуск: `python -m app.reminders` или POST /api/internal/run-reminders.
Расписание — внешний cron/launchd (надёжнее, чем in-process планировщик).
"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings

log = logging.getLogger("reminders")

# Карта «этап → роль ответственного» (подтверждено заказчиком).
STAGE_ROLE: dict[int, models.Role] = {
    1: models.Role.manager,  # ТЗ получено
    2: models.Role.manager,  # Эскизирование
    3: models.Role.brand,  # Согласование дизайна
    4: models.Role.manager,  # Подготовка к производству
    5: models.Role.manager,  # Производство
    6: models.Role.manager,  # Контроль качества
    7: models.Role.manager,  # Упаковка
    8: models.Role.shipment_manager,  # Готов к отгрузке
    9: models.Role.shipment_manager,  # Доставка
    10: models.Role.retailer,  # Монтаж
    11: models.Role.manager,  # Финальное согласование
    # 12 CLOSED — без напоминаний
}

# Пороги SLA (дни).
SLA_STAGE_STUCK_DAYS = 4  # этап без движения дольше — напомнить
SLA_DEADLINE_DAYS = 3  # до дедлайна осталось <= — напомнить
SLA_APPROVAL_PENDING_DAYS = 2  # согласование висит дольше — напомнить


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _as_utc(d: dt.datetime | None) -> dt.datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.UTC)


def _recipients(db: Session, role: models.Role) -> list[models.User]:
    return list(
        db.scalars(
            select(models.User).where(models.User.role == role, models.User.is_active.is_(True))
        ).all()
    )


def _stage_started_at(db: Session, task: models.Task) -> dt.datetime:
    """Когда начался текущий этап = время последнего перехода в него (или created_at)."""
    row = db.scalar(
        select(models.TaskStageHistory.created_at)
        .where(
            models.TaskStageHistory.task_id == task.id,
            models.TaskStageHistory.to_stage == task.stage,
        )
        .order_by(models.TaskStageHistory.id.desc())
        .limit(1)
    )
    return _as_utc(row) or _as_utc(task.created_at) or _now()


def _add(db: Session, *, user_id, task_id, stage, rule, message, dedup_key) -> bool:
    """Создать уведомление, если такого (dedup_key) ещё нет. True — создано."""
    exists = db.scalar(
        select(func.count())
        .select_from(models.Notification)
        .where(models.Notification.dedup_key == dedup_key)
    )
    if exists:
        return False
    db.add(
        models.Notification(
            user_id=user_id,
            task_id=task_id,
            stage=stage,
            rule=rule,
            message=message,
            dedup_key=dedup_key,
            status="pending",
        )
    )
    return True


def build_due_notifications(db: Session, now: dt.datetime | None = None) -> int:
    """Просканировать открытые задачи и согласования, создать напоминания.
    Возвращает число созданных строк (идемпотентно по дням)."""
    now = now or _now()
    day = now.date().isoformat()
    created = 0

    open_tasks = list(
        db.scalars(select(models.Task).where(models.Task.stage < models.LAST_STAGE)).all()
    )

    for t in open_tasks:
        role = STAGE_ROLE.get(t.stage)
        recipients = _recipients(db, role) if role else []
        label = models.STAGE_LABELS.get(models.TaskStage(t.stage), str(t.stage))

        # 1) этап завис
        age_days = (now - _stage_started_at(db, t)).days
        if age_days > SLA_STAGE_STUCK_DAYS and recipients:
            for u in recipients:
                msg = (
                    f"Задача {t.code}: этап «{label}» без движения {age_days} дн. "
                    f"(SLA {SLA_STAGE_STUCK_DAYS})."
                )
                if _add(
                    db,
                    user_id=u.id,
                    task_id=t.id,
                    stage=t.stage,
                    rule="stage_stuck",
                    message=msg,
                    dedup_key=f"stage_stuck:{t.id}:{t.stage}:{u.id}:{day}",
                ):
                    created += 1

        # 2) дедлайн близко/просрочен
        dl = _as_utc(t.deadline_tt)
        if dl and recipients:
            days_left = (dl.date() - now.date()).days
            if days_left <= SLA_DEADLINE_DAYS:
                when = (
                    f"через {days_left} дн." if days_left >= 0 else f"просрочен на {-days_left} дн."
                )
                for u in recipients:
                    msg = f"Задача {t.code}: дедлайн ТТ {dl.date().isoformat()} — {when}"
                    if _add(
                        db,
                        user_id=u.id,
                        task_id=t.id,
                        stage=t.stage,
                        rule="deadline",
                        message=msg,
                        dedup_key=f"deadline:{t.id}:{u.id}:{day}",
                    ):
                        created += 1

    # 3) согласования висят (pending дольше порога) → менеджерам
    pend = list(
        db.scalars(
            select(models.Approval).where(models.Approval.status == models.ApprovalStatus.pending)
        ).all()
    )
    managers = _recipients(db, models.Role.manager)
    for a in pend:
        age = (now - (_as_utc(a.created_at) or now)).days
        if age > SLA_APPROVAL_PENDING_DAYS and managers:
            code = a.task.code if a.task else "—"
            for u in managers:
                msg = f"Согласование «{a.type}» по {code} ждёт {age} дн."
                if _add(
                    db,
                    user_id=u.id,
                    task_id=(a.task.id if a.task else None),
                    stage=None,
                    rule="approval_pending",
                    message=msg,
                    dedup_key=f"approval_pending:{a.id}:{u.id}:{day}",
                ):
                    created += 1

    db.commit()
    return created


# ---- каналы доставки -------------------------------------------------------
def _send_email(to: str, text: str) -> bool:
    s = get_settings()
    if not s.email_enabled or not to:
        return False
    import smtplib
    from email.mime.text import MIMEText

    m = MIMEText(text, _charset="utf-8")
    m["Subject"] = "RetailDesign OS — напоминание"
    m["From"] = s.smtp_from
    m["To"] = to
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as srv:
        if s.smtp_tls:
            srv.starttls()
        if s.smtp_user:
            srv.login(s.smtp_user, s.smtp_password)
        srv.sendmail(s.smtp_from, [to], m.as_string())
    return True


def _send_telegram(chat_id: str, text: str) -> bool:
    s = get_settings()
    if not s.telegram_enabled or not chat_id:
        return False
    import urllib.parse
    import urllib.request

    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200


def dispatch_pending(db: Session, dry_run: bool | None = None) -> dict:
    """Разослать pending-уведомления по включённым каналам.

    Если каналы не сконфигурированы или dry_run=True — только лог (status=sent,
    channels='log'), чтобы движок был тестируем без реальной инфраструктуры.
    """
    s = get_settings()
    if dry_run is None:
        dry_run = not (s.email_enabled or s.telegram_enabled)

    rows = list(
        db.scalars(select(models.Notification).where(models.Notification.status == "pending")).all()
    )
    sent = failed = 0
    for n in rows:
        channels: list[str] = []
        ok_any = False
        try:
            if dry_run:
                log.info("[reminder dry-run] user=%s %s", n.user_id, n.message)
                channels.append("log")
                ok_any = True
            else:
                u = n.user
                if s.telegram_enabled and u and u.telegram_chat_id:
                    if _send_telegram(u.telegram_chat_id, n.message):
                        channels.append("telegram")
                        ok_any = True
                if s.email_enabled and u and u.email:
                    if _send_email(u.email, n.message):
                        channels.append("email")
                        ok_any = True
                if not ok_any:  # некому/нечем слать — фиксируем в лог
                    log.info("[reminder no-channel] user=%s %s", n.user_id, n.message)
                    channels.append("log")
                    ok_any = True
            n.channels = ",".join(channels)
            n.status = "sent" if ok_any else "failed"
            n.sent_at = _now() if ok_any else None
            sent += 1 if ok_any else 0
            failed += 0 if ok_any else 1
        except Exception as e:  # доставка не должна валить весь обход
            log.warning("reminder dispatch failed id=%s: %s", n.id, e)
            n.status = "failed"
            failed += 1
    db.commit()
    return {"dispatched": sent, "failed": failed, "dry_run": dry_run}


def run_reminders(db: Session, dry_run: bool | None = None) -> dict:
    created = build_due_notifications(db)
    disp = dispatch_pending(db, dry_run=dry_run)
    return {"created": created, **disp}
