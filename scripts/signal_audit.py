"""
scripts/signal_audit.py
گزارش تشخیصی سیگنال‌ها — نسخه ۱.۰
============================================================
هدف: یافتن ریشه‌ی باگ‌های سیگنال‌دهی و راستی‌آزمایی

این اسکریپت **مستقل از دیتابیس** اجرا می‌شود:
  • با ``--file path.json`` از فایل JSON می‌خواند
  • بدون آرگومان، از دیتابیس لوکال (SQLite/Postgres)

خروجی:
  • گزارش رنگی در ترمینال
  • فایل ``signal_audit_report.json`` در کنار اسکریپت

نحوه‌ی اجرا:
    python scripts/signal_audit.py
    python scripts/signal_audit.py --file trademun_signals.json
    python scripts/signal_audit.py --output my_report.json

نسخه ۱.۰ — فاز ۱۰.۱
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ─── مسیر پروژه (برای import از api/models) ───
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("signal_audit")


# ═══════════════════════════════════════════════════════════
# رنگ‌های ترمینال — ساده و بدون وابستگی
# ═══════════════════════════════════════════════════════════
class C:
    """ANSI colors — روی ویندوز با colorama کار نمی‌کنه، ساده ANSI"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_RED = "\033[101m"
    BG_GREEN = "\033[102m"
    BG_YELLOW = "\033[103m"

    @classmethod
    def disable(cls):
        """خاموش کردن رنگ — برای ویندوز یا redirect به فایل"""
        for attr in dir(cls):
            if attr.isupper() and not attr.startswith("_"):
                setattr(cls, attr, "")


# ═══════════════════════════════════════════════════════════
# ساختار سیگنال نرمال‌شده
# ═══════════════════════════════════════════════════════════
@dataclass
class NormalizedSignal:
    """سیگنال نرمال‌شده — مستقل از منبع ورودی (DB یا JSON)"""

    id: int
    timestamp: str
    ticker: str
    source: str
    signal: str
    direction: str
    confidence: int
    consensus: str
    regime: str
    tf: str
    market_type: str
    risk_profile: str
    result: Optional[str]
    expired: bool
    expired_bias: Optional[str]
    trend_correct: Optional[bool]
    had_trap: bool
    trap_type: Optional[str]
    is_weak: bool
    rr: Optional[float] = None
    rr_net: Optional[float] = None
    price: Optional[float] = None
    confidence_tier: str = ""  # محاسبه‌شده


def _confidence_tier(conf: int) -> str:
    """دسته‌بندی confidence به ۵ لایه"""
    if conf >= 80:
        return "80-100"
    if conf >= 60:
        return "60-79"
    if conf >= 50:
        return "50-59"
    if conf >= 40:
        return "40-49"
    if conf >= 30:
        return "30-39"
    return "0-29"


# ═══════════════════════════════════════════════════════════
# بارگذارها — از JSON و DB
# ═══════════════════════════════════════════════════════════
def load_from_json(path: Path) -> list[NormalizedSignal]:
    """بارگذاری سیگنال‌ها از فایل JSON"""
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError(f"فایل {path} باید یک آرایه JSON باشد")

    out: list[NormalizedSignal] = []
    for item in raw:
        try:
            sig = NormalizedSignal(
                id=int(item.get("id", 0)),
                timestamp=str(item.get("timestamp", "")),
                ticker=str(item.get("ticker", "")),
                source=str(item.get("source", "")),
                signal=str(item.get("signal", "")),
                direction=str(item.get("direction", "neutral")),
                confidence=int(item.get("confidence", 0) or 0),
                consensus=str(item.get("consensus", "neutral")),
                regime=str(item.get("regime", "range")),
                tf=str(item.get("tf", "")),
                market_type=str(item.get("market_type", "futures")),
                risk_profile=str(item.get("risk_profile", "aggressive")),
                result=item.get("result"),
                expired=bool(item.get("expired", False)),
                expired_bias=item.get("expired_bias"),
                trend_correct=item.get("trend_correct"),
                had_trap=bool(item.get("had_trap", False)),
                trap_type=item.get("trap_type"),
                is_weak=bool(item.get("is_weak", False)),
                rr=item.get("rr"),
                rr_net=item.get("rr_net"),
                price=item.get("price"),
            )
            sig.confidence_tier = _confidence_tier(sig.confidence)
            out.append(sig)
        except Exception as e:
            logger.warning(f"رد کردن رکورد نامعتبر: {e}")
            continue

    return out


def load_from_db() -> list[NormalizedSignal]:
    """بارگذاری سیگنال‌ها از دیتابیس لوکال"""
    try:
        from sqlmodel import Session, select

        from api.database import engine
        from api.models import SignalLog
    except Exception as e:
        raise RuntimeError(
            f"import از api.database ناموفق: {e}\n"
            f"مطمئن شو در ریشه‌ی پروژه هستی و venv فعاله"
        ) from e

    out: list[NormalizedSignal] = []
    with Session(engine) as session:
        rows = session.exec(select(SignalLog)).all()

    for r in rows:
        sig = NormalizedSignal(
            id=r.id or 0,
            timestamp=r.timestamp.isoformat() if r.timestamp else "",
            ticker=r.ticker,
            source=r.source,
            signal=r.signal,
            direction=r.direction,
            confidence=r.confidence,
            consensus=r.consensus,
            regime=r.regime,
            tf=r.tf,
            market_type=r.market_type,
            risk_profile=r.risk_profile,
            result=r.result,
            expired=r.expired,
            expired_bias=r.expired_bias,
            trend_correct=r.trend_correct,
            had_trap=r.had_trap,
            trap_type=r.trap_type,
            is_weak=r.is_weak,
            rr=r.rr,
            rr_net=r.rr_net,
            price=r.price,
        )
        sig.confidence_tier = _confidence_tier(sig.confidence)
        out.append(sig)

    return out


# ═══════════════════════════════════════════════════════════
# آنالیز — گروه‌بندی و شمارش
# ═══════════════════════════════════════════════════════════
def _is_closed(sig: NormalizedSignal) -> bool:
    """آیا نتیجه‌ی سیگنال قطعی شده؟"""
    return sig.result in ("win", "loss") or sig.expired


def _outcome(sig: NormalizedSignal) -> str:
    """نتیجه‌ی قطعی: win / loss / expired_win / expired_loss / expired_flat / pending"""
    if sig.result == "win":
        return "win"
    if sig.result == "loss":
        return "loss"
    if sig.expired:
        bias = sig.expired_bias or "flat"
        return f"expired_{bias}"
    return "pending"


def _win_rate(wins: int, losses: int) -> float:
    total = wins + losses
    return round(wins / total * 100, 2) if total > 0 else 0.0


def _section(title: str, icon: str = "📊") -> None:
    print()
    print(f"{C.BOLD}{C.CYAN}{'═' * 62}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{icon}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═' * 62}{C.RESET}")


def _subtitle(text: str) -> None:
    print(f"\n{C.BOLD}{C.YELLOW}▸ {text}{C.RESET}")


def _row(label: str, value: Any, color: str = "") -> None:
    print(f"  {label:.<40} {color}{value}{C.RESET}")


def analyze_signals(signals: list[NormalizedSignal]) -> dict:
    """آنالیز کامل سیگنال‌ها — خروجی به‌صورت dict"""

    report: dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "total_signals": len(signals),
        },
        "overall": {},
        "by_direction": {},
        "by_confidence_tier": {},
        "by_regime": {},
        "by_market_type": {},
        "by_risk_profile": {},
        "by_source": {},
        "by_tf": {},
        "by_is_weak": {},
        "by_trap": {},
        "by_expired_bias": {},
        "trend_correct": {},
        "pending_analysis": {},
        "outcome_distribution": {},
        "warnings": [],
    }

    if not signals:
        report["warnings"].append("هیچ سیگنالی برای آنالیز وجود ندارد")
        return report

    # ═══ شمارنده‌های کلی ═══
    total = len(signals)
    wins = sum(1 for s in signals if s.result == "win")
    losses = sum(1 for s in signals if s.result == "loss")
    expired = sum(1 for s in signals if s.expired)
    pending = sum(1 for s in signals if not _is_closed(s))

    report["overall"] = {
        "total": total,
        "closed_win_loss": wins + losses,
        "wins": wins,
        "losses": losses,
        "expired": expired,
        "pending": pending,
        "win_rate": _win_rate(wins, losses),
    }

    # ═══ توزیع نتیجه ═══
    outcomes: dict[str, int] = defaultdict(int)
    for s in signals:
        outcomes[_outcome(s)] += 1
    report["outcome_distribution"] = dict(outcomes)

    # ═══ به تفکیک جهت ═══
    by_dir: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        d = s.direction or "neutral"
        by_dir[d]["total"] += 1
        if s.result == "win":
            by_dir[d]["win"] += 1
        elif s.result == "loss":
            by_dir[d]["loss"] += 1
        elif s.expired:
            by_dir[d]["expired"] += 1
        else:
            by_dir[d]["pending"] += 1

    report["by_direction"] = {
        d: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for d, v in by_dir.items()
    }

    # ═══ به تفکیک سطح confidence ═══
    by_conf: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        tier = s.confidence_tier or _confidence_tier(s.confidence)
        by_conf[tier]["total"] += 1
        if s.result == "win":
            by_conf[tier]["win"] += 1
        elif s.result == "loss":
            by_conf[tier]["loss"] += 1
        elif s.expired:
            by_conf[tier]["expired"] += 1
        else:
            by_conf[tier]["pending"] += 1

    report["by_confidence_tier"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_conf.items()
    }

    # ═══ به تفکیک رژیم ═══
    by_regime: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        by_regime[s.regime]["total"] += 1
        if s.result == "win":
            by_regime[s.regime]["win"] += 1
        elif s.result == "loss":
            by_regime[s.regime]["loss"] += 1
        elif s.expired:
            by_regime[s.regime]["expired"] += 1
        else:
            by_regime[s.regime]["pending"] += 1

    report["by_regime"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])}
        for k, v in by_regime.items()
    }

    # ═══ به تفکیک market_type ═══
    by_mt: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        mt = s.market_type or "unknown"
        by_mt[mt]["total"] += 1
        if s.result == "win":
            by_mt[mt]["win"] += 1
        elif s.result == "loss":
            by_mt[mt]["loss"] += 1
        elif s.expired:
            by_mt[mt]["expired"] += 1
        else:
            by_mt[mt]["pending"] += 1

    report["by_market_type"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_mt.items()
    }

    # ═══ به تفکیک risk_profile ═══
    by_rp: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        rp = s.risk_profile or "unknown"
        by_rp[rp]["total"] += 1
        if s.result == "win":
            by_rp[rp]["win"] += 1
        elif s.result == "loss":
            by_rp[rp]["loss"] += 1
        elif s.expired:
            by_rp[rp]["expired"] += 1
        else:
            by_rp[rp]["pending"] += 1

    report["by_risk_profile"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_rp.items()
    }

    # ═══ به تفکیک source ═══
    by_src: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        by_src[s.source]["total"] += 1
        if s.result == "win":
            by_src[s.source]["win"] += 1
        elif s.result == "loss":
            by_src[s.source]["loss"] += 1
        elif s.expired:
            by_src[s.source]["expired"] += 1
        else:
            by_src[s.source]["pending"] += 1

    report["by_source"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_src.items()
    }

    # ═══ به تفکیک TF ═══
    by_tf: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        by_tf[s.tf]["total"] += 1
        if s.result == "win":
            by_tf[s.tf]["win"] += 1
        elif s.result == "loss":
            by_tf[s.tf]["loss"] += 1
        elif s.expired:
            by_tf[s.tf]["expired"] += 1
        else:
            by_tf[s.tf]["pending"] += 1

    report["by_tf"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_tf.items()
    }

    # ═══ به تفکیک is_weak ═══
    by_weak: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        key = "weak" if s.is_weak else "not_weak"
        by_weak[key]["total"] += 1
        if s.result == "win":
            by_weak[key]["win"] += 1
        elif s.result == "loss":
            by_weak[key]["loss"] += 1
        elif s.expired:
            by_weak[key]["expired"] += 1
        else:
            by_weak[key]["pending"] += 1

    report["by_is_weak"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_weak.items()
    }

    # ═══ تله‌ها ═══
    by_trap: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0, "pending": 0}
    )
    for s in signals:
        key = "had_trap" if s.had_trap else "no_trap"
        by_trap[key]["total"] += 1
        if s.result == "win":
            by_trap[key]["win"] += 1
        elif s.result == "loss":
            by_trap[key]["loss"] += 1
        elif s.expired:
            by_trap[key]["expired"] += 1
        else:
            by_trap[key]["pending"] += 1

    report["by_trap"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])} for k, v in by_trap.items()
    }

    # ═══ نوع تله ═══
    by_trap_type: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "win": 0, "loss": 0, "expired": 0}
    )
    for s in signals:
        if not s.had_trap or not s.trap_type:
            continue
        by_trap_type[s.trap_type]["total"] += 1
        if s.result == "win":
            by_trap_type[s.trap_type]["win"] += 1
        elif s.result == "loss":
            by_trap_type[s.trap_type]["loss"] += 1
        elif s.expired:
            by_trap_type[s.trap_type]["expired"] += 1

    report["by_trap_type"] = {
        k: {**v, "win_rate": _win_rate(v["win"], v["loss"])}
        for k, v in by_trap_type.items()
    }

    # ═══ توزیع expired_bias ═══
    exp_bias: dict[str, int] = defaultdict(int)
    for s in signals:
        if s.expired:
            exp_bias[s.expired_bias or "flat"] += 1
    report["by_expired_bias"] = dict(exp_bias)

    # ═══ correlation trend_correct ═══
    tc_true_wins = 0
    tc_true_losses = 0
    tc_false_wins = 0
    tc_false_losses = 0

    for s in signals:
        if s.trend_correct is None:
            continue
        if s.result not in ("win", "loss"):
            continue
        if s.trend_correct:
            if s.result == "win":
                tc_true_wins += 1
            else:
                tc_true_losses += 1
        else:
            if s.result == "win":
                tc_false_wins += 1
            else:
                tc_false_losses += 1

    report["trend_correct"] = {
        "true_wins": tc_true_wins,
        "true_losses": tc_true_losses,
        "false_wins": tc_false_wins,
        "false_losses": tc_false_losses,
        "true_win_rate": _win_rate(tc_true_wins, tc_true_losses),
        "false_win_rate": _win_rate(tc_false_wins, tc_false_losses),
    }

    # ═══ آنالیز Pending ═══
    pending_by_tf: dict[str, int] = defaultdict(int)
    for s in signals:
        if not _is_closed(s):
            pending_by_tf[s.tf] += 1

    report["pending_analysis"] = {
        "by_tf": dict(pending_by_tf),
    }

    # ═══ هشدارها ═══
    warnings: list[str] = []

    # ─── هشدار ۱: SHORT bias ───
    dir_stats = report["by_direction"]
    long_s = dir_stats.get("long", {})
    short_s = dir_stats.get("short", {})
    if long_s.get("total", 0) > 0 and short_s.get("total", 0) > 0:
        total_dir = long_s["total"] + short_s["total"]
        short_pct = short_s["total"] / total_dir * 100
        if short_pct > 55:
            warnings.append(
                f"⚠️ SHORT bias: {short_pct:.1f}% سیگنال‌ها SHORT هستن "
                f"(انتظار: ۴۰-۶۰٪)"
            )

    # ─── هشدار ۲: is_weak معکوس ───
    weak_s = report["by_is_weak"].get("weak", {})
    strong_s = report["by_is_weak"].get("not_weak", {})
    if weak_s.get("win_rate", 0) > strong_s.get("win_rate", 0) + 5:
        warnings.append(
            f"⚠️ is_weak معکوس: ضعیف‌ها ({weak_s.get('win_rate', 0)}%) "
            f"بهتر از قطعی‌ها ({strong_s.get('win_rate', 0)}%) عمل کردن"
        )

    # ─── هشدار ۳: confidence بالا = عملکرد بد ───
    conf_stats = report["by_confidence_tier"]
    tiers_with_data = [
        (k, v)
        for k, v in conf_stats.items()
        if (v.get("win", 0) + v.get("loss", 0)) >= 3
    ]
    if len(tiers_with_data) >= 2:
        high_tier = max(tiers_with_data, key=lambda x: x[0])
        low_tier = min(tiers_with_data, key=lambda x: x[0])
        if high_tier[1].get("win_rate", 0) < low_tier[1].get("win_rate", 0):
            warnings.append(
                f"⚠️ Confidence معکوس: tier {high_tier[0]} → "
                f"{high_tier[1].get('win_rate', 0)}% ولی "
                f"tier {low_tier[0]} → {low_tier[1].get('win_rate', 0)}%"
            )

    # ─── هشدار ۴: تله معکوس ───
    trap_s = report["by_trap"].get("had_trap", {})
    notrap_s = report["by_trap"].get("no_trap", {})
    if trap_s.get("win_rate", 0) > notrap_s.get("win_rate", 0) + 5:
        warnings.append(
            f"⚠️ trap معکوس: با تله {trap_s.get('win_rate', 0)}% "
            f"بهتر از بدون تله {notrap_s.get('win_rate', 0)}%"
        )

    # ─── هشدار ۵: pending زیاد ───
    if total > 0:
        pending_pct = pending / total * 100
        if pending_pct > 30:
            warnings.append(
                f"⚠️ {pending_pct:.1f}% سیگنال‌ها pending موندن "
                f"(مشکوک به scheduler)"
            )

    report["warnings"] = warnings

    return report


# ═══════════════════════════════════════════════════════════
# نمایش رنگی در ترمینال
# ═══════════════════════════════════════════════════════════
def _win_rate_color(rate: float) -> str:
    if rate >= 55:
        return C.GREEN
    if rate >= 45:
        return C.YELLOW
    return C.RED


def print_report(report: dict) -> None:
    """چاپ گزارش با رنگ در ترمینال"""

    print()
    print(f"{C.BOLD}{C.MAGENTA}{'█' * 62}{C.RESET}")
    print(
        f"{C.BOLD}{C.MAGENTA}█  🔍  گزارش تشخیصی سیگنال‌های Trademun              █{C.RESET}"
    )
    print(
        f"{C.BOLD}{C.MAGENTA}█  📅  {report['meta']['generated_at'][:19]}                  █{C.RESET}"
    )
    print(f"{C.BOLD}{C.MAGENTA}{'█' * 62}{C.RESET}")

    # ═══ ۱. کلیات ═══
    _section("کلیات", "📊")
    o = report["overall"]
    _row("کل سیگنال‌ها", o["total"], C.BOLD)
    _row("نتایج قطعی (win/loss)", o["closed_win_loss"])
    _row("برد", o["wins"], C.GREEN)
    _row("باخت", o["losses"], C.RED)
    _row("منقضی", o["expired"], C.YELLOW)
    _row("در انتظار", o["pending"], C.DIM)
    _row(
        "نرخ برد (win/loss)",
        f"{o['win_rate']}%",
        _win_rate_color(o["win_rate"]) + C.BOLD,
    )

    # ═══ ۲. توزیع نتیجه ═══
    _section("توزیع کامل نتایج", "🎲")
    for outcome, count in sorted(
        report["outcome_distribution"].items(),
        key=lambda x: -x[1],
    ):
        color = (
            C.GREEN if "win" in outcome else (C.RED if "loss" in outcome else C.YELLOW)
        )
        _row(outcome, count, color)

    # ═══ ۳. جهت ═══
    _section("به تفکیک جهت (LONG/SHORT)", "🎯")
    for d, v in report["by_direction"].items():
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        print(
            f"  {C.BOLD}{d:10}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"exp: {v['expired']:>4} | "
            f"pend: {v['pending']:>3} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    # ═══ ۴. سطح confidence ═══
    _section("به تفکیک سطح Confidence", "📈")
    tier_order = ["0-29", "30-39", "40-49", "50-59", "60-79", "80-100"]
    for tier in tier_order:
        v = report["by_confidence_tier"].get(tier)
        if not v:
            continue
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        print(
            f"  {C.BOLD}{tier:8}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"exp: {v['expired']:>4} | "
            f"pend: {v['pending']:>3} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    # ═══ ۵. is_weak ═══
    _section("تفکیک is_weak (ضعیف/قطعی)", "⚖️")
    for k, v in report["by_is_weak"].items():
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        label = "ضعیف" if k == "weak" else "قطعی"
        print(
            f"  {C.BOLD}{label:10}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"exp: {v['expired']:>4} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    # ═══ ۶. تله ═══
    _section("تفکیک تله‌ها", "🚨")
    for k, v in report["by_trap"].items():
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        label = "با تله" if k == "had_trap" else "بدون تله"
        print(
            f"  {C.BOLD}{label:12}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"exp: {v['expired']:>4} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    if report["by_trap_type"]:
        _subtitle("نوع تله")
        for k, v in report["by_trap_type"].items():
            wr = v["win_rate"]
            color = _win_rate_color(wr)
            print(
                f"  • {C.BOLD}{k:18}{C.RESET} | "
                f"کل: {v['total']:>3} | "
                f"برد: {v['win']} | "
                f"باخت: {v['loss']} | "
                f"exp: {v['expired']} | "
                f"WR: {color}{wr}%{C.RESET}"
            )

    # ═══ ۷. رژیم ═══
    _section("به تفکیک رژیم بازار", "🌊")
    for r, v in report["by_regime"].items():
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        print(
            f"  {C.BOLD}{r:15}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"exp: {v['expired']:>4} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    # ═══ ۸. TF ═══
    _section("به تفکیک تایم‌فریم", "⏱")
    for tf, v in report["by_tf"].items():
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        print(
            f"  {C.BOLD}{tf:10}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"exp: {v['expired']:>4} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    # ═══ ۹. صرافی ═══
    _section("به تفکیک صرافی", "🏦")
    for src, v in report["by_source"].items():
        wr = v["win_rate"]
        color = _win_rate_color(wr)
        print(
            f"  {C.BOLD}{src:12}{C.RESET} | "
            f"کل: {v['total']:>4} | "
            f"برد: {C.GREEN}{v['win']:>3}{C.RESET} | "
            f"باخت: {C.RED}{v['loss']:>3}{C.RESET} | "
            f"WR: {color}{wr:>5}%{C.RESET}"
        )

    # ═══ ۱۰. Trend Correct ═══
    _section("همبستگی trend_correct با نتیجه", "🧭")
    tc = report["trend_correct"]
    print(f"  {C.GREEN}trend_correct=True{C.RESET}:")
    _row("  برد", tc["true_wins"], C.GREEN)
    _row("  باخت", tc["true_losses"], C.RED)
    _row("  نرخ برد", f"{tc['true_win_rate']}%", _win_rate_color(tc["true_win_rate"]))
    print()
    print(f"  {C.RED}trend_correct=False{C.RESET}:")
    _row("  برد", tc["false_wins"], C.GREEN)
    _row("  باخت", tc["false_losses"], C.RED)
    _row("  نرخ برد", f"{tc['false_win_rate']}%", _win_rate_color(tc["false_win_rate"]))

    # ═══ ۱۱. expired_bias ═══
    _section("توزیع expired_bias", "⏰")
    for bias, count in report["by_expired_bias"].items():
        color = C.GREEN if bias == "win" else (C.RED if bias == "loss" else C.YELLOW)
        _row(bias, count, color)

    # ═══ ۱۲. Pending ═══
    _section("سیگنال‌های در انتظار (pending)", "⏳")
    pa = report["pending_analysis"]
    _row("کل pending", report["overall"]["pending"], C.YELLOW)
    if pa["by_tf"]:
        _subtitle("به تفکیک TF")
        for tf, count in pa["by_tf"].items():
            _row(tf, count)

    # ═══ ۱۳. هشدارها ═══
    if report["warnings"]:
        _section("⚠️  هشدارهای بحرانی", "🚨")
        for w in report["warnings"]:
            print(f"  {C.BG_RED}{C.WHITE} {w} {C.RESET}")
    else:
        print()
        print(f"{C.BG_GREEN}{C.WHITE} ✅ هیچ هشدار بحرانی‌ای یافت نشد {C.RESET}")

    print()
    print(f"{C.BOLD}{C.MAGENTA}{'█' * 62}{C.RESET}")
    print(
        f"{C.BOLD}{C.MAGENTA}█  پایان گزارش                                      █{C.RESET}"
    )
    print(f"{C.BOLD}{C.MAGENTA}{'█' * 62}{C.RESET}")
    print()


# ═══════════════════════════════════════════════════════════
# ذخیره‌ی JSON
# ═══════════════════════════════════════════════════════════
def save_report_json(report: dict, path: Path) -> None:
    """ذخیره‌ی گزارش به فایل JSON"""
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"{C.GREEN}✅ گزارش JSON ذخیره شد: {C.BOLD}{path}{C.RESET}")


# ═══════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="گزارش تشخیصی سیگنال‌های Trademun",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال‌ها:
  python scripts/signal_audit.py
  python scripts/signal_audit.py --file trademun_signals.json
  python scripts/signal_audit.py --output custom_report.json
  python scripts/signal_audit.py --no-color
""",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="فایل JSON سیگنال‌ها (اگه ندید، از دیتابیس لوکال می‌خونه)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="مسیر فایل گزارش (پیش‌فرض: signal_audit_report.json)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="غیرفعال کردن رنگ در ترمینال",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="فقط فایل JSON ذخیره کن، چیزی چاپ نکن",
    )

    args = parser.parse_args()

    if args.no_color:
        C.disable()

    # ═══ ۱. بارگذاری ═══
    signals: list[NormalizedSignal] = []

    if args.file:
        path = Path(args.file)
        if not path.exists():
            logger.error(f"❌ فایل پیدا نشد: {path}")
            sys.exit(1)
        print(f"{C.CYAN}📂 بارگذاری از فایل: {path}{C.RESET}")
        signals = load_from_json(path)
    else:
        print(f"{C.CYAN}💾 بارگذاری از دیتابیس لوکال...{C.RESET}")
        try:
            signals = load_from_db()
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری از DB: {e}")
            print()
            print(f"{C.YELLOW}راهنما: از --file برای فایل JSON استفاده کن{C.RESET}")
            sys.exit(1)

    print(f"{C.GREEN}✅ {len(signals)} سیگنال بارگذاری شد{C.RESET}")

    if not signals:
        print(f"{C.YELLOW}⚠️ هیچ سیگنالی برای آنالیز نیست{C.RESET}")
        sys.exit(0)

    # ═══ ۲. آنالیز ═══
    report = analyze_signals(signals)

    # ═══ ۳. چاپ گزارش ═══
    if not args.quiet:
        print_report(report)

    # ═══ ۴. ذخیره ═══
    output_path = (
        Path(args.output) if args.output else _ROOT / "signal_audit_report.json"
    )
    save_report_json(report, output_path)


if __name__ == "__main__":
    main()
