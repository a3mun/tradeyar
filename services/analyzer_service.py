"""
services/analyzer_service.py
لایه تحلیل — با کش + fingerprint
============================================================
نسخه ۳.۰: کش تحلیل بر اساس کندل آخر
"""

import logging
from datetime import datetime
from typing import Optional

from core.analyzer import (
    analyze_symbol,
    build_analysis_paragraph,
    build_checklist_weighted,
    compute_fear_greed,
)
from core.contracts import TF_NAMES

from services.cache import analysis_cache, get_ttl, make_fingerprint
from services.data_service import fetch_ohlcv, fetch_quote

logger = logging.getLogger(__name__)


def _fear_greed_label(value: float) -> tuple[str, str, str]:
    if value <= 20:
        return ("ترس شدید", "red", "😱")
    elif value <= 40:
        return ("ترس", "red", "😰")
    elif value <= 60:
        return ("خنثی", "yellow", "😐")
    elif value <= 80:
        return ("طمع", "green", "🤑")
    else:
        return ("طمع شدید", "green", "🚀")


def _build_ai_export(ticker, name, tf_name, analysis, tfs_data) -> str:
    """خروجی AI — خلاصه نسخه"""
    if not analysis:
        return ""
    lines = [
        f"# {name} ({ticker}) — {tf_name}",
        f"سیگنال: {analysis.get('signal', '—')} · "
        f"اطمینان: {analysis.get('confidence', 0):.0f}% · "
        f"قیمت: {analysis.get('price', 0):.2f}",
        f"رژیم: {analysis.get('regime', '—')} · "
        f"اجماع: {analysis.get('consensus', '—')}",
        "",
        "## دلایل گروه‌ها:",
    ]
    for g_key, g_data in (analysis.get("groups") or {}).items():
        lines.append(
            f"- {g_key}: رأی={g_data.get('vote', 0)} "
            f"قدرت={g_data.get('strength_fa', '')}"
        )
        for r in g_data.get("reasons", [])[:3]:
            lines.append(f"  · {r}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# تحلیل با کش هوشمند
# ═══════════════════════════════════════════════════════════
def analyze(
    ticker: str,
    source: str = "nobitex",
    tf_name: str = "۵ دقیقه",
    market_type: str = "futures",
    risk_profile: str = "aggressive",
    ticker_name: str = "",
    include_extras: bool = True,
    use_cache: bool = True,
) -> Optional[dict]:
    """تحلیل با کش بر اساس fingerprint کندل"""

    # ═══ ۰. چک TSETMC (فقط روزانه) ═══
    is_iranian_stock = bool(ticker) and not ticker[0].isascii()
    if is_iranian_stock:
        if tf_name != "روزانه":
            logger.debug(f"[Analyzer] TSETMC فقط روزانه — رد {ticker} {tf_name}")
            return None
        source = "tsetmc"  # ─── اصلاح خودکار منبع ───

    # ═══ ۱. دیتا ═══
    df = fetch_ohlcv(ticker, tf_name, source, use_cache=use_cache)
    if df is None or df.empty:
        return None

    # ═══ ۲. fingerprint ───
    fingerprint = make_fingerprint(df) if use_cache else ""
    cache_key = f"analysis:{ticker}:{source}:{tf_name}:{market_type}:{risk_profile}"
    fp_key = f"{cache_key}:fp"

    if use_cache:
        cached_fp = analysis_cache.get(fp_key)
        if cached_fp == fingerprint:
            cached_result = analysis_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"[Analyzer] کش hit: {ticker} {tf_name}")
                return cached_result

    # ═══ ۳. تحلیل ═══
    try:
        result = analyze_symbol(
            df=df,
            risk_profile=risk_profile,
            tf_name=tf_name,
            tfs_data=None,
            market_type=market_type,
            ticker=ticker,
        )
    except Exception as e:
        logger.error(f"[Analyzer] خطا در analyze_symbol: {e}")
        return None

    if result is None:
        return None

    sl_tp = result.get("sl_tp") or {}

    output = {
        "ok": True,
        "ticker": ticker,
        "name": ticker_name or ticker,
        "source": source,
        "timeframe": tf_name,
        "market_type": market_type,
        "risk_profile": risk_profile,
        "price": result.get("price", 0.0),
        "signal": result.get("signal", "خنثی"),
        "direction": result.get("direction", "neutral"),
        "confidence": result.get("confidence", 0),
        "confidence_tier": result.get("confidence_tier", "neutral"),
        "consensus": result.get("consensus", "neutral"),
        "regime": result.get("regime", "range"),
        "action_fa": result.get("action_fa", ""),
        "explanation": result.get("explanation", ""),
        "sl": sl_tp.get("sl"),
        "tp": sl_tp.get("tp"),
        "rr": result.get("rr"),
        "atr": float(result.get("atr", 0.0)),
        "atr_mult_sl": float(sl_tp.get("effective_sl_mult", 1.0)),
        "atr_mult_tp": float(sl_tp.get("effective_tp_mult", 1.5)),
        "atr": result.get("atr", 0.0),
        "atr_mult_sl": sl_tp.get("effective_sl_mult", 1.0),
        "atr_mult_tp": sl_tp.get("effective_tp_mult", 1.5),
        "support": result.get("support", 0.0),
        "resistance": result.get("resistance", 0.0),
        "pivots": result.get("pivots", {}),
        "swings": result.get("swings", {}),
        "fibonacci": result.get("fibonacci", {}),
        "groups": result.get("groups", {}),
        "votes_long": result.get("votes_long", 0),
        "votes_short": result.get("votes_short", 0),
        "votes_neutral": result.get("votes_neutral", 0),
        "reasons": result.get("reasons", []),
        "scenarios": result.get("scenarios", []),
        "traps": result.get("traps", {}),
        "traps_summary": result.get("traps_summary", {}),
        "divergence": result.get("divergence", {}),
        "multi_tf_info": result.get("multi_tf_info", ""),
        "multi_tf_ok": result.get("multi_tf_ok", True),
        "neutral_explain": result.get("neutral_explain", {}),
        "deep_analysis": "",
        "checklist": {},
        "ai_export": "",
        "close_series": result.get("close_series", []),
        "fingerprint": fingerprint,
    }

    if include_extras:
        try:
            tfs_one = {tf_name: result}
            output["deep_analysis"] = build_analysis_paragraph(
                ticker=ticker,
                name=ticker_name or ticker,
                tfs=tfs_one,
                gsr=None,
                risk_profile=risk_profile,
                tf_name=tf_name,
            )
        except Exception as e:
            logger.warning(f"[Analyzer] deep_analysis: {e}")

        try:
            tfs_one = {tf_name: result}
            items, pct, final, color = build_checklist_weighted(
                tfs_one, main_tf=tf_name
            )
            output["checklist"] = {
                "items": items,
                "percentage": pct,
                "final": final,
                "final_color": color,
            }
        except Exception as e:
            logger.warning(f"[Analyzer] checklist: {e}")

        try:
            output["ai_export"] = _build_ai_export(
                ticker=ticker,
                name=ticker_name or ticker,
                tf_name=tf_name,
                analysis=result,
                tfs_data={tf_name: result},
            )
        except Exception as e:
            logger.warning(f"[Analyzer] ai_export: {e}")

    # ═══ override market_type و risk_profile (فقط برای خروجی) ═══
    output["market_type"] = market_type
    output["risk_profile"] = risk_profile

    # ═══ ۴. ذخیره در کش ═══
    # ═══ ثبت خودکار سیگنال در دیتابیس ═══
    try:
        from services.signal_recorder import record_signal

        record_signal(
            ticker=ticker,
            name=ticker_name or ticker,
            signal=output["signal"],
            price=output["price"],
            tf_name=tf_name,
            source=source,
            market_type=market_type,
            risk_profile=risk_profile,
            sl_tp={
                "sl": output.get("sl"),
                "tp": output.get("tp"),
                "type": output.get("direction"),
            },
            direction=output.get("direction", "neutral"),
            confidence=output.get("confidence", 0),
            consensus=output.get("consensus", "neutral"),
            regime=output.get("regime", "range"),
            rr=output.get("rr"),
            traps=output.get("traps", {}),
        )
    except Exception as e:
        logger.debug(f"[Analyzer] record_signal: {e}")

    if use_cache:
        ttl = get_ttl(tf_name)
        # ─── فقط اگه extras داشت، کش کن ───
        if include_extras:
            analysis_cache.set(cache_key, output, ttl)
        analysis_cache.set(fp_key, fingerprint, ttl)

    return output


# ═══════════════════════════════════════════════════════════
# چند TF
# ═══════════════════════════════════════════════════════════
def analyze_multi_tf(
    ticker: str,
    source: str = "nobitex",
    tf_list: list[str] = None,
    market_type: str = "spot",
    risk_profile: str = "aggressive",
    ticker_name: str = "",
) -> dict:
    if tf_list is None:
        tf_list = list(TF_NAMES)

    results = {}
    for tf in tf_list:
        try:
            r = analyze(
                ticker=ticker,
                source=source,
                tf_name=tf,
                market_type=market_type,
                risk_profile=risk_profile,
                ticker_name=ticker_name,
                include_extras=False,
            )
            if r:
                results[tf] = r
        except Exception as e:
            logger.warning(f"[Analyzer] {tf}: {e}")

    return results


def deep_analysis(
    ticker, name, tfs, gsr=None, risk_profile="aggressive", tf_name="۵ دقیقه"
):
    try:
        return build_analysis_paragraph(
            ticker=ticker,
            name=name,
            tfs=tfs,
            gsr=gsr,
            risk_profile=risk_profile,
            tf_name=tf_name,
        )
    except Exception as e:
        logger.error(f"[Analyzer] deep_analysis: {e}")
        return "خطا در تولید تحلیل."


def checklist(tfs, main_tf="۵ دقیقه"):
    try:
        items, pct, final, color = build_checklist_weighted(tfs, main_tf)
        return {"items": items, "percentage": pct, "final": final, "final_color": color}
    except Exception as e:
        logger.error(f"[Analyzer] checklist: {e}")
        return {"items": [], "percentage": 0, "final": "", "final_color": "yellow"}


def fear_greed(ticker, source="nobitex"):
    df = fetch_ohlcv(ticker, "۱ ساعت", source)
    if df is None or df.empty:
        return None
    try:
        value = compute_fear_greed(df)
        label, color, icon = _fear_greed_label(value)
        return {
            "ok": True,
            "ticker": ticker,
            "value": round(value, 1),
            "label": label,
            "color": color,
            "icon": icon,
        }
    except Exception as e:
        logger.error(f"[Analyzer] fear_greed: {e}")
        return None


def quote(ticker, source="nobitex"):
    """قیمت لحظه‌ای — سبک و سریع"""
    return fetch_quote(ticker, source)
