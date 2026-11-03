"""
api/routers/admin.py
"""

import logging
import shutil
import io
import subprocess
import os
import gzip
import threading
import time
import sys

from api.plans import PLANS, calculate_new_end_date
from sqlalchemy import func
from pathlib import Path
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from api.config import BASE_DIR
from api.database import get_session, engine, is_sqlite
from api.auth import require_admin
from api.models import User, Subscription, PaymentRequest, Ticket, TicketMessage
from api.plans import PLANS
from services.sms import send_subscription_activated_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

MAIN_ADMIN_PHONE = "09129630901"
MAINTENANCE_FLAG = BASE_DIR / "data" / "maintenance.flag"


def _calc_sub_status(sub: Subscription | None, is_admin: bool) -> tuple[str, bool]:
    if is_admin:
        return "admin", True
    if not sub:
        return "free", False
    if not sub.end_date:
        return "active", True
    end = sub.end_date
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if end > now:
        if sub.plan == "free":
            return "free_active", True
        return "active", True
    return "expired", False


# ═══════════════════════════════════════════════════════════
# حالت تعمیرات (Maintenance Mode)
# ═══════════════════════════════════════════════════════════
@router.get("/maintenance")
async def get_maintenance_status(admin: User = Depends(require_admin)):
    return {"is_maintenance": MAINTENANCE_FLAG.exists()}


@router.post("/maintenance/enable")
async def enable_maintenance(admin: User = Depends(require_admin)):
    MAINTENANCE_FLAG.parent.mkdir(parents=True, exist_ok=True)
    MAINTENANCE_FLAG.touch()
    return {"ok": True, "message": "حالت تعمیرات فعال شد."}


@router.post("/maintenance/disable")
async def disable_maintenance(admin: User = Depends(require_admin)):
    if MAINTENANCE_FLAG.exists():
        MAINTENANCE_FLAG.unlink()
    return {"ok": True, "message": "حالت تعمیرات غیرفعال شد."}


# ═══════════════════════════════════════════════════════════
# ۱. بک‌آپ
# ═══════════════════════════════════════════════════════════
@router.get("/backup")
async def backup_database(admin: User = Depends(require_admin)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BASE_DIR / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    raw_backup_path = None
    compressed_path = None

    try:
        if is_sqlite:
            db_path = BASE_DIR / "data" / "trademun.db"
            if not db_path.exists():
                raise HTTPException(status_code=404, detail="فایل دیتابیس یافت نشد")
            raw_backup_path = backup_dir / f"backup_raw_{timestamp}.db"
            shutil.copy2(db_path, raw_backup_path)
            ext = "db"
        else:
            raw_backup_path = backup_dir / f"backup_raw_{timestamp}.sql"
            user = engine.url.username
            dbname = engine.url.database
            password = engine.url.password or ""
            host = engine.url.host or "localhost"
            port = engine.url.port or 5432

            env = os.environ.copy()
            env["PGPASSWORD"] = password
            cmd = ["pg_dump", "-h", host, "-p", str(port), "-U", user, dbname]

            with open(raw_backup_path, "wb") as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

            if result.returncode != 0:
                # ⬅️ لاگ کردن خطای دقیق psql
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                logger.error(f"[Restore] psql failed: {error_msg}")
                raise HTTPException(
                    status_code=500, detail=f"خطای psql: {error_msg[:500]}"
                )

            ext = "sql"

        compressed_path = backup_dir / f"Trademun_Backup_{timestamp}.{ext}.gz"
        with open(raw_backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        if raw_backup_path.exists():
            os.remove(raw_backup_path)

        return FileResponse(
            path=compressed_path,
            filename=compressed_path.name,
            media_type="application/gzip",
        )

    except Exception as e:
        if raw_backup_path and raw_backup_path.exists():
            os.remove(raw_backup_path)
        if compressed_path and compressed_path.exists():
            os.remove(compressed_path)
        raise HTTPException(status_code=500, detail=f"خطای بک‌آپ: {str(e)}")


# ═══════════════════════════════════════════════════════════
# ۲. بازیابی
# ═══════════════════════════════════════════════════════════
@router.post("/backups/restore")
async def restore_backup(
    file: UploadFile = File(...), admin: User = Depends(require_admin)
):
    from api.database import is_sqlite
    import gzip, shutil, os, threading, time, sys

    if not is_sqlite:
        raise HTTPException(
            status_code=400,
            detail="بازیابی روی سرور (PostgreSQL) از پنل ادمین غیرفعال است. لطفاً از راهنمای SSH استفاده کنید.",
        )

    content = await file.read()
    raw_data = gzip.decompress(content)
    db_path = BASE_DIR / "data" / "trademun.db"

    if db_path.exists():
        shutil.copy2(db_path, BASE_DIR / "data" / "trademun_before_restore.db")
    with open(db_path, "wb") as f:
        f.write(raw_data)

    def restart():
        time.sleep(2)
        sys.exit(1)

    threading.Thread(target=restart, daemon=True).start()

    return {"ok": True, "message": "بازیابی SQLite انجام شد."}


# ═══════════════════════════════════════════════════════════
# ۳. لیست و حذف بک‌آپ‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/backups")
async def list_backups(admin: User = Depends(require_admin)):
    backup_dir = BASE_DIR / "data" / "backups"
    files = []
    if backup_dir.exists():
        for f in backup_dir.glob("Trademun_Backup_*.gz"):
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return {"ok": True, "items": files}


class DeleteBackupsRequest(BaseModel):
    names: list[str]


@router.post("/backups/delete")
async def delete_backups(
    req: DeleteBackupsRequest, admin: User = Depends(require_admin)
):
    backup_dir = BASE_DIR / "data" / "backups"
    deleted = []
    for name in req.names:
        # ⬅️ فقط چک کن فایل توی پوشه backups باشه، فرمت خاصی رو چک نکن
        file_path = backup_dir / name
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            deleted.append(name)
    return {"ok": True, "message": f"{len(deleted)} بک‌آپ حذف شد", "deleted": deleted}


# ═══════════════════════════════════════════════════════════
# ۴. افزودن دستی کاربر
# ═══════════════════════════════════════════════════════════
@router.post("/users/add")
async def add_user_manually(
    phone: str,
    full_name: str,
    plan: str = "free",
    days: int = 0,
    send_sms: bool = True,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    existing = session.exec(select(User).where(User.phone == phone)).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="کاربری با این شماره قبلاً ثبت‌نام کرده است."
        )

    now = datetime.now(timezone.utc)
    new_user = User(phone=phone, full_name=full_name, created_at=now, is_active=True)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    if plan != "free" and days > 0:
        plan_info = PLANS.get(plan)
        if not plan_info:
            raise HTTPException(status_code=400, detail="پلن نامعتبر است")
        end_date = now + timedelta(days=days)
        sub = Subscription(
            user_id=new_user.id,
            plan=plan,
            start_date=now,
            end_date=end_date,
            status="active",
        )
        session.add(sub)
        session.commit()
        if send_sms:
            try:
                send_subscription_activated_sms(phone, plan_info["title"], end_date)
            except Exception:
                pass

    return {"ok": True, "message": f"کاربر {phone} با موفقیت اضافه شد."}


# ═══════════════════════════════════════════════════════════
# ۵. خروجی اکسل
# ═══════════════════════════════════════════════════════════
@router.get("/users/excel")
async def export_users_excel(
    admin: User = Depends(require_admin), session: Session = Depends(get_session)
):
    users = session.exec(select(User)).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "کاربران تریدمون"
    ws.sheet_view.rightToLeft = True
    headers = [
        "شماره موبایل",
        "نام",
        "ایمیل",
        "رمز (فعال/غیرفعال)",
        "نقش",
        "تاریخ عضویت",
        "آخرین ورود",
        "آخرین IP",
        "پلن فعلی",
        "تاریخ انقضا",
        "وضعیت",
        "تاریخچه پلن‌ها",
        "تاریخچه پرداخت‌ها",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="14213D")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for u in users:
        sub = session.exec(
            select(Subscription)
            .where(Subscription.user_id == u.id)
            .order_by(Subscription.created_at.desc())
        ).first()
        subs = session.exec(
            select(Subscription)
            .where(Subscription.user_id == u.id)
            .order_by(Subscription.created_at.asc())
        ).all()
        payments = session.exec(
            select(PaymentRequest)
            .where(PaymentRequest.user_id == u.id)
            .order_by(PaymentRequest.created_at.asc())
        ).all()
        status_text, _ = _calc_sub_status(sub, u.is_admin)
        status_fa = {
            "active": "فعال",
            "expired": "منقضی",
            "free_active": "رایگان (فعال)",
            "free": "بدون اشتراک",
            "admin": "مدیر",
        }.get(status_text, "نامشخص")
        subs_history = " | ".join(
            [
                f"{s.plan} ({s.start_date.strftime('%Y-%m-%d')} تا {s.end_date.strftime('%Y-%m-%d') if s.end_date else 'نامحدود'})"
                for s in subs
            ]
        )
        pay_history = " | ".join(
            [
                f"{p.plan} ({p.amount} تومان، {p.status}, {p.created_at.strftime('%Y-%m-%d')})"
                for p in payments
            ]
        )
        ws.append(
            [
                u.phone,
                u.full_name or "نامشخص",
                u.email or "ثبت نشده",
                "تعیین شده" if u.hashed_password else "تعیین نشده",
                "مدیر" if u.is_admin else "کاربر",
                u.created_at.strftime("%Y-%m-%d") if u.created_at else "نامشخص",
                u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "نامشخص",
                u.last_ip or "نامشخص",
                "نامحدود" if u.is_admin else (sub.plan if sub else "بدون اشتراک"),
                (
                    "نامحدود"
                    if u.is_admin
                    else (
                        sub.end_date.strftime("%Y-%m-%d")
                        if sub and sub.end_date
                        else "نامشخص"
                    )
                ),
                status_fa,
                subs_history or "ندارد",
                pay_history or "ندارد",
            ]
        )
    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(
            max(max_length + 4, 14), 35
        )
    ws.row_dimensions[1].height = 28
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="trademun-users-{timestamp}.xlsx"'
        },
    )


# ═══════════════════════════════════════════════════════════
# ۶. لیست کاربران
# ═══════════════════════════════════════════════════════════
@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin), session: Session = Depends(get_session)
):
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    result = []
    for u in users:
        sub = session.exec(
            select(Subscription)
            .where(Subscription.user_id == u.id)
            .order_by(Subscription.created_at.desc())
        ).first()
        status_text, is_active = _calc_sub_status(sub, u.is_admin)
        result.append(
            {
                "id": u.id,
                "phone": u.phone,
                "full_name": u.full_name or "نامشخص",
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "last_ip": u.last_ip or "نامشخص",
                "last_user_agent": u.last_user_agent or "نامشخص",
                "plan": (
                    "نامحدود (مدیر)"
                    if u.is_admin
                    else (sub.plan if sub else "بدون اشتراک")
                ),
                "end_date": (
                    None
                    if u.is_admin
                    else (sub.end_date.isoformat() if sub and sub.end_date else None)
                ),
                "sub_status": status_text,
                "is_active_sub": is_active,
            }
        )
    return {"ok": True, "items": result}


# ═══════════════════════════════════════════════════════════
# ۷. جزئیات کاربر
# ═══════════════════════════════════════════════════════════
@router.get("/users/{user_id}/details")
async def get_user_details(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    subs = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    ).all()
    subs_list = [
        {
            "id": s.id,
            "plan": s.plan,
            "start": s.start_date.isoformat(),
            "end": s.end_date.isoformat() if s.end_date else None,
            "status": s.status,
        }
        for s in subs
    ]
    payments = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user_id)
        .order_by(PaymentRequest.created_at.desc())
    ).all()
    pay_list = [
        {
            "id": p.id,
            "plan": p.plan,
            "amount": p.amount,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
            "note": p.receipt_note,
        }
        for p in payments
    ]
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "last_ip": user.last_ip,
            "last_user_agent": user.last_user_agent,
        },
        "subscriptions": subs_list,
        "payments": pay_list,
    }


# ═══════════════════════════════════════════════════════════
# ۸. تغییر پلن دستی (با منطق جدید تاریخ)
# ═══════════════════════════════════════════════════════════
@router.post("/users/{user_id}/change-plan")
async def change_user_plan(
    user_id: int,
    plan: str,
    send_sms: bool = True,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    # ۱. پیدا کردن کاربر
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="مدیران اشتراک دائمی دارند")

    # ۲. چک کردن پلن
    plan_info = PLANS.get(plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="پلن نامعتبر است")

    # ۳. پیدا کردن آخرین اشتراک
    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    now = datetime.now(timezone.utc)

    # ⬅️ محاسبه تاریخ جدید با تابع کمکی
    current_end = sub.end_date if sub else None
    new_end = calculate_new_end_date(current_end, plan_info["days"])

    # ۴. ذخیره
    if sub:
        sub.plan = plan
        sub.start_date = now
        sub.end_date = new_end
        sub.status = "active"
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            start_date=now,
            end_date=new_end,
            status="active",
        )
        session.add(sub)

    session.commit()

    # ۵. ارسال پیامک (اختیاری)
    if send_sms:
        try:
            send_subscription_activated_sms(
                user.phone, plan_info["title"], sub.end_date
            )
        except Exception:
            pass

    return {"ok": True, "message": f"پلن کاربر به {plan_info['title']} تغییر یافت"}


# ═══════════════════════════════════════════════════════════
# ۹. تنظیم دستی روزها (با منطق جدید تاریخ)
# ═══════════════════════════════════════════════════════════
@router.post("/users/{user_id}/adjust-days")
async def adjust_user_days(
    user_id: int,
    days: int,
    send_sms: bool = True,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    # ۱. پیدا کردن کاربر
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="مدیران اشتراک دائمی دارند")

    # ۲. پیدا کردن آخرین اشتراک
    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    now = datetime.now(timezone.utc)

    # ⬅️ محاسبه تاریخ جدید
    current_end = sub.end_date if sub else None

    if days > 0:
        # اضافه کردن روز (با تابع کمکی)
        new_end = calculate_new_end_date(current_end, days)
    else:
        # کم کردن روز (فقط از تاریخ فعلی کم کن)
        if current_end:
            new_end = current_end + timedelta(days=days)
            new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            new_end = now + timedelta(days=days)

    # ۳. ذخیره
    if sub:
        sub.end_date = new_end
        # اگه تاریخ جدید از الان کمتر شد، اشتراک منقضی بشه
        if new_end < now:
            sub.status = "expired"
        else:
            sub.status = "active"
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan="free",
            start_date=now,
            end_date=new_end,
            status="active" if new_end > now else "expired",
        )
        session.add(sub)

    session.commit()

    # ۴. ارسال پیامک (اختیاری)
    if send_sms:
        try:
            send_subscription_activated_sms(
                user.phone, f"تغییر اعتبار ({days} روز)", sub.end_date
            )
        except Exception:
            pass

    return {"ok": True, "message": f"{days} روز به اشتراک کاربر اضافه شد"}


# ═══════════════════════════════════════════════════════════
# ۱۰. مدیریت دسترسی‌ها و حذف کاربر (فیکس شده)
# ═══════════════════════════════════════════════════════════
@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if admin.phone != MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=403, detail="فقط مدیر اصلی")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    user.is_admin = True
    session.add(user)
    session.commit()
    return {"ok": True, "message": f"کاربر {user.phone} به مدیر ارتقا یافت"}


@router.post("/users/{user_id}/remove-admin")
async def remove_user_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if admin.phone != MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=403, detail="فقط مدیر اصلی")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.phone == MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=400, detail="نمی‌توانید ادمین اصلی را حذف کنید")
    user.is_admin = False
    session.add(user)
    session.commit()
    return {"ok": True, "message": f"دسترسی ادمین {user.phone} گرفته شد"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    hard_delete: bool = False,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if admin.phone != MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=403, detail="فقط مدیر اصلی")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.phone == MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=400, detail="نمی‌توانید ادمین اصلی را حذف کنید")

    if hard_delete:
        # ⬅️ ۱. اول همه پیام‌های تیکت‌های این کاربر رو پاک کن
        user_tickets = session.exec(
            select(Ticket).where(Ticket.user_id == user_id)
        ).all()
        ticket_ids = [t.id for t in user_tickets]

        if ticket_ids:
            session.exec(
                select(TicketMessage).where(TicketMessage.ticket_id.in_(ticket_ids))
            ).all()
            for msg in session.exec(
                select(TicketMessage).where(TicketMessage.ticket_id.in_(ticket_ids))
            ).all():
                session.delete(msg)
            session.commit()  # ⬅️ حتماً کامیت کن

            # ⬅️ ۲. بعد تیکت‌ها رو پاک کن
            for t in user_tickets:
                session.delete(t)
            session.commit()

        # ⬅️ ۳. حالا بقیه داده‌های کاربر (اشتراک، پرداخت)
        for sub in session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).all():
            session.delete(sub)
        for pay in session.exec(
            select(PaymentRequest).where(PaymentRequest.user_id == user_id)
        ).all():
            session.delete(pay)
        session.commit()

        # ⬅️ ۴. و در آخر خود کاربر
        session.delete(user)
        session.commit()
        return {
            "ok": True,
            "message": "کاربر و تمام داده‌های مرتبط حذف شدند (غیرقابل بازگشت).",
        }
    else:
        user.is_active = False
        session.add(user)
        session.commit()
        return {"ok": True, "message": "کاربر غیرفعال شد (قابل بازگشت)."}


# ═══════════════════════════════════════════════════════════
# ۱۱. پرداخت‌ها و تراکنش‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/payments")
async def list_payments(
    admin: User = Depends(require_admin), session: Session = Depends(get_session)
):
    payments = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.status == "pending")
        .order_by(PaymentRequest.created_at.desc())
    ).all()
    result = []
    for p in payments:
        user = session.get(User, p.user_id)
        result.append(
            {
                "id": p.id,
                "user_phone": user.phone if user else "ناشناس",
                "user_joined_at": (
                    user.created_at.isoformat() if user and user.created_at else None
                ),
                "user_last_login": (
                    user.last_login.isoformat() if user and user.last_login else None
                ),
                "plan": p.plan,
                "receipt_note": p.receipt_note,
                "created_at": p.created_at.isoformat(),
                "ip_address": p.ip_address or "نامشخص",
                "user_agent": p.user_agent or "نامشخص",
                "full_name": p.full_name or "نامشخص",
                "payment_time": p.payment_time or "نامشخص",
            }
        )
    return {"ok": True, "items": result}


@router.get("/transactions")
async def list_all_transactions(
    admin: User = Depends(require_admin), session: Session = Depends(get_session)
):
    payments = session.exec(
        select(PaymentRequest).order_by(PaymentRequest.created_at.desc())
    ).all()
    result = []
    for p in payments:
        user = session.get(User, p.user_id)
        result.append(
            {
                "id": p.id,
                "user_phone": user.phone if user else "ناشناس",
                "plan": p.plan,
                "amount": p.amount,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "reviewed_by": p.reviewed_by,
                "receipt_note": p.receipt_note,
                "payment_time": p.payment_time,
            }
        )
    return {"ok": True, "items": result}


@router.post("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payment = session.get(PaymentRequest, payment_id)
    if not payment or payment.status != "pending":
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    user = session.get(User, payment.user_id)
    plan_info = PLANS.get(payment.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="پلن نامعتبر است")

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()
    now = datetime.now(timezone.utc)

    # ⬅️ محاسبه تاریخ جدید
    current_end = sub.end_date if sub else None
    new_end = calculate_new_end_date(current_end, plan_info["days"])

    if sub:
        sub.plan = payment.plan
        sub.start_date = now
        sub.end_date = new_end
        sub.status = "active"
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan=payment.plan,
            start_date=now,
            end_date=new_end,
            status="active",
        )
        session.add(sub)

    payment.status = "approved"
    payment.reviewed_at = now
    payment.reviewed_by = admin.phone
    session.add(payment)
    session.commit()

    try:
        send_subscription_activated_sms(user.phone, plan_info["title"], sub.end_date)
    except Exception:
        pass
    return {"ok": True, "message": "پرداخت تایید و اشتراک فعال شد"}


@router.post("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payment = session.get(PaymentRequest, payment_id)
    if not payment or payment.status != "pending":
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    payment.status = "rejected"
    payment.reviewed_at = datetime.now(timezone.utc)
    payment.reviewed_by = admin.phone
    session.add(payment)
    session.commit()
    return {"ok": True, "message": "پرداخت رد شد"}


@router.get("/users/{user_id}/ticket-count")
async def get_user_ticket_count(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """تعداد تیکت‌های کاربر (برای هشدار حذف)"""
    count = session.exec(
        select(func.count()).select_from(Ticket).where(Ticket.user_id == user_id)
    ).one()
    return {"count": count}


# ⬅️ endpoint عمومی برای چک کردن حالت تعمیرات (بدون لاگین)
@router.get("/maintenance/public")
async def get_public_maintenance_status():
    return {"is_maintenance": MAINTENANCE_FLAG.exists()}
