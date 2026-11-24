"""
TradeMun Ticket API
نسخه محافظه‌کارانه ارتقای سیستم تیکت
- حفظ مسیرها و قراردادهای فعلی API
- حفظ مدل‌های Ticket و TicketMessage و بدون Migration
- اعتبارسنجی واقعی فایل‌های JPEG/PNG و محدودیت حجم
- اعتبارسنجی مسیر پیوست قبل از اتصال به پیام
- اصلاح شمارش پیام‌های متوالی
- حذف فایل فقط از پوشه اختصاصی تیکت‌ها
"""

import logging
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select, func

from api.auth import get_current_user
from api.database import get_session
from api.models import Ticket, TicketMessage, User
from api.schemas import (
    TicketCreate,
    TicketDetail,
    TicketMessageCreate,
    TicketMessageRead,
    TicketRead,
    TicketStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tickets"])

MAX_FILE_SIZE = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
UPLOAD_DIR = Path("data/tickets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_OPEN_TICKETS_PER_USER = 1
MAX_CONSECUTIVE_USER_MESSAGES = 10
MESSAGE_COOLDOWN_SECONDS = 1

# مسیر عمومی فعلی حفظ شده تا با فرانت‌اند موجود سازگار بماند.
PUBLIC_UPLOAD_PREFIX = "/data/tickets/"
_ATTACHMENT_NAME_RE = re.compile(r"^[a-f0-9]{32}\.(?:jpg|jpeg|png)$", re.IGNORECASE)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(user: User) -> None:
    if not bool(user.is_admin):
        raise HTTPException(status_code=403, detail="دسترسی ادمین لازم است")


def _ticket_or_404(session: Session, ticket_id: int) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    return ticket


def _get_owned_ticket(session: Session, ticket_id: int, user: User) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    return ticket


def _ticket_messages(session: Session, ticket_id: int) -> list[TicketMessage]:
    return session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc(), TicketMessage.id.asc())
    ).all()


def _build_ticket_read(
    session: Session, ticket: Ticket, user: User | None = None
) -> dict:
    messages = _ticket_messages(session, ticket.id)
    last = messages[-1] if messages else None

    unread = 0
    if user:
        viewer_is_admin = bool(user.is_admin)
        unread = sum(
            1
            for message in messages
            if not message.is_read and message.is_admin != viewer_is_admin
        )

    data = {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "messages_count": len(messages),
        "unread_count": unread,
        "last_message": last.message if last else None,
        "last_message_at": last.created_at if last else None,
    }

    if user and bool(user.is_admin):
        owner = session.get(User, ticket.user_id)
        data["user_phone"] = owner.phone if owner else None
        data["user_name"] = owner.full_name if owner and owner.full_name else None

    return data


def _build_ticket_detail(session: Session, ticket: Ticket, user: User) -> dict:
    messages = _ticket_messages(session, ticket.id)
    msg_reads = []

    for message in messages:
        sender = session.get(User, message.sender_id)
        msg_reads.append(
            TicketMessageRead(
                id=message.id,
                sender_id=message.sender_id,
                is_admin=message.is_admin,
                message=message.message,
                attachment_path=message.attachment_path,
                attachment_name=message.attachment_name,
                is_read=message.is_read,
                created_at=message.created_at,
                sender_name=(sender.full_name or sender.phone) if sender else None,
            )
        )

    data = _build_ticket_read(session, ticket, user)
    data["messages"] = msg_reads
    return data


def _validate_attachment_reference(path_value: str | None, name_value: str | None):
    """
    فقط فایل‌هایی پذیرفته می‌شوند که از endpoint آپلود همین سیستم آمده باشند.
    مسیر نسبی/مطلق دلخواه از کلاینت هرگز به فایل‌سیستم تبدیل نمی‌شود.
    """
    if not path_value and not name_value:
        return None, None
    if not path_value or not name_value:
        raise HTTPException(status_code=400, detail="اطلاعات پیوست ناقص است")



    if not path_value.startswith(PUBLIC_UPLOAD_PREFIX):
        raise HTTPException(status_code=400, detail="مسیر پیوست نامعتبر است")

    stored_name = path_value[len(PUBLIC_UPLOAD_PREFIX) :]
    if (
        "/" in stored_name
        or "\\" in stored_name
        or not _ATTACHMENT_NAME_RE.fullmatch(stored_name)
    ):
        raise HTTPException(status_code=400, detail="نام فایل پیوست نامعتبر است")

    ext = Path(stored_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="نوع فایل پیوست مجاز نیست")

    root = UPLOAD_DIR.resolve()
    candidate = (root / stored_name).resolve()
    if candidate.parent != root or not candidate.is_file():
        raise HTTPException(status_code=400, detail="فایل پیوست پیدا نشد")

    # نام نمایشی صرفاً متن است؛ کنترل طول و حذف مسیرهای احتمالی.
    safe_display_name = Path(str(name_value).replace("\\", "/")).name[:180].strip()
    if not safe_display_name:
        safe_display_name = "attachment" + ext

    return path_value, safe_display_name


def _has_valid_image_signature(contents: bytes, extension: str) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return len(contents) >= 3 and contents[:3] == b"\xff\xd8\xff"
    if extension == ".png":
        return contents.startswith(b"\x89PNG\r\n\x1a\n")
    return False


async def _save_attachment(file: UploadFile) -> tuple[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="نام فایل نامعتبر")

    original_name = Path(file.filename.replace("\\", "/")).name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="فقط JPG و PNG مجاز است")

    # یک بایت بیشتر می‌خوانیم تا فایل بزرگ بدون بارگذاری کامل شناسایی شود.
    contents = await file.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="حجم فایل حداکثر ۲ مگابایت است")

    if not _has_valid_image_signature(contents, ext):
        raise HTTPException(
            status_code=400, detail="محتوای فایل با پسوند آن مطابقت ندارد"
        )

    unique_name = f"{uuid.uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / unique_name

    try:
        with file_path.open("xb") as handle:
            handle.write(contents)
    except OSError:
        logger.exception("[Tickets] Failed to save attachment")
        raise HTTPException(status_code=500, detail="ذخیره فایل انجام نشد")

    return f"{PUBLIC_UPLOAD_PREFIX}{unique_name}", original_name[:180]


def _validate_message_or_attachment(
    req: TicketMessageCreate,
) -> tuple[str | None, str | None]:
    message = (req.message or "").strip()
    path_value, name_value = _validate_attachment_reference(
        req.attachment_path, req.attachment_name
    )
    if not message and not path_value:
        raise HTTPException(status_code=400, detail="متن پیام یا فایل پیوست لازم است")
    if len(message) > 2000:
        raise HTTPException(status_code=400, detail="متن پیام بیش از حد مجاز است")
    return path_value, name_value


def _check_user_message_limits(session: Session, ticket_id: int, user_id: int) -> None:
    last_user_message = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .where(TicketMessage.sender_id == user_id)
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
    ).first()

    now = _utcnow()
    if last_user_message:
        created_at = last_user_message.created_at
        # سازگاری با datetimeهای قدیمی بدون timezone
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now - created_at < timedelta(seconds=MESSAGE_COOLDOWN_SECONDS):
            raise HTTPException(
                status_code=429,
                detail="لطفاً کمی صبر کنید و سپس پیام بعدی را ارسال کنید.",
            )

    recent_messages = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
        .limit(MAX_CONSECUTIVE_USER_MESSAGES)
    ).all()

    consecutive_user_messages = 0
    for message in recent_messages:
        if message.is_admin:
            break
        if message.sender_id != user_id:
            # پیام غیرادمین از کاربر دیگری نباید به عنوان پیام همین کاربر شمرده شود.
            break
        consecutive_user_messages += 1

    if consecutive_user_messages >= MAX_CONSECUTIVE_USER_MESSAGES:
        raise HTTPException(
            status_code=429,
            detail=(
                f"شما {MAX_CONSECUTIVE_USER_MESSAGES} پیام متوالی ارسال کرده‌اید. "
                "لطفاً تا پاسخ تیم پشتیبانی صبر کنید."
            ),
        )


def _mark_messages_read(
    session: Session, ticket_id: int, messages_from_admin: bool
) -> None:
    unread_messages = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .where(TicketMessage.is_admin == messages_from_admin)
        .where(TicketMessage.is_read == False)
    ).all()

    if not unread_messages:
        return

    for message in unread_messages:
        message.is_read = True
        session.add(message)
    session.commit()


def _safe_delete_attachment(path_value: str | None) -> None:
    if not path_value or not path_value.startswith(PUBLIC_UPLOAD_PREFIX):
        return

    stored_name = path_value[len(PUBLIC_UPLOAD_PREFIX) :]
    if (
        "/" in stored_name
        or "\\" in stored_name
        or not _ATTACHMENT_NAME_RE.fullmatch(stored_name)
    ):
        logger.warning("[Tickets] Skipping unsafe attachment path during deletion")
        return

    root = UPLOAD_DIR.resolve()
    candidate = (root / stored_name).resolve()
    if candidate.parent != root:
        logger.warning("[Tickets] Skipping attachment outside upload directory")
        return

    try:
        candidate.unlink(missing_ok=True)
    except OSError:
        logger.exception("[Tickets] Could not delete attachment %s", stored_name)


# ─────────────────────────────────────────────────────────
# کاربر
# ─────────────────────────────────────────────────────────
@router.post("/tickets", response_model=TicketDetail)
async def create_ticket(
    req: TicketCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    open_count = session.exec(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.user_id == user.id)
        .where(Ticket.status == "open")
    ).one()

    if open_count >= MAX_OPEN_TICKETS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="شما یک تیکت باز دارید. لطفاً تا بسته شدن آن صبر کنید.",
        )

    attachment_path, attachment_name = (
        _validate_attachment_reference(req.attachment_path, req.attachment_name)
        if req.attachment_path or req.attachment_name
        else (None, None)
    )

    now = _utcnow()
    ticket = Ticket(
        user_id=user.id,
        subject=req.subject.strip(),
        status="open",
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    message = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=False,
        message=req.message.strip(),
        attachment_path=attachment_path,
        attachment_name=attachment_name,
        is_read=False,
        created_at=now,
    )
    session.add(message)
    session.commit()

    try:
        from api.routers.admin_ws import notify_admins

        await notify_admins(
            {
                "type": "new_ticket",
                "ticket_id": ticket.id,
                "user_phone": user.phone,
                "subject": req.subject,
                "message": f"🎫 تیکت جدید از {user.phone}: {req.subject}",
            }
        )
    except Exception as exc:
        logger.warning("[Tickets] WebSocket notify failed: %s", exc)

    return _build_ticket_detail(session, ticket, user)


@router.get("/tickets", response_model=list[TicketRead])
async def list_my_tickets(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tickets = session.exec(
        select(Ticket)
        .where(Ticket.user_id == user.id)
        .order_by(Ticket.updated_at.desc(), Ticket.id.desc())
    ).all()
    return [_build_ticket_read(session, ticket, user) for ticket in tickets]


@router.get("/tickets/stats", response_model=TicketStats)
async def get_my_ticket_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tickets = session.exec(select(Ticket).where(Ticket.user_id == user.id)).all()

    open_count = sum(ticket.status == "open" for ticket in tickets)
    closed_count = sum(ticket.status == "closed" for ticket in tickets)

    unread_count = 0
    ticket_ids = [ticket.id for ticket in tickets]
    if ticket_ids:
        unread_count = session.exec(
            select(func.count())
            .select_from(TicketMessage)
            .where(TicketMessage.ticket_id.in_(ticket_ids))
            .where(TicketMessage.is_admin == True)
            .where(TicketMessage.is_read == False)
        ).one()

    return TicketStats(
        open_count=open_count,
        closed_count=closed_count,
        unread_count=unread_count,
        total_count=len(tickets),
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
async def get_my_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ticket = _get_owned_ticket(session, ticket_id, user)
    _mark_messages_read(session, ticket.id, messages_from_admin=True)
    return _build_ticket_detail(session, ticket, user)


@router.post("/tickets/{ticket_id}/reply", response_model=TicketMessageRead)
async def reply_to_my_ticket(
    ticket_id: int,
    req: TicketMessageCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ticket = _get_owned_ticket(session, ticket_id, user)
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="این تیکت بسته شده است")

    attachment_path, attachment_name = _validate_message_or_attachment(req)
    _check_user_message_limits(session, ticket.id, user.id)

    now = _utcnow()
    message = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=False,
        message=(req.message or "").strip(),
        attachment_path=attachment_path,
        attachment_name=attachment_name,
        is_read=False,
        created_at=now,
    )
    ticket.updated_at = now
    session.add(message)
    session.add(ticket)
    session.commit()
    session.refresh(message)

    try:
        from api.routers.admin_ws import notify_admins

        await notify_admins(
            {
                "type": "ticket_reply",
                "ticket_id": ticket.id,
                "sender": "user",
                "user_phone": user.phone,
                "message": f"💬 پاسخ کاربر {user.phone} در تیکت #{ticket.id}",
            }
        )
    except Exception as exc:
        logger.warning("[Tickets] WebSocket notify failed: %s", exc)

    return TicketMessageRead(
        id=message.id,
        sender_id=message.sender_id,
        is_admin=message.is_admin,
        message=message.message,
        attachment_path=message.attachment_path,
        attachment_name=message.attachment_name,
        is_read=message.is_read,
        created_at=message.created_at,
        sender_name=user.full_name or user.phone,
    )


@router.post("/tickets/{ticket_id}/upload")
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ticket = _get_owned_ticket(session, ticket_id, user)
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="تیکت بسته شده است")

    path, name = await _save_attachment(file)
    return {"ok": True, "path": path, "name": name}


# ─────────────────────────────────────────────────────────
# ادمین
# ─────────────────────────────────────────────────────────
@router.get("/admin/tickets", response_model=list[TicketRead])
async def admin_list_tickets(
    status: str | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    statement = select(Ticket)
    if status in ("open", "closed"):
        statement = statement.where(Ticket.status == status)
    tickets = session.exec(
        statement.order_by(Ticket.updated_at.desc(), Ticket.id.desc())
    ).all()
    return [_build_ticket_read(session, ticket, user) for ticket in tickets]


@router.get("/admin/tickets/stats", response_model=TicketStats)
async def admin_ticket_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    total_count = session.exec(select(func.count()).select_from(Ticket)).one()
    open_count = session.exec(
        select(func.count()).select_from(Ticket).where(Ticket.status == "open")
    ).one()
    closed_count = session.exec(
        select(func.count()).select_from(Ticket).where(Ticket.status == "closed")
    ).one()
    unread_count = session.exec(
        select(func.count())
        .select_from(TicketMessage)
        .where(TicketMessage.is_admin == False)
        .where(TicketMessage.is_read == False)
    ).one()

    return TicketStats(
        open_count=open_count,
        closed_count=closed_count,
        unread_count=unread_count,
        total_count=total_count,
    )


@router.get("/admin/tickets/{ticket_id}", response_model=TicketDetail)
async def admin_get_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = _ticket_or_404(session, ticket_id)
    _mark_messages_read(session, ticket.id, messages_from_admin=False)
    return _build_ticket_detail(session, ticket, user)


@router.post("/admin/tickets/{ticket_id}/reply", response_model=TicketMessageRead)
async def admin_reply_to_ticket(
    ticket_id: int,
    req: TicketMessageCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = _ticket_or_404(session, ticket_id)
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="این تیکت بسته شده است")

    attachment_path, attachment_name = _validate_message_or_attachment(req)
    now = _utcnow()
    message = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=True,
        message=(req.message or "").strip(),
        attachment_path=attachment_path,
        attachment_name=attachment_name,
        is_read=False,
        created_at=now,
    )
    ticket.updated_at = now
    session.add(message)
    session.add(ticket)
    session.commit()
    session.refresh(message)

    return TicketMessageRead(
        id=message.id,
        sender_id=message.sender_id,
        is_admin=message.is_admin,
        message=message.message,
        attachment_path=message.attachment_path,
        attachment_name=message.attachment_name,
        is_read=message.is_read,
        created_at=message.created_at,
        sender_name=user.full_name or user.phone,
    )


@router.post("/admin/tickets/{ticket_id}/close")
async def admin_close_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = _ticket_or_404(session, ticket_id)
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="این تیکت قبلاً بسته شده است")

    now = _utcnow()
    ticket.status = "closed"
    ticket.closed_at = now
    ticket.closed_by = user.phone
    ticket.updated_at = now
    session.add(ticket)
    session.commit()
    return {"ok": True, "message": "تیکت بسته شد"}


@router.post("/admin/tickets/{ticket_id}/upload")
async def admin_upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = _ticket_or_404(session, ticket_id)
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="تیکت بسته شده است")

    path, name = await _save_attachment(file)
    return {"ok": True, "path": path, "name": name}


@router.delete("/admin/tickets/{ticket_id}")
async def admin_delete_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = _ticket_or_404(session, ticket_id)

    messages = session.exec(
        select(TicketMessage).where(TicketMessage.ticket_id == ticket.id)
    ).all()

    # فایل‌ها فقط پس از حذف موفق رکوردها پاک می‌شوند؛ مسیرها نیز محدود شده‌اند.
    attachment_paths = [
        message.attachment_path for message in messages if message.attachment_path
    ]

    try:
        for message in messages:
            session.delete(message)
        session.commit()

        session.delete(ticket)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("[Tickets] Ticket deletion failed for ticket_id=%s", ticket_id)
        raise HTTPException(status_code=500, detail="حذف تیکت انجام نشد")

    for attachment_path in attachment_paths:
        _safe_delete_attachment(attachment_path)

    return {"ok": True, "message": "تیکت و پیوست‌های آن حذف شدند."}
