"""
api/routers/tickets.py
سیستم تیکتینگ — فاز ۱۳ (با آپلود فایل)
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from datetime import timedelta  # ⬅️ اضافه شد
from sqlmodel import Session, select, func

from api.auth import get_current_user, is_admin_phone
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

# ─── تنظیمات آپلود ───
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
UPLOAD_DIR = Path("data/tickets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ─── محدودیت تیکت باز ───
MAX_OPEN_TICKETS_PER_USER = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(user: User) -> None:
    if not is_admin_phone(user.phone):
        raise HTTPException(status_code=403, detail="دسترسی ادمین لازم است")


def _build_ticket_read(
    session: Session, ticket: Ticket, user: User | None = None
) -> dict:
    messages = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .order_by(TicketMessage.created_at.asc())
    ).all()

    last = messages[-1] if messages else None

    # unread: پیام‌هایی که مخاطب نخونده
    unread = 0
    if user:
        is_admin_viewer = is_admin_phone(user.phone)
        unread = sum(
            1 for m in messages if not m.is_read and m.is_admin != is_admin_viewer
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
    if user and is_admin_phone(user.phone):
        owner = session.get(User, ticket.user_id)
        data["user_phone"] = owner.phone if owner else None
        data["user_name"] = (
            owner.full_name if owner and owner.full_name else None
        )  # ⬅️ این خط رو اضافه کن
    return data


def _build_ticket_detail(session: Session, ticket: Ticket, user: User) -> dict:
    messages = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .order_by(TicketMessage.created_at.asc())
    ).all()

    msg_reads = []
    for m in messages:
        sender = session.get(User, m.sender_id)
        msg_reads.append(
            TicketMessageRead(
                id=m.id,
                sender_id=m.sender_id,
                is_admin=m.is_admin,
                message=m.message,
                attachment_path=m.attachment_path,
                attachment_name=m.attachment_name,
                is_read=m.is_read,
                created_at=m.created_at,
                sender_name=(sender.full_name or sender.phone) if sender else None,
            )
        )

    data = _build_ticket_read(session, ticket, user)
    data["messages"] = msg_reads
    return data


async def _save_attachment(file: UploadFile) -> tuple[str, str]:
    """ذخیره فایل و برگرداندن (path, name)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="نام فایل نامعتبر")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="فقط JPG و PNG مجاز است")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="حجم فایل حداکثر ۵ مگابایت")

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name
    with open(file_path, "wb") as f:
        f.write(contents)
    return f"/data/tickets/{unique_name}", file.filename


# ═══════════════════════════════════════════════════════════
# کاربر
# ═══════════════════════════════════════════════════════════
@router.post("/tickets", response_model=TicketDetail)
async def create_ticket(
    req: TicketCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """ایجاد تیکت جدید — حداکثر 1 تیکت باز همزمان"""
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

    ticket = Ticket(
        user_id=user.id,
        subject=req.subject,
        status="open",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=False,
        message=req.message,
        is_read=False,
        created_at=_utcnow(),
    )

    session.add(msg)
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
    except Exception as e:
        logger.warning(f"[Tickets] WebSocket notify failed: {e}")

    return _build_ticket_detail(session, ticket, user)


@router.get("/tickets", response_model=list[TicketRead])
async def list_my_tickets(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tickets = session.exec(
        select(Ticket)
        .where(Ticket.user_id == user.id)
        .order_by(Ticket.updated_at.desc())
    ).all()
    return [_build_ticket_read(session, t, user) for t in tickets]


@router.get("/tickets/stats", response_model=TicketStats)
async def get_my_ticket_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """آمار تیکت‌های کاربر برای داشبورد"""
    all_tickets = session.exec(select(Ticket).where(Ticket.user_id == user.id)).all()

    open_count = sum(1 for t in all_tickets if t.status == "open")
    closed_count = sum(1 for t in all_tickets if t.status == "closed")

    # پیام‌های خونده‌نشده (که ادمین فرستاده)
    unread_count = 0
    for t in all_tickets:
        msgs = session.exec(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == t.id)
            .where(TicketMessage.is_admin == True)
            .where(TicketMessage.is_read == False)
        ).all()
        unread_count += len(msgs)

    return TicketStats(
        open_count=open_count,
        closed_count=closed_count,
        unread_count=unread_count,
        total_count=len(all_tickets),
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
async def get_my_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")

    # علامت‌گذاری پیام‌های ادمین به عنوان خوانده‌شده
    admin_msgs = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .where(TicketMessage.is_admin == True)
        .where(TicketMessage.is_read == False)
    ).all()
    for m in admin_msgs:
        m.is_read = True
        session.add(m)
    session.commit()

    return _build_ticket_detail(session, ticket, user)


@router.post("/tickets/{ticket_id}/reply", response_model=TicketMessageRead)
async def reply_to_my_ticket(
    ticket_id: int,
    req: TicketMessageCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="این تیکت بسته شده است")

        # ⬅️ چک ضد اسپم
    last_msg = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .where(TicketMessage.sender_id == user.id)
        .order_by(TicketMessage.created_at.desc())
    ).first()

    if last_msg:
        time_diff = _utcnow() - last_msg.created_at
        if time_diff < timedelta(seconds=3):
            raise HTTPException(
                status_code=429,
                detail="لطفاً کمی صبر کنید. ارسال پیام متوالی مجاز نیست.",
            )
    # ⬅️ چک تعداد پیام‌های متوالی (حداکثر ۵ پیام بدون پاسخ ادمین)
    recent_messages = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .order_by(TicketMessage.created_at.desc())
        .limit(6)  # ۵ پیام کاربر + ۱ پیام ادمین
    ).all()

    consecutive_user_messages = 0
    for msg in recent_messages:
        if msg.is_admin:
            break  # اگه به پیام ادمین رسیدیم، متوقف شو
        consecutive_user_messages += 1

    if consecutive_user_messages >= 5:
        raise HTTPException(
            status_code=429,
            detail="شما ۵ پیام متوالی ارسال کرده‌اید. لطفاً تا پاسخ تیم پشتیبانی صبر کنید.",
        )

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=False,
        message=req.message,
        attachment_path=req.attachment_path,
        attachment_name=req.attachment_name,
        is_read=False,
        created_at=_utcnow(),
    )
    ticket.updated_at = _utcnow()
    session.add(msg)
    session.add(ticket)
    session.commit()
    session.refresh(msg)

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
    except Exception as e:
        logger.warning(f"[Tickets] WS notify failed: {e}")

    return TicketMessageRead(
        id=msg.id,
        sender_id=msg.sender_id,
        is_admin=msg.is_admin,
        message=msg.message,
        attachment_path=msg.attachment_path,
        attachment_name=msg.attachment_name,
        is_read=msg.is_read,
        created_at=msg.created_at,
        sender_name=user.full_name or user.phone,
    )


# ═══════════════════════════════════════════════════════════
# آپلود فایل (کاربر)
# ═══════════════════════════════════════════════════════════
@router.post("/tickets/{ticket_id}/upload")
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """آپلود فایل (JPG/PNG، حداکثر ۵MB) به تیکت"""
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="تیکت بسته شده است")

    path, name = await _save_attachment(file)
    return {"ok": True, "path": path, "name": name}


# ═══════════════════════════════════════════════════════════
# ادمین
# ═══════════════════════════════════════════════════════════
@router.get("/admin/tickets", response_model=list[TicketRead])
async def admin_list_tickets(
    status: str | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    stmt = select(Ticket).order_by(Ticket.updated_at.desc())
    if status in ("open", "closed"):
        stmt = (
            select(Ticket)
            .where(Ticket.status == status)
            .order_by(Ticket.updated_at.desc())
        )
    tickets = session.exec(stmt).all()
    return [_build_ticket_read(session, t, user) for t in tickets]


@router.get("/admin/tickets/stats", response_model=TicketStats)
async def admin_ticket_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """آمار کل تیکت‌ها برای ادمین"""
    _require_admin(user)
    all_tickets = session.exec(select(Ticket)).all()
    open_count = sum(1 for t in all_tickets if t.status == "open")
    closed_count = sum(1 for t in all_tickets if t.status == "closed")

    unread_count = 0
    for t in all_tickets:
        msgs = session.exec(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == t.id)
            .where(TicketMessage.is_admin == False)
            .where(TicketMessage.is_read == False)
        ).all()
        unread_count += len(msgs)

    return TicketStats(
        open_count=open_count,
        closed_count=closed_count,
        unread_count=unread_count,
        total_count=len(all_tickets),
    )


@router.get("/admin/tickets/{ticket_id}", response_model=TicketDetail)
async def admin_get_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")

    # علامت‌گذاری پیام‌های کاربر به عنوان خوانده‌شده
    user_msgs = session.exec(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .where(TicketMessage.is_admin == False)
        .where(TicketMessage.is_read == False)
    ).all()
    for m in user_msgs:
        m.is_read = True
        session.add(m)
    session.commit()

    return _build_ticket_detail(session, ticket, user)


@router.post("/admin/tickets/{ticket_id}/reply", response_model=TicketMessageRead)
async def admin_reply_to_ticket(
    ticket_id: int,
    req: TicketMessageCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="این تیکت بسته شده است")

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=True,
        message=req.message,
        is_read=False,
        created_at=_utcnow(),
    )
    ticket.updated_at = _utcnow()
    session.add(msg)
    session.add(ticket)
    session.commit()
    session.refresh(msg)

    return TicketMessageRead(
        id=msg.id,
        sender_id=msg.sender_id,
        is_admin=msg.is_admin,
        message=msg.message,
        attachment_path=msg.attachment_path,
        attachment_name=msg.attachment_name,
        is_read=msg.is_read,
        created_at=msg.created_at,
        sender_name=user.full_name or user.phone,
    )


@router.post("/admin/tickets/{ticket_id}/close")
async def admin_close_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="این تیکت قبلاً بسته شده است")

    ticket.status = "closed"
    ticket.closed_at = _utcnow()
    ticket.closed_by = user.phone
    ticket.updated_at = _utcnow()
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
    """آپلود فایل توسط ادمین"""
    _require_admin(user)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="تیکت بسته شده است")

    path, name = await _save_attachment(file)
    return {"ok": True, "path": path, "name": name}


import os
from pathlib import Path  # (اگه Path قبلا import نشده بود)


@router.delete("/admin/tickets/{ticket_id}")
async def admin_delete_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")

    # ⬅️ ۱. پاک کردن فایل‌های پیوست
    messages = session.exec(
        select(TicketMessage).where(TicketMessage.ticket_id == ticket.id)
    ).all()
    for m in messages:
        if m.attachment_path:
            file_path = Path(".") / m.attachment_path.lstrip("/")
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass

    # ⬅️ ۲. اول پیام‌ها رو پاک کن و کامیت کن
    for m in messages:
        session.delete(m)
    session.commit()

    # ⬅️ ۳. بعد خود تیکت رو پاک کن
    session.delete(ticket)
    session.commit()

    return {"ok": True, "message": "تیکت و پیوست‌ها برای همیشه حذف شدند."}
