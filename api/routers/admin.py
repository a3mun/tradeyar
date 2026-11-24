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
from api.models import SignalLog, SiteStatsOverride, User
from fastapi import Body
from datetime import datetime, timezone
from api.plans import PLANS, calculate_new_end_date
from sqlalchemy import func
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import jdatetime
from services.subscription_service import activate_or_reserve_subscription
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
from api.models import (
    User,
    Subscription,
    PaymentRequest,
    Ticket,
    TicketMessage,
    RefundRequest,
    ExtensionDownloadLog,
    SubscriptionLog,
)
from api.plans import PLANS
from services.sms import send_subscription_activated_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


def _to_jalali_str(dt: datetime | None, include_time: bool = False) -> str:
    """تبدیل تاریخ میلادی به شمسی (تهران)"""
    if not dt:
        return "—"
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        tehran_dt = dt.astimezone(ZoneInfo("Asia/Tehran"))
        j = jdatetime.datetime.fromgregorian(datetime=tehran_dt)
        if include_time:
            return j.strftime("%Y/%m/%d %H:%M")
        return j.strftime("%Y/%m/%d")
    except Exception:
        return "—"


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
    # ⬅️ تاریخ شمسی به وقت تهران
    now_tehran = datetime.now(ZoneInfo("Asia/Tehran"))
    jalali = jdatetime.datetime.fromgregorian(datetime=now_tehran)
    timestamp = jalali.strftime("%Y%m%d_%H%M%S")

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

            cmd = [
                "pg_dump",
                "-h",
                host,
                "-p",
                str(port),
                "-U",
                user,
                "--clean",
                "--if-exists",
                dbname,
            ]

            with open(raw_backup_path, "wb") as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

            if result.returncode != 0:
                raise HTTPException(
                    status_code=500, detail=f"خطای pg_dump: {result.stderr.decode()}"
                )
            ext = "sql"

        compressed_path = backup_dir / f"Trademun_Backup_{timestamp}.{ext}.gz"
        with open(raw_backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        if raw_backup_path.exists():
            os.remove(raw_backup_path)

        return {
            "ok": True,
            "message": "بک‌آپ با موفقیت ساخته شد",
            "name": compressed_path.name,
            "size": compressed_path.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

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


# ⬅️ endpoint امن دانلود بک‌آپ (فقط ادمین)
@router.get("/backups/{name}/download")
async def download_backup(name: str, admin: User = Depends(require_admin)):
    # جلوگیری از path traversal
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="نام فایل نامعتبر")
    file_path = BASE_DIR / "data" / "backups" / name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="فایل یافت نشد")
    return FileResponse(
        path=file_path,
        filename=name,
        media_type="application/gzip",
    )


class DeleteBackupsRequest(BaseModel):
    names: list[str]


@router.post("/backups/delete")
async def delete_backups(
    req: DeleteBackupsRequest, admin: User = Depends(require_admin)
):
    backup_dir = BASE_DIR / "data" / "backups"
    deleted = []
    for name in req.names:
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
                f"{s.plan} ({_to_jalali_str(s.start_date)} تا {_to_jalali_str(s.end_date) if s.end_date else 'نامحدود'})"
                for s in subs
            ]
        )
        pay_history = " | ".join(
            [
                f"{p.plan} ({p.amount} تومان، {p.status}, {_to_jalali_str(p.created_at)})"
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
                _to_jalali_str(u.created_at),
                _to_jalali_str(u.last_login, include_time=True),
                u.last_ip or "نامشخص",
                "نامحدود" if u.is_admin else (sub.plan if sub else "بدون اشتراک"),
                (
                    "نامحدود"
                    if u.is_admin
                    else (
                        _to_jalali_str(sub.end_date)
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
    from api.models import ExtensionDownloadLog
    from sqlalchemy import func

    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    result = []
    for u in users:
        sub = session.exec(
            select(Subscription)
            .where(Subscription.user_id == u.id)
            .order_by(Subscription.created_at.desc())
        ).first()

        status_text, is_active = _calc_sub_status(sub, u.is_admin)

        # 🔴 چک کردن اینکه آیا کاربر افزونه رو دانلود کرده یا نه
        has_downloaded = (
            session.exec(
                select(func.count())
                .select_from(ExtensionDownloadLog)
                .where(ExtensionDownloadLog.user_id == u.id)
            ).one()
            > 0
        )

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
                "extension_downloaded": has_downloaded,  # 🔴 فیلد جدید
                "is_active": u.is_active,
                "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
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

    # 🔴 دریافت قیمت‌های جدید از جدول PricingSettings
    pricing_settings = session.exec(select(PricingSettings)).all()
    pricing_map = {s.plan_id: s.price for s in pricing_settings}

    # 🔴 محاسبه جمع‌بندی مالی
    total_paid = sum(
        p.amount
        for p in payments
        if p.status == "approved" and p.payment_method != "refund"
    )
    total_refunded = sum(
        p.amount
        for p in payments
        if p.status == "approved" and p.payment_method == "refund"
    )
    net_balance = total_paid - total_refunded

    pay_list = [
        {
            "id": p.id,
            "plan": p.plan,
            "amount": p.amount,
            "status": p.status,
            "payment_method": p.payment_method,
            "created_at": p.created_at.isoformat(),
            "note": p.receipt_note,
            # 🔴 استفاده از قیمت جدید (اگر در جدول نبود، از PLANS قدیمی)
            "plan_price": p.plan_price_at_purchase
            or pricing_map.get(p.plan, PLANS.get(p.plan, {}).get("price", 0)),
            "zibal_ref_id": p.zibal_ref_id,  # 🔴 اضافه شد
            "zibal_track_id": p.zibal_track_id,  # 🔴 اضافه شد
        }
        for p in payments
    ]

    subscription_logs = session.exec(
        select(SubscriptionLog)
        .where(SubscriptionLog.user_id == user_id)
        .order_by(SubscriptionLog.created_at.desc())
    ).all()

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
            "is_active": user.is_active,
            "last_seen_at": (
                user.last_seen_at.isoformat() if user.last_seen_at else None
            ),
        },
        "subscriptions": subs_list,
        "payments": pay_list,
        "total_paid": total_paid,
        "total_refunded": total_refunded,
        "net_balance": net_balance,
        "subscription_logs": [
            {
                "id": log.id,
                "admin_phone": log.admin_phone,
                "action_type": log.action_type,
                "description": log.description,
                "created_at": log.created_at.isoformat(),
            }
            for log in subscription_logs
        ],
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
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="مدیران اشتراک دائمی دارند")

    plan_info = PLANS.get(plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="پلن نامعتبر است")

    now = datetime.now(timezone.utc)

    # ۱. پیدا کردن آخرین اشتراک (فعال یا رزرو) برای تعیین تاریخ شروع جدید
    last_sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.end_date.desc())
    ).first()

    # ۲. اگر اشتراک قبلی وجود داشت و در آینده تموم می‌شه → شروع جدید بعد از اون
    if last_sub and last_sub.end_date:
        end = last_sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end > now:
            new_start = end  # شروع از لحظه‌ای که اشتراک قبلی تموم می‌شه
        else:
            new_start = now  # اشتراک قبلی منقضی شده، از الان شروع کن
    else:
        new_start = now

    new_end = new_start + timedelta(days=plan_info["days"])

    # ۳. ساخت اشتراک جدید (به عنوان رزرو یا فعال)
    new_sub = Subscription(
        user_id=user.id,
        plan=plan,
        start_date=new_start,
        end_date=new_end,
        status="active",  # وضعیت واقعی در فرانت محاسبه می‌شه
    )
    session.add(new_sub)
    session.commit()
    session.refresh(new_sub)

    if send_sms:
        try:
            send_subscription_activated_sms(
                user.phone, plan_info["title"], new_sub.end_date
            )
        except Exception:
            pass

    return {"ok": True, "message": f"پلن {plan_info['title']} برای کاربر ثبت شد"}


@router.delete("/users/{user_id}/subscriptions/{sub_id}")
async def delete_user_subscription(
    user_id: int,
    sub_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """حذف یک اشتراک (فعال، رزرو، یا منقضی) توسط ادمین"""
    sub = session.get(Subscription, sub_id)
    if not sub or sub.user_id != user_id:
        raise HTTPException(404, "اشتراک یافت نشد")

    # 🔴 ثبت لاگ قبل از حذف
    log = SubscriptionLog(
        user_id=user_id,
        admin_phone=admin.phone,
        action_type="manual_sub_delete",
        description=f"حذف اشتراک {PLANS.get(sub.plan, {}).get('title', sub.plan)} (از {_to_jalali_str(sub.start_date)} تا {_to_jalali_str(sub.end_date)})",
    )
    session.add(log)

    session.delete(sub)
    session.commit()
    return {"ok": True, "message": "اشتراک با موفقیت حذف شد و در تاریخچه ثبت گردید"}


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
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="مدیران اشتراک دائمی دارند")

    # در approve_payment، قبل از ساخت اشتراک جدید:
    active_subs = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "active")
    ).all()
    for old_sub in active_subs:
        old_sub.status = "expired"
        session.add(old_sub)
    session.commit()

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    now = datetime.now(timezone.utc)
    current_end = sub.end_date if sub else None

    if days > 0:
        new_end = calculate_new_end_date(current_end, days)
    else:
        if current_end:
            new_end = current_end + timedelta(days=days)
            new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            new_end = now + timedelta(days=days)

    if sub:
        sub.end_date = new_end
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

    if send_sms:
        try:
            send_subscription_activated_sms(
                user.phone, f"تغییر اعتبار ({days} روز)", sub.end_date
            )
        except Exception:
            pass

    # 🔴 ثبت لاگ تغییر تاریخ
    action = "افزایش" if days > 0 else "کاهش"
    log = SubscriptionLog(
        user_id=user_id,
        admin_phone=admin.phone,
        action_type="manual_date_adjust",
        description=f"{action} {abs(days)} روز به تاریخ انقضا",
    )
    session.add(log)
    session.commit()

    return {"ok": True, "message": f"{days} روز به اشتراک کاربر اضافه شد"}


@router.post("/users/{user_id}/set-expiry-date")
async def set_user_expiry_date(
    user_id: int,
    new_date_jalali: str = Body(...),
    send_sms: bool = Body(False),  # 🔴 از Body بگیره، پیش‌فرض False
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """
    تنظیم مستقیم تاریخ انقضا با تاریخ شمسی (مثلاً 1405/11/25)
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="مدیران اشتراک دائمی دارند")

    # تبدیل تاریخ شمسی به میلادی
    try:
        from jdatetime import datetime as jdatetime_cls

        parts = new_date_jalali.strip().split("/")
        if len(parts) != 3:
            raise ValueError("فرمت تاریخ اشتباه است")
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
        gdate = jdatetime_cls(jy, jm, jd).togregorian()
        # تنظیم ساعت به 23:59:59 به وقت تهران
        new_end = gdate.replace(hour=23, minute=59, second=59, microsecond=0)
        # تبدیل به UTC
        new_end = new_end.replace(tzinfo=ZoneInfo("Asia/Tehran")).astimezone(
            timezone.utc
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"تاریخ نامعتبر: {e}")

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    now = datetime.now(timezone.utc)

    if sub:
        sub.end_date = new_end
        sub.status = "active" if new_end > now else "expired"
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

    if send_sms:
        try:
            send_subscription_activated_sms(user.phone, "تغییر تاریخ انقضا", new_end)
        except Exception:
            pass

    # 🔴 ثبت لاگ تغییر تاریخ
    log = SubscriptionLog(
        user_id=user_id,
        admin_phone=admin.phone,
        action_type="manual_date_set",
        description=f"تنظیم دستی تاریخ انقضا به {new_date_jalali}",
    )
    session.add(log)
    session.commit()

    return {"ok": True, "message": f"تاریخ انقضا به {new_date_jalali} تغییر یافت"}


# ═══════════════════════════════════════════════════════════
# ۱۰. مدیریت دسترسی‌ها و حذف کاربر
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

    if not hard_delete:
        user.is_active = False
        session.add(user)
        session.commit()
        return {"ok": True, "message": "کاربر غیرفعال شد (قابل بازگشت)."}

    # حذف کامل در یک تراکنش؛ در صورت هر خطا همه تغییرات rollback می‌شوند.
    from api.models import ExtensionToken

    try:
        # 1) وابستگی مستقیم RefundRequest به Subscription باید قبل از اشتراک حذف شود.
        refund_requests = session.exec(
            select(RefundRequest).where(RefundRequest.user_id == user_id)
        ).all()
        for item in refund_requests:
            session.delete(item)

        # 2) پیام‌های تیکت‌های متعلق به کاربر، سپس خود تیکت‌ها.
        user_tickets = session.exec(
            select(Ticket).where(Ticket.user_id == user_id)
        ).all()
        ticket_ids = [ticket.id for ticket in user_tickets if ticket.id is not None]

        if ticket_ids:
            ticket_messages = session.exec(
                select(TicketMessage).where(TicketMessage.ticket_id.in_(ticket_ids))
            ).all()
            for message in ticket_messages:
                session.delete(message)

        # TicketMessage.sender_id نیز FK به users.id است.
        # پیام‌هایی که این کاربر فرستاده، حتی اگر در تیکت دیگری باشند،
        # نباید بعد از حذف کاربر باقی بمانند.
        sent_messages = session.exec(
            select(TicketMessage).where(TicketMessage.sender_id == user_id)
        ).all()
        sent_ids = {message.id for message in sent_messages}
        for message in sent_messages:
            session.delete(message)

        for ticket in user_tickets:
            session.delete(ticket)

        # 3) سایر جدول‌های دارای FK به کاربر.
        for model in (
            Subscription,
            PaymentRequest,
            ExtensionToken,
            ExtensionDownloadLog,
            SubscriptionLog,
        ):
            records = session.exec(select(model).where(model.user_id == user_id)).all()
            for record in records:
                session.delete(record)

        # اجرای DELETEها پیش از حذف کاربر و سپس commit واحد.
        session.flush()
        session.delete(user)
        session.commit()

        return {
            "ok": True,
            "message": "کاربر و تمام داده‌های وابسته با موفقیت حذف شدند.",
        }

    except Exception:
        session.rollback()
        logger.exception("Hard delete failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=500,
            detail="حذف کامل کاربر انجام نشد؛ تمام تغییرات برگشت داده شدند. لاگ سرور را بررسی کنید.",
        )


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
                "amount": p.amount or 0,
                "payment_method": p.payment_method or "card",
                "receipt_note": p.receipt_note,
                "created_at": p.created_at.isoformat(),
                "ip_address": p.ip_address or "نامشخص",
                "user_agent": p.user_agent or "نامشخص",
                "full_name": p.full_name or "نامشخص",
                "payment_time": p.payment_time or "نامشخص",
            }
        )
    return {"ok": True, "items": result}


# 🔴 اندپوینت جدید برای همه تراکنش‌ها (شامل رد شده‌ها)
@router.get("/all-transactions")
async def list_all_transactions_merged(
    admin: User = Depends(require_admin), session: Session = Depends(get_session)
):
    payments = session.exec(
        select(PaymentRequest).order_by(PaymentRequest.created_at.desc())
    ).all()

    # 🔴 دریافت قیمت‌های جدید از جدول PricingSettings
    pricing_settings = session.exec(select(PricingSettings)).all()
    pricing_map = {s.plan_id: s.price for s in pricing_settings}

    result = []
    for p in payments:
        user = session.get(User, p.user_id)

        # 🔴 استفاده از قیمت جدید (اگر در جدول نبود، از PLANS قدیمی)
        current_price = p.plan_price_at_purchase or pricing_map.get(
            p.plan, PLANS.get(p.plan, {}).get("price", 0)
        )

        result.append(
            {
                "id": f"pay_{p.id}",
                "source": "payment_request",
                "user_phone": user.phone if user else "ناشناس",
                "plan": p.plan,
                "plan_price": current_price,  # 🔴 قیمت به‌روز شده
                "amount": p.amount or 0,
                "payment_method": p.payment_method or "card",
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "reviewed_by": p.reviewed_by,
                "receipt_note": p.receipt_note,
                "payment_time": p.payment_time,
                "admin_note": p.admin_note,
                "full_name": p.full_name,
                "zibal_ref_id": p.zibal_ref_id,  # 🔴 اضافه شد
                "zibal_track_id": p.zibal_track_id,  # 🔴 اضافه شد
            }
        )
    return {"ok": True, "items": result}


# 🔴 اندپوینت جدید برای ویرایش مبلغ توسط ادمین
@router.patch("/transactions/{tx_id}/amount")
async def update_transaction_amount(
    tx_id: str,
    amount: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if tx_id.startswith("pay_"):
        pid = int(tx_id.replace("pay_", ""))
        p = session.get(PaymentRequest, pid)
        if not p:
            raise HTTPException(404, "تراکنش یافت نشد")
        p.amount = amount
        # 🔴 حفظ یادداشت قبلی
        old_note = p.admin_note or ""
        p.admin_note = f"{old_note} (مبلغ توسط مدیر ویرایش شد)"
        session.add(p)
        session.commit()
        return {"ok": True, "message": "مبلغ ویرایش شد", "id": tx_id, "amount": amount}
    raise HTTPException(400, "شناسه نامعتبر")


# 🔴 اندپوینت جدید برای اکسل تراکنش‌ها
@router.get("/transactions/excel")
async def export_transactions_excel(
    admin: User = Depends(require_admin), session: Session = Depends(get_session)
):
    payments = session.exec(
        select(PaymentRequest).order_by(PaymentRequest.created_at.desc())
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "تراکنش‌ها"
    ws.sheet_view.rightToLeft = True

    headers = [
        "شناسه",
        "شماره کاربر",
        "پلن",
        "روش پرداخت",
        "مبلغ (تومان)",
        "وضعیت",
        "تاریخ ثبت",
        "بررسی توسط",
        "یادداشت ادمین",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="14213D")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for p in payments:
        user = session.get(User, p.user_id)
        status_fa = {
            "pending": "در انتظار",
            "approved": "تایید شده",
            "rejected": "رد شده",
        }.get(p.status, p.status)
        method_fa = {"zibal": "درگاه زیبال", "card": "کارت به کارت"}.get(
            p.payment_method, p.payment_method or "نامشخص"
        )
        ws.append(
            [
                f"pay_{p.id}",
                user.phone if user else "ناشناس",
                PLANS.get(p.plan, {}).get("title", p.plan),
                method_fa,
                p.amount or 0,
                status_fa,
                _to_jalali_str(p.created_at, include_time=True),
                p.reviewed_by or "—",
                p.admin_note or "",
            ]
        )

    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(
            max(max_length + 4, 14), 35
        )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="trademun-transactions-{timestamp}.xlsx"'
        },
    )


@router.post("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: int,
    admin_note: str = Body(None, embed=True),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payment = session.get(PaymentRequest, payment_id)
    if not payment:
        raise HTTPException(404, "تراکنش یافت نشد")
    user = session.get(User, payment.user_id)
    if not user:
        raise HTTPException(404, "کاربر یافت نشد")

    # 🔴 استفاده از تابع مشترک
    activation = activate_or_reserve_subscription(session, user.id, payment.plan)

    if not activation["ok"]:
        raise HTTPException(status_code=400, detail=activation["error"])

    payment.status = "approved"
    payment.reviewed_at = datetime.now(timezone.utc)
    payment.reviewed_by = admin.phone
    payment.admin_note = admin_note
    session.add(payment)
    session.commit()

    try:
        send_subscription_activated_sms(
            user.phone,
            activation["plan_info"]["title"],
            activation["new_sub_end"],
        )
    except Exception:
        pass

    msg = "اشتراک رزرو شد" if activation["is_reserved"] else "اشتراک فعال شد"
    return {"ok": True, "message": f"پرداخت تایید و {msg}"}


@router.post("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: int,
    admin_note: str = Body(None, embed=True),  # 🔴 embed=True
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payment = session.get(PaymentRequest, payment_id)
    payment.status = "rejected"
    payment.reviewed_at = datetime.now(timezone.utc)
    payment.reviewed_by = admin.phone
    payment.admin_note = admin_note  # 🔴 ذخیره یادداشت
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


@router.get("/maintenance/public")
async def get_public_maintenance_status():
    return {"is_maintenance": MAINTENANCE_FLAG.exists()}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from api.auth import get_password_hash

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    user.hashed_password = get_password_hash(new_password)
    session.add(user)
    session.commit()
    return {"ok": True, "message": "رمز عبور کاربر با موفقیت تغییر یافت"}


# ═══════════════════════════════════════════════════════════
# 🔴 آمار دانلود افزونه
# ═══════════════════════════════════════════════════════════
@router.get("/users/{user_id}/extension-stats")
async def get_extension_stats(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from api.models import ExtensionDownloadLog
    from sqlalchemy import func

    # تعداد کل
    total = session.exec(
        select(func.count())
        .select_from(ExtensionDownloadLog)
        .where(ExtensionDownloadLog.user_id == user_id)
    ).one()

    # لیست کامل لاگ‌ها (مرتب از جدید به قدیم)
    logs = session.exec(
        select(ExtensionDownloadLog)
        .where(ExtensionDownloadLog.user_id == user_id)
        .order_by(ExtensionDownloadLog.downloaded_at.desc())
    ).all()

    return {
        "total_downloads": total or 0,
        "logs": [
            {
                "id": log.id,
                "downloaded_at": log.downloaded_at.isoformat(),
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
            }
            for log in logs
        ],
    }


@router.get("/extension-logs")
async def get_extension_logs(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from api.models import ExtensionDownloadLog

    logs = session.exec(
        select(ExtensionDownloadLog)
        .order_by(ExtensionDownloadLog.downloaded_at.desc())
        .limit(100)
    ).all()

    result = []
    for log in logs:
        user = session.get(User, log.user_id)
        result.append(
            {
                "id": log.id,
                "user_phone": user.phone if user else "ناشناس",
                "user_name": user.full_name if user else "-",
                "downloaded_at": log.downloaded_at.isoformat(),
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
            }
        )
    return {"items": result}


# ═══════════════════════════════════════════════════════════
# 🔴 اندپوینت جدید: تغییر وضعیت تراکنش توسط ادمین
# ═══════════════════════════════════════════════════════════
@router.patch("/transactions/{tx_id}/status")
async def update_transaction_status(
    tx_id: str,
    new_status: str,
    send_sms: bool = False,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if tx_id.startswith("pay_"):
        pid = int(tx_id.replace("pay_", ""))
        p = session.get(PaymentRequest, pid)
        if not p:
            raise HTTPException(404, "تراکنش یافت نشد")

        p.status = new_status
        p.reviewed_at = datetime.now(timezone.utc)
        p.reviewed_by = admin.phone

        # 🔴 فعال‌سازی اشتراک در صورت تایید (با تابع مشترک)
        if new_status == "approved":
            user = session.get(User, p.user_id)
            if user:
                activation = activate_or_reserve_subscription(session, user.id, p.plan)
                if not activation["ok"]:
                    raise HTTPException(status_code=400, detail=activation["error"])

                if send_sms:
                    try:
                        send_subscription_activated_sms(
                            user.phone,
                            activation["plan_info"]["title"],
                            activation["new_sub_end"],
                        )
                    except Exception:
                        pass

        session.add(p)
        session.commit()
        return {"ok": True, "message": f"وضعیت تراکنش به {new_status} تغییر یافت"}
    raise HTTPException(400, "شناسه نامعتبر")


# ═══════════════════════════════════════════════════════════
# 🔴 اندپوینت جدید: لاگ تغییرات تراکنش
# ═══════════════════════════════════════════════════════════
@router.get("/transactions/{tx_id}/logs")
async def get_transaction_logs(
    tx_id: str,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    # فعلاً یه لاگ ساده برمی‌گردونیم (چون جدول جداگانه نداریم)
    return {"logs": []}


@router.patch("/transactions/{tx_id}/note")
async def update_transaction_note(
    tx_id: str,
    admin_note: str = Body(..., embed=True),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if tx_id.startswith("pay_"):
        pid = int(tx_id.replace("pay_", ""))
        p = session.get(PaymentRequest, pid)
        if not p:
            raise HTTPException(404, "تراکنش یافت نشد")

        p.admin_note = admin_note
        session.add(p)
        session.commit()
        return {"ok": True, "message": "یادداشت ذخیره شد"}
    raise HTTPException(400, "شناسه نامعتبر")


# ═══════════════════════════════════════════════════════════
# 🔴 مدیریت عودت وجه (توسط ادمین)
# ═══════════════════════════════════════════════════════════
@router.post("/users/{user_id}/refund")
async def create_refund_request(
    user_id: int,
    new_plan: str = Body(...),
    refund_amount: int = Body(...),
    admin_note: str = Body(None),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "کاربر یافت نشد")

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    ).first()

    if not sub or sub.plan == "free":
        raise HTTPException(400, "کاربر اشتراک فعال ندارد")

    # 🔴 فقط درخواست عودت ثبت می‌شه (تغییر پلن دستی توسط ادمین انجام شده)
    req = RefundRequest(
        user_id=user_id,
        subscription_id=sub.id,
        old_plan=sub.plan,
        new_plan=new_plan,
        refund_amount=refund_amount,
        admin_note=admin_note,
        status="pending",
    )
    session.add(req)
    session.commit()

    # 🔴 ثبت لاگ عودت وجه
    log = SubscriptionLog(
        user_id=user_id,
        admin_phone=admin.phone,
        action_type="refund",
        description=f"ثبت درخواست عودت {refund_amount:,} تومان (از {sub.plan} به {new_plan})",
    )
    session.add(log)
    session.commit()

    return {"ok": True, "message": "درخواست عودت ثبت شد (تغییر پلن را دستی بررسی کنید)"}


@router.get("/refunds")
async def list_refunds(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    reqs = session.exec(
        select(RefundRequest).order_by(RefundRequest.created_at.desc())
    ).all()
    result = []
    for r in reqs:
        user = session.get(User, r.user_id)
        result.append(
            {
                "id": r.id,
                "user_phone": user.phone if user else "ناشناس",
                "old_plan": r.old_plan,
                "new_plan": r.new_plan,
                "refund_amount": r.refund_amount,
                "admin_note": r.admin_note,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
        )

    return {"ok": True, "items": result}


@router.post("/refunds/{req_id}/approve")
async def approve_refund(
    req_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    req = session.get(RefundRequest, req_id)
    if not req or req.status != "pending":
        raise HTTPException(404, "درخواست یافت نشد")

    req.status = "refunded"
    req.processed_at = datetime.now(timezone.utc)
    req.processed_by = admin.phone
    session.add(req)

    # 🔴 ثبت تراکنش عودت
    new_payment = PaymentRequest(
        user_id=req.user_id,
        plan="refund",
        amount=req.refund_amount,
        status="approved",
        payment_method="refund",
        admin_note=f"عودت وجه - {req.admin_note or ''}",
        created_at=datetime.now(timezone.utc),
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=admin.phone,
    )
    session.add(new_payment)
    session.commit()
    return {"ok": True, "message": "عودت وجه تایید شد"}


@router.post("/refunds/{req_id}/reject")
async def reject_refund(
    req_id: int,
    admin_note: str = Body(None, embed=True),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    req = session.get(RefundRequest, req_id)
    if not req or req.status != "pending":
        raise HTTPException(404, "درخواست یافت نشد")

    req.status = "rejected"
    req.processed_at = datetime.now(timezone.utc)
    req.processed_by = admin.phone
    req.admin_note = admin_note or req.admin_note
    session.add(req)
    session.commit()
    return {"ok": True, "message": "درخواست عودت رد شد"}


# ═══════════════════════════════════════════════════════════
# 🔴 آمار کلی پنل ادمین
# ═══════════════════════════════════════════════════════════
@router.get("/dashboard-stats")
async def get_dashboard_stats(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from api.models import PaymentRequest, RefundRequest
    from sqlalchemy import func

    # درآمد کل (فقط پرداخت‌های تایید شده و غیر refund)
    total_revenue = (
        session.exec(
            select(func.sum(PaymentRequest.amount))
            .where(PaymentRequest.status == "approved")
            .where(PaymentRequest.payment_method != "refund")
        ).one()
        or 0
    )

    # جمع عودت‌ها (تایید شده)
    total_refunded = (
        session.exec(
            select(func.sum(PaymentRequest.amount))
            .where(PaymentRequest.status == "approved")
            .where(PaymentRequest.payment_method == "refund")
        ).one()
        or 0
    )

    # درآمد خالص
    net_revenue = total_revenue - total_refunded

    # تعداد درخواست‌های عودت pending
    pending_refunds = (
        session.exec(
            select(func.count())
            .select_from(RefundRequest)
            .where(RefundRequest.status == "pending")
        ).one()
        or 0
    )

    return {
        "ok": True,
        "total_revenue": total_revenue,
        "total_refunded": total_refunded,
        "net_revenue": net_revenue,
        "pending_refunds": pending_refunds,
    }


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if admin.phone != MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=403, detail="فقط مدیر اصلی")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    user.is_active = True
    session.add(user)
    session.commit()
    return {"ok": True, "message": f"کاربر {user.phone} فعال شد"}


# ═══════════════════════════════════════════════════════════
# 🎯 سایت آمار — کنترل نمایشی (فاز ۱۴.۹.۱۲)
# ═══════════════════════════════════════════════════════════
from pydantic import BaseModel as _PydanticBase
from services.backtest_service import get_site_stats as _get_site_stats


class SiteStatsOverrideRequest(_PydanticBase):
    key: str
    value: float


@router.get("/site-stats")
async def admin_get_site_stats(
    _admin=Depends(require_admin),
    session: Session = Depends(get_session),
):
    data = _get_site_stats()

    override = session.exec(
        select(SiteStatsOverride).where(SiteStatsOverride.key == "is_hidden")
    ).first()

    data["is_hidden"] = bool(override.is_hidden) if override else False

    return {"ok": True, **data}


@router.post("/site-stats/override")
async def admin_set_site_stats_override(
    req: SiteStatsOverrideRequest,
    current_user=Depends(require_admin),
    session: Session = Depends(get_session),
):
    allowed_keys = [
        "win_rate",
        "direction_accuracy",
        "total_signals",
        "win_rate_scalp",
        "direction_accuracy_scalp",
        "win_rate_swing",
        "direction_accuracy_swing",
        "win_rate_position",
        "direction_accuracy_position",
    ]
    if req.key not in allowed_keys:
        raise HTTPException(status_code=400, detail="کلید نامعتبر")
    if req.value < 0 or req.value > 100:
        raise HTTPException(status_code=400, detail="مقدار باید بین ۰ تا ۱۰۰ باشد")
    existing = session.exec(
        select(SiteStatsOverride).where(SiteStatsOverride.key == req.key)
    ).first()
    if existing:
        existing.value = req.value
        existing.updated_by = current_user.phone
        session.add(existing)
    else:
        session.add(
            SiteStatsOverride(
                key=req.key, value=req.value, updated_by=current_user.phone
            )
        )
    session.commit()
    return {"ok": True, "key": req.key, "value": req.value}


from api.models import PricingSettings  # به importها اضافه کن


class SiteStatsVisibilityRequest(BaseModel):
    hidden: bool


@router.post("/site-stats/toggle-visibility")
async def toggle_site_stats_visibility(
    req: SiteStatsVisibilityRequest,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    override = session.exec(
        select(SiteStatsOverride).where(SiteStatsOverride.key == "is_hidden")
    ).first()

    if not override:
        override = SiteStatsOverride(
            key="is_hidden",
            value=0.0,
            is_hidden=req.hidden,
            updated_by=admin.phone,
            updated_at=datetime.now(timezone.utc),
        )
    else:
        override.is_hidden = req.hidden
        override.updated_by = admin.phone
        override.updated_at = datetime.now(timezone.utc)

    session.add(override)
    session.commit()

    return {"ok": True, "is_hidden": req.hidden}


# ─── خواندن قیمت‌ها (برای صفحه اشتراک) ───
@router.get("/pricing")
async def get_pricing_settings(session: Session = Depends(get_session)):
    # این API نباید نیاز به لاگین داشته باشه، چون صفحه اشتراک برای همه بازه
    settings = session.exec(select(PricingSettings)).all()
    # اگر خالی بود، مقادیر پیش‌فرض رو برگردون
    if not settings:
        return {
            "1_month": {
                "price": 390000,
                "old_price": 590000,
                "discount": 33,
                "popular": False,
            },
            "3_months": {
                "price": 1050000,
                "old_price": 1770000,
                "discount": 40,
                "popular": True,
            },
            "6_months": {
                "price": 1870000,
                "old_price": 3540000,
                "discount": 47,
                "popular": False,
            },
            "12_months": {
                "price": 3270000,
                "old_price": 7080000,
                "discount": 54,
                "popular": False,
            },
        }
    return {
        s.plan_id: {
            "price": s.price,
            "old_price": s.old_price,
            "discount": s.discount,
            "popular": s.popular,
        }
        for s in settings
    }


# ─── ذخیره قیمت‌ها (فقط برای ادمین) ───
class PricingUpdateItem(BaseModel):
    plan_id: str
    price: int
    old_price: int
    discount: int
    popular: bool


@router.post("/pricing/update")
async def update_pricing_settings(
    items: list[PricingUpdateItem],
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    for item in items:
        existing = session.exec(
            select(PricingSettings).where(PricingSettings.plan_id == item.plan_id)
        ).first()
        if existing:
            existing.price = item.price
            existing.old_price = item.old_price
            existing.discount = item.discount
            existing.popular = item.popular
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
        else:
            session.add(
                PricingSettings(
                    plan_id=item.plan_id,
                    price=item.price,
                    old_price=item.old_price,
                    discount=item.discount,
                    popular=item.popular,
                )
            )
    session.commit()
    return {"ok": True, "message": "قیمت‌ها با موفقیت به‌روزرسانی شدند"}


@router.delete("/site-stats/override/{key}")
async def admin_delete_site_stats_override(
    key: str,
    _admin=Depends(require_admin),
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(SiteStatsOverride).where(SiteStatsOverride.key == key)
    ).first()
    if existing:
        session.delete(existing)
        session.commit()
    return {"ok": True, "deleted": key}
