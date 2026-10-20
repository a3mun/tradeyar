from fastapi import APIRouter, Depends, Header
from sqlmodel import Session, select
from api.database import get_session
from api.models import SignalLog

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/unsent")
def get_unsent_signals(
    session: Session = Depends(get_session),
    x_api_key: str = Header(...),
):
    # 🔴 بررسی کلید امنیتی
    if x_api_key != "38800":  # همون رمز ادمین
        return {"error": "unauthorized"}

    signals = session.exec(
        select(SignalLog).where(SignalLog.telegram_sent == False).order_by(SignalLog.id)
    ).all()
    return [s.model_dump() for s in signals]


@router.post("/mark-sent/{signal_id}")
def mark_signal_sent(
    signal_id: int,
    session: Session = Depends(get_session),
    x_api_key: str = Header(...),
):
    if x_api_key != "38800":
        return {"error": "unauthorized"}

    signal = session.get(SignalLog, signal_id)
    if signal:
        signal.telegram_sent = True
        session.add(signal)
        session.commit()
    return {"ok": True}
