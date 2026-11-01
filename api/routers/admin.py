"""
api/routers/admin.py
"""

import logging, shutil, csv, io, subprocess, tempfile, os
import gzip
import threading
import time
from pydantic import BaseModel

from pathlib import Path
from sqlalchemy import text
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from api.database import get_session, engine
from api.auth import require_admin
from api.models import User, Subscription, PaymentRequest
from api.plans import PLANS
from services.sms import send_subscription_activated_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

MAIN_ADMIN_PHONE = "09129630901"


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
# ۱. بک‌آپ (Postgres / SQLite)
# ═══════════════════════════════════════════════════════════
@router.get("/backup")
async def backup_database(admin: User = Depends(require_admin)):
    from api.config import BASE_DIR

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    is_sqlite = engine.url.drivername.startswith("sqlite")

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
                raise HTTPException(
                    status_code=500, detail=f"خطای pg_dump: {result.stderr.decode()}"
                )
            if not raw_backup_path.exists() or raw_backup_path.stat().st_size == 0:
                raise HTTPException(status_code=500, detail="فایل بک‌آپ خالی است")
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
# ۲. بازیابی (Postgres / SQLite) با ری‌استارت خودکار
# ═══════════════════════════════════════════════════════════
@router.post("/backups/restore")
async def restore_backup(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
):
    from api.config import BASE_DIR

    is_sqlite = engine.url.drivername.startswith("sqlite")

    if not file.filename.endswith(".gz"):
        raise HTTPException(status_code=400, detail="فایل باید با پسوند .gz باشد")

    try:
        content = await file.read()
        raw_data = gzip.decompress(content)

        # چک امنیتی فرمت فایل
        is_sql_file = file.filename.endswith(".sql.gz")
        is_db_file = file.filename.endswith(".db.gz")

        if is_sqlite and not is_db_file:
            raise HTTPException(
                status_code=400,
                detail="شما در حال اجرای لوکال (SQLite) هستید. فقط فایل‌های .db.gz مجاز هستند.",
            )
        if not is_sqlite and not is_sql_file:
            raise HTTPException(
                status_code=400,
                detail="شما در حال اجرای سرور (PostgreSQL) هستید. فقط فایل‌های .sql.gz مجاز هستند.",
            )

        if is_sqlite:
            db_path = BASE_DIR / "data" / "trademun.db"
            if db_path.exists():
                shutil.copy2(db_path, BASE_DIR / "data" / "trademun_before_restore.db")
            with open(db_path, "wb") as f:
                f.write(raw_data)
        else:
            user = engine.url.username
            dbname = engine.url.database
            password = engine.url.password or ""
            host = engine.url.host or "localhost"
            port = engine.url.port or 5432

            env = os.environ.copy()
            env["PGPASSWORD"] = password
            cmd = ["psql", "-h", host, "-p", str(port), "-U", user, "-d", dbname]
            result = subprocess.run(cmd, input=raw_data, env=env, capture_output=True)

            if result.returncode != 0:
                raise HTTPException(
                    status_code=500, detail=f"خطای psql: {result.stderr.decode()}"
                )

        # ری‌استارت خودکار پس از ۲ ثانیه
        def restart_app():
            time.sleep(2)
            os._exit(0)

        threading.Thread(target=restart_app, daemon=True).start()

        return {
            "ok": True,
            "message": "بازیابی با موفقیت انجام شد. سیستم در حال ری‌استارت خودکار است...",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در بازیابی: {str(e)}")


# ═══════════════════════════════════════════════════════════
# ۳. لیست و حذف بک‌آپ‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/backups")
async def list_backups(admin: User = Depends(require_admin)):
    from api.config import BASE_DIR

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
    from api.config import BASE_DIR

    backup_dir = BASE_DIR / "data" / "backups"
    deleted = []
    for name in req.names:
        if not name.startswith("Trademun_Backup_") or not name.endswith(".gz"):
            continue
        file_path = backup_dir / name
        if file_path.exists():
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
# ۸. تغییر پلن دستی
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
    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()
    now = datetime.now(timezone.utc)
    if sub:
        sub.plan = plan
        sub.start_date = now
        sub.end_date = now + timedelta(days=plan_info["days"])
        sub.status = "active"
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            start_date=now,
            end_date=now + timedelta(days=plan_info["days"]),
            status="active",
        )
        session.add(sub)
    session.commit()
    if send_sms:
        try:
            send_subscription_activated_sms(
                user.phone, plan_info["title"], sub.end_date
            )
        except Exception:
            pass
    return {"ok": True, "message": f"پلن کاربر به {plan_info['title']} تغییر یافت"}


# ═══════════════════════════════════════════════════════════
# ۹. تنظیم دستی روزها
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
    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()
    now = datetime.now(timezone.utc)
    if sub:
        sub.end_date = (sub.end_date or now) + timedelta(days=days)
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan="free",
            start_date=now,
            end_date=now + timedelta(days=days),
            status="active",
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
    return {"ok": True, "message": f"{days} روز به اشتراک کاربر اضافه شد"}


# ═══════════════════════════════════════════════════════════
# ۱۰. مدیریت دسترسی‌ها
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


# ═══════════════════════════════════════════════════════════
# ۱۱. حذف کاربر
# ═══════════════════════════════════════════════════════════
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
        for sub in session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).all():
            session.delete(sub)
        for pay in session.exec(
            select(PaymentRequest).where(PaymentRequest.user_id == user_id)
        ).all():
            session.delete(pay)
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
# ۱۲. پرداخت‌ها
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
    if sub:
        start_date = max(sub.end_date, now) if sub.end_date else now
        sub.plan = payment.plan
        sub.start_date = now
        sub.end_date = start_date + timedelta(days=plan_info["days"])
        sub.status = "active"
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan=payment.plan,
            start_date=now,
            end_date=now + timedelta(days=plan_info["days"]),
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
