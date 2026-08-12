"""Document management: upload / list / download / delete files per task.

Files get a uuid-based storage name to avoid collisions and path-traversal;
the original filename is kept in the DB for display. Actual bytes go through
app.storage (local disk for dev/tests, Cloudflare R2 in production — see
that module for why local disk alone isn't safe to rely on in production).
"""

from __future__ import annotations

import os
import re
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas, security
from ..config import get_settings
from ..database import get_db
from ..rate_limit import limiter
from ..services import audit
from ..storage import storage

router = APIRouter(tags=["documents"])
settings = get_settings()

ReadDep = Depends(security.get_current_user)
WriteDep = Depends(security.require_roles(models.Role.manager))

# Whitelist of allowed file types (defence against uploading executable/script
# content). Extensions are checked case-insensitively.
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".ppt",
    ".pptx",
    ".stl",
    ".obj",
    ".step",
    ".stp",
    ".3mf",
    ".skp",
    ".dwg",
    ".ai",
    ".psd",
    ".eps",
    ".zip",
    ".rar",
    ".7z",
    ".txt",
}
SAFE_EXT_RE = re.compile(r"[^a-z0-9]")

# Magic-byte signatures for the types a browser renders inline (images, PDF) —
# where a spoofed extension is an actual XSS/content-confusion vector. CAD /
# office / archive formats stay extension-only: browsers don't render them,
# so the risk is far lower and real content-sniffing for those is a separate,
# bigger effort (antivirus-style scanning), not attempted here.
_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "pdf": (b"%PDF",),
}


def _content_matches_extension(ext: str, data: bytes) -> bool:
    if ext == "svg":
        # Text format, no magic bytes — block the concrete XSS vector instead.
        return "<script" not in data[:4096].decode("utf-8", errors="ignore").lower()
    if ext == "webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    sigs = _MAGIC_SIGNATURES.get(ext)
    return True if not sigs else any(data.startswith(sig) for sig in sigs)


def _sanitize_filename(name: str) -> str:
    # Strip any path components and control characters; cap length.
    base = os.path.basename(name or "").replace("\x00", "").strip()
    base = "".join(ch for ch in base if ch.isprintable())
    return (base or "file")[:255]


def _safe_ext(filename: str) -> str:
    # Returns the extension WITHOUT the leading dot, lowercased, alnum only.
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    return SAFE_EXT_RE.sub("", ext)[:10]


KIND_LABELS = {
    models.DocKind.brief: "ТЗ бренда",
    models.DocKind.kp: "КП подрядчика",
    models.DocKind.sketch: "Эскизы",
    models.DocKind.model3d: "3D-модель",
    models.DocKind.photo: "Фото продукта",
    models.DocKind.nomenclature: "Номенклатура / ШК",
    models.DocKind.layout: "Раскладка ШК",
    models.DocKind.ds: "ДС",
    models.DocKind.invoice: "Счёт",
    models.DocKind.waybill: "Накладная",
    models.DocKind.registry: "Реестр",
    models.DocKind.planogram: "Планограмма",
    models.DocKind.other: "Документ",
}


def _to_out(d: models.Document) -> dict:
    return {
        "id": d.id,
        "task": d.task.code if d.task else None,
        "equipment_id": d.equipment_id,
        "kind": d.kind.value,
        "kind_label": KIND_LABELS.get(d.kind, "Документ"),
        "stage": d.stage,
        "filename": d.filename,
        "content_type": d.content_type,
        "size": d.size,
        "uploaded_by": d.uploaded_by.full_name if d.uploaded_by else None,
        "created_at": d.created_at.isoformat() if d.created_at else "",
        "download_url": f"{settings.api_prefix}/documents/{d.id}/download",
    }


def _validate_and_store(file: UploadFile, data: bytes, kind: str):
    """Общая валидация типа/размера/имени + сохранение в storage. Возвращает
    (doc_kind, clean_name, storage_name)."""
    try:
        doc_kind = models.DocKind(kind)
    except ValueError as exc:
        raise HTTPException(422, f"Invalid kind '{kind}'") from exc
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) == 0:
        raise HTTPException(422, "Пустой файл")
    if len(data) > max_bytes:
        raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ")
    clean_name = _sanitize_filename(file.filename or "")
    ext = _safe_ext(clean_name)
    if ("." + ext) not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(e.lstrip(".") for e in ALLOWED_EXTENSIONS))
        raise HTTPException(415, f"Недопустимый тип файла. Разрешены: {allowed}")
    if not _content_matches_extension(ext, data):
        raise HTTPException(415, "Содержимое файла не соответствует расширению")
    storage_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    storage.save(storage_name, data, file.content_type or "application/octet-stream")
    return doc_kind, clean_name, storage_name


async def _read_limited(file: UploadFile) -> bytes:
    """Reads the upload in chunks, aborting as soon as the size cap is
    exceeded — avoids buffering an oversized body fully into memory before
    _validate_and_store's own size check ever runs."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ")
        chunks.append(chunk)
    return b"".join(chunks)


def _reload_doc(db: Session, doc_id: int) -> models.Document:
    doc = db.scalar(
        select(models.Document)
        .options(
            selectinload(models.Document.task),
            selectinload(models.Document.uploaded_by),
        )
        .where(models.Document.id == doc_id)
    )
    assert doc is not None
    return doc


def _get_task(db: Session, code: str) -> models.Task:
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    return task


@router.get("/tasks/{code}/documents", response_model=list[schemas.DocumentOut])
def list_documents(
    code: str, stage: int | None = None, db: Session = Depends(get_db), _user: models.User = ReadDep
):
    task = _get_task(db, code)
    stmt = (
        select(models.Document)
        .options(selectinload(models.Document.task), selectinload(models.Document.uploaded_by))
        .where(models.Document.task_id == task.id)
    )
    if stage is not None:
        stmt = stmt.where(models.Document.stage == stage)
    rows = db.scalars(stmt.order_by(models.Document.id.desc())).all()
    return [_to_out(d) for d in rows]


@router.post("/tasks/{code}/documents", response_model=schemas.DocumentOut, status_code=201)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    code: str,
    file: UploadFile = File(...),
    kind: str = Form("other"),
    stage: int | None = Form(None),
    db: Session = Depends(get_db),
    user: models.User = WriteDep,
):
    task = _get_task(db, code)
    if stage is not None and not (models.FIRST_STAGE <= stage <= models.LAST_STAGE):
        raise HTTPException(422, f"stage must be {models.FIRST_STAGE}..{models.LAST_STAGE}")
    data = await _read_limited(file)
    doc_kind, clean_name, storage_name = _validate_and_store(file, data, kind)
    doc = models.Document(
        task_id=task.id,
        kind=doc_kind,
        stage=stage,
        filename=clean_name,
        storage_name=storage_name,
        content_type=file.content_type or "application/octet-stream",
        size=len(data),
        uploaded_by_id=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    # КП-файл (kind=kp) — поступление КП. Если по задаче ещё нет записи об оплате,
    # создаём её; «Дату КП» подтягиваем из даты загрузки файла.
    if doc_kind == models.DocKind.kp:
        existing = db.scalar(select(models.Payment).where(models.Payment.task_id == task.id))
        if existing is None:
            db.add(
                models.Payment(
                    task_id=task.id, contractor="", kp_date=doc.created_at, status="Ожидает оплаты"
                )
            )
            db.commit()
        elif not existing.kp_date:
            existing.kp_date = doc.created_at
            db.commit()
    return _to_out(_reload_doc(db, doc.id))


# ---- library-card files (полные файлы проекта) ----------------------------
@router.get("/equipment/{eq_id}/documents", response_model=list[schemas.DocumentOut])
def list_card_documents(eq_id: int, db: Session = Depends(get_db), _user: models.User = ReadDep):
    card = db.get(models.Equipment, eq_id)
    if not card:
        raise HTTPException(404, "Карточка не найдена")
    rows = db.scalars(
        select(models.Document)
        .options(selectinload(models.Document.uploaded_by))
        .where(models.Document.equipment_id == eq_id)
        .order_by(models.Document.id.desc())
    ).all()
    return [_to_out(d) for d in rows]


@router.post("/equipment/{eq_id}/documents", response_model=schemas.DocumentOut, status_code=201)
@limiter.limit("20/minute")
async def upload_card_document(
    request: Request,
    eq_id: int,
    file: UploadFile = File(...),
    kind: str = Form("other"),
    db: Session = Depends(get_db),
    user: models.User = WriteDep,
):
    card = db.get(models.Equipment, eq_id)
    if not card:
        raise HTTPException(404, "Карточка не найдена")
    data = await _read_limited(file)
    doc_kind, clean_name, storage_name = _validate_and_store(file, data, kind)
    doc = models.Document(
        equipment_id=card.id,
        kind=doc_kind,
        filename=clean_name,
        storage_name=storage_name,
        content_type=file.content_type or "application/octet-stream",
        size=len(data),
        uploaded_by_id=user.id,
    )
    db.add(doc)
    db.commit()
    return _to_out(_reload_doc(db, doc.id))


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db), _user: models.User = ReadDep):
    doc = db.get(models.Document, doc_id)
    if not doc:
        raise HTTPException(404, "Документ не найден")
    data = storage.read(doc.storage_name)
    if data is None:
        raise HTTPException(410, "Файл отсутствует в хранилище")
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc.filename)}",
        },
    )


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db), user: models.User = WriteDep):
    doc = db.get(models.Document, doc_id)
    if not doc:
        raise HTTPException(404, "Документ не найден")
    owner_code = doc.task.code if doc.task else f"eq-{doc.equipment_id}"
    audit.log_deletion(
        db,
        user,
        entity_type="document",
        entity_code=owner_code,
        description=f"Файл: {doc.filename}",
    )
    storage.delete(doc.storage_name)
    db.delete(doc)
    db.commit()
