"""Машина переходов между этапами Task (BUSINESS_RULES §2).

Правила (согласовано):
- Вперёд — только на следующий этап (current + 1). Перескок запрещён — с
  одним исключением: этап INSTALLATION ("Монтаж") применяется только к
  corner-оборудованию, и для остальных задач перепрыгивается автоматически
  (см. `_wants_install`/`validate_transition`).
- Назад — на любой предыдущий этап (revert разрешён), включая пропущенный
  INSTALLATION — это осознанно не блокируется, чтобы менеджер мог откатить
  ошибку на любой шаг назад без спецкейсов.
- Предусловия этапа CLOSED (все Deliveries=DELIVERED, есть Payment, все
  обязательные Approvals) проверяются в `check_close_preconditions` и
  применяются в `apply_transition` при переходе на CLOSED.

Слой services не лезет в HTTP — бросает ValueError, роутер транслирует в 4xx.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import (
    Delivery,
    DeliveryStatus,
    Payment,
    TaskStage,
    TaskStageHistory,
)

FIRST = int(TaskStage.BRIEF_RECEIVED)
LAST = int(TaskStage.CLOSED)
INSTALL_STAGE = int(TaskStage.INSTALLATION)


def label(stage: int) -> str:
    from ..models import STAGE_LABELS

    return STAGE_LABELS[TaskStage(stage)]


def validate_stage_value(stage: int) -> TaskStage:
    if stage not in (s.value for s in TaskStage):
        raise ValueError(f"Недопустимый этап {stage}; допустимо {FIRST}..{LAST}")
    return TaskStage(stage)


def _wants_install(task) -> bool:
    """Монтаж применяется только к corner-оборудованию. Задачи без привязки
    к изделию (equipment_id пуст) по умолчанию считаются требующими монтаж —
    скрываем/пропускаем этап только когда точно знаем, что изделие не corner."""
    kind = task.equipment.kind if task.equipment else None
    return kind is None or kind == "corner"


def validate_transition(current: int, target: int, *, task=None) -> None:
    """Разрешает: target == current (no-op), target == current+1 (вперёд на 1),
    target < current (возврат, любая дистанция). Запрещает: перескок вперёд
    > 1 этап — с исключением: не-corner задача на этапе current==INSTALL_STAGE-1
    может перепрыгнуть сразу на INSTALL_STAGE+1, минуя "Монтаж". Явный target
    == INSTALL_STAGE для не-corner задачи отклоняется отдельно."""
    validate_stage_value(current)
    validate_stage_value(target)
    if target == current:
        return
    if target > current:
        skip_install = (
            task is not None
            and current == INSTALL_STAGE - 1
            and target == INSTALL_STAGE + 1
            and not _wants_install(task)
        )
        if skip_install:
            return
        if target == INSTALL_STAGE and task is not None and not _wants_install(task):
            kind = task.equipment.kind if task.equipment else "—"
            raise ValueError(
                f"Этап «{label(INSTALL_STAGE)}» не применяется к изделию типа «{kind}» "
                "(только corner). Перейдите сразу на «Распределение по ТТ»."
            )
        if target != current + 1:
            raise ValueError(
                f"Нельзя перескочить с этапа {current} ({label(current)}) сразу на "
                f"{target} ({label(target)}). Двигайтесь последовательно (по одному)."
            )
    # target == current+1 (вперёд) или target < current (возврат) — разрешено.


def next_stage(current: int, task=None) -> int:
    """Следующий этап (для автоперехода после согласования). Не выходит за
    LAST; пропускает INSTALL_STAGE для не-corner задач."""
    n = min(current + 1, LAST)
    if n == INSTALL_STAGE and task is not None and not _wants_install(task):
        n = min(n + 1, LAST)
    return n


def record_transition(
    db: Session,
    *,
    task_id: int,
    from_stage: int | None,
    to_stage: int,
    user_id: int | None = None,
    comment: str | None = None,
) -> None:
    """Пишет одну запись в лог переходов. Коммит — на вызывающем коде."""
    db.add(
        TaskStageHistory(
            task_id=task_id,
            from_stage=from_stage,
            to_stage=to_stage,
            user_id=user_id,
            comment=comment,
        )
    )


def check_stage_preconditions(db: Session, task, stage: int) -> list[str]:
    """Предусловия ВЫХОДА с этапа `stage` (внутренние согласования карточки).

    Возвращает список невыполненных условий (пустой = можно двигаться дальше).
    Применяется только при движении вперёд; возврат назад не блокируется.
    Этап CLOSED проверяется отдельно в check_close_preconditions.
    """
    import json as _json

    from sqlalchemy import func
    from sqlalchemy import select as _select

    from ..models import DocKind, Document

    def has_doc(*kinds) -> bool:
        return bool(
            db.scalar(
                _select(func.count())
                .select_from(Document)
                .where(Document.task_id == task.id, Document.kind.in_(list(kinds)))
            )
        )

    reasons: list[str] = []
    s = int(stage)

    if s == 1:  # ТЗ получено → нужно заполненное ТЗ и загруженный файл ТЗ
        brief: dict = {}
        try:
            brief = _json.loads(task.brief_data) if task.brief_data else {}
        except Exception:
            brief = {}
        if not (brief.get("product_name") or task.name):
            reasons.append("не заполнено ТЗ (укажите хотя бы название продукта)")
        if not has_doc(DocKind.brief):
            reasons.append("не загружен файл ТЗ")
        if not task.deadline_tt:
            reasons.append("не указана дата отгрузки в ТТ")
        if not task.launch_date:
            reasons.append("не указана дата предполагаемого лонча")
    elif s == 2:  # Разработка дизайна → нужен загруженный дизайн
        if not has_doc(DocKind.sketch, DocKind.model3d, DocKind.photo):
            reasons.append("не загружен файл дизайна")
    elif s == 3:  # Согласования → согласование бренда + сети
        if not task.prep_brand_approved_at:
            reasons.append("нет согласования бренда")
        if not task.prep_zya_approved_at:
            reasons.append("нет согласования сети")
    elif s == 4:  # Бюджет и КП → загружен файл КП + согласование финансы + бренд
        # Согласование сети на этом этапе не требуется — оно уже получено
        # раньше, на этапе 3 «Согласования» (prep_zya); дублировать его
        # здесь было ошибкой.
        # Файл КП обязателен: именно его загрузка автосоздаёт Payment
        # (см. routers/documents.py) — без него согласования можно было
        # проставить вручную, задача уходила дальше, а Payment так и не
        # появлялся, и это вскрывалось только на закрытии ("нет оплаты").
        if not has_doc(DocKind.kp):
            reasons.append("не загружен файл КП")
        if not task.kp_manager_approved_at:
            reasons.append("нет согласования финансов")
        if not task.kp_director_approved_at:
            reasons.append("нет согласования бренда")
    elif s == 5:  # Документы → загружены ДС и счёт
        if not has_doc(DocKind.ds):
            reasons.append("не загружено ДС")
        if not has_doc(DocKind.invoice):
            reasons.append("не загружен счёт")
    elif s == 6:  # Образец и Производство → образец утверждён
        if not task.sample_approved_at:
            reasons.append("образец не утверждён")
    elif s == 7:  # Отгрузка → загружены накладная и реестр
        if not has_doc(DocKind.waybill):
            reasons.append("не загружена накладная")
        if not has_doc(DocKind.registry):
            reasons.append("не загружен реестр")
    # этапы 8 (Монтаж), 9 (Распределение) — без жёстких внутренних гейтов
    # на этом шаге
    return reasons


def check_close_preconditions(db: Session, task) -> list[str]:
    """Предусловия закрытия задачи (этап CLOSED): все поставки доставлены +
    есть оплата. Возвращает список невыполненных условий (пустой = можно
    закрывать).

    Согласования (бренд/сеть/финансы/КК) здесь НЕ проверяются отдельно — это
    уже сделано `check_stage_preconditions` на выходе с этапов 3/5/7:
    задача физически не может дойти до 12, не пройдя через них. Отдельная
    таблица `Approval` (общая, не 1:1 с задачей) — это другой, отдельный
    объект («ОЖИДАЮТ РЕШЕНИЯ» inbox), в неё никогда не пишутся строки,
    привязанные к конкретной задаче, так что проверка "все approved" по ней
    была вечно пустой и ничего не проверяла.
    """
    from sqlalchemy import func
    from sqlalchemy import select as _select

    reasons: list[str] = []

    not_delivered = db.scalar(
        _select(func.count())
        .select_from(Delivery)
        .where(Delivery.task_id == task.id, Delivery.status != DeliveryStatus.delivered)
    )
    if not_delivered:
        reasons.append(f"не все ТТ доставлены (не доставлено: {not_delivered})")

    has_payment = db.scalar(
        _select(func.count()).select_from(Payment).where(Payment.task_id == task.id)
    )
    if not has_payment:
        reasons.append("нет оплаты (Payment)")

    return reasons


def apply_transition(
    db: Session,
    task,
    target: int,
    *,
    user_id: int | None = None,
    comment: str | None = None,
) -> None:
    """Валидирует переход, логирует его и выставляет task.stage.

    Бросает ValueError при недопустимом переходе (роутер транслирует в 4xx).
    Переход на CLOSED дополнительно проверяет предусловия закрытия.
    No-op, если target == текущему этапу.
    """
    validate_transition(task.stage, target, task=task)
    if target == task.stage:
        return
    # Движение вперёд — проверяем внутренние согласования покидаемого этапа.
    if target > task.stage:
        pre = check_stage_preconditions(db, task, task.stage)
        if pre:
            raise ValueError(f"Этап «{label(task.stage)}» не завершён: " + "; ".join(pre) + ".")
    if target == LAST:
        reasons = check_close_preconditions(db, task)
        if reasons:
            raise ValueError("Нельзя закрыть задачу: " + "; ".join(reasons) + ".")
    record_transition(
        db,
        task_id=task.id,
        from_stage=task.stage,
        to_stage=target,
        user_id=user_id,
        comment=comment,
    )
    task.stage = target


def record_creation(db: Session, task, *, user_id: int | None = None) -> None:
    """Исходная запись истории при создании задачи (from_stage = NULL)."""
    record_transition(
        db,
        task_id=task.id,
        from_stage=None,
        to_stage=task.stage,
        user_id=user_id,
        comment="создание задачи",
    )
