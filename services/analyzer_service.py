"""
services/analyzer_service.py
لایه تحلیل — با کش + fingerprint
============================================================
نسخه ۳.۱: کارمزد واقعی per IRT/USDT
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from core.data_fetcher import get_data_source

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# عمق بازار — فعال/غیرفعال
# ═══════════════════════════════════════════════════════════
_ORDERBOOK_ENABLED = True


def _orderbook_enabled() -> bool:
    return _ORDERBOOK_ENABLED


def set_orderbook_enabled(enabled: bool) -> None:
    """روشن/خاموش کردن عمق بازار (برای تست یا بار سنگین)"""
    global _ORDERBOOK_ENABLED
    _ORDERBOOK_ENABLED = bool(enabled)


def _is_iranian(ticker: str) -> bool:
    """آیا این نماد ایرانی است (تومانی/ریالی)؟"""
    if not ticker:
        return False
    upper = ticker.upper()
    if upper.endswith("-IRT") or upper.endswith("-RLS"):
        return True
    return not ticker[0].isascii()


def _resolve_live_price(ticker: str, source: str, fallback: float) -> float:
    """
    قیمت زنده — برای TSETMC از endpoint زنده، برای بقیه از fallback.

    ⚠️ چرا لازم است:
        TSETMC کندل امروز را تا پایان معاملات نمی‌دهد. یعنی
        آخرین کندل DataFrame = دیروز. برای نمایش قیمت واقعی
        امروز باید از ClosingPriceInfo استفاده کنیم.
    """
    # ─── TSETMC: نمادهای غیر-ASCII ───
    is_iranian_stock = bool(ticker) and not ticker[0].isascii()
    if not (source == "tsetmc" or is_iranian_stock):
        return float(fallback or 0.0)

    try:
        from core.tsetmc_fetcher import fetch_tsetmc_live_quote

        live = fetch_tsetmc_live_quote(ticker)
        if live and live.get("price"):
            return float(live["price"])
    except Exception as e:
        logger.debug(f"[Analyzer] live price {ticker}: {e}")

    return float(fallback or 0.0)


def _build_ai_export(
    ticker: str,
    name: str,
    tf_name: str,
    analysis: dict,
    tfs_data: dict | None = None,
) -> str:
    """خروجی **خام** برای هوش مصنوعی — نسخه ۳.۱"""
    if not analysis:
        return ""

    lines: list[str] = []
    L = lines.append

    L(f"# تحلیل خام: {name} ({ticker}) — {tf_name}")
    L("")

    price = analysis.get("price", 0)
    signal = analysis.get("signal", "—")
    confidence = analysis.get("confidence", 0)
    direction = analysis.get("direction", "neutral")
    regime = analysis.get("regime", "range")
    consensus = analysis.get("consensus", "neutral")
    market_type = analysis.get("market_type", "spot")
    source = analysis.get("source_used") or analysis.get("source") or "—"

    L("## قیمت و وضعیت")
    L(f"- قیمت فعلی: {price}")
    L(f"- تایم‌فریم: {tf_name}")
    L(f"- بازار: {'اسپات' if market_type == 'spot' else 'فیوچرز'}")
    L(f"- منبع دیتا: {source}")
    L(f"- سیگنال فعلی سیستم: {signal} ({confidence}%)")
    L(f"- جهت سیستم: {direction}")
    L(f"- وضعیت بازار: {regime}")
    L(f"- اجماع سیستم: {consensus}")
    L("")

    # ═══ اندیکاتورهای تکنیکال (خام) ═══
    L("## اندیکاتورهای تکنیکال (خام)")

    L("### مومنتوم")
    _mom_keys = [
        ("rsi", "RSI(14)"),
        ("stoch_k", "Stochastic %K"),
        ("stoch_d", "Stochastic %D"),
        ("willr", "Williams %R"),
    ]
    for key, label in _mom_keys:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")

    L("### روند")
    _trend_keys = [
        ("ema200", "EMA200"),
        ("macd_hist", "MACD Histogram"),
        ("adx", "ADX(14)"),
    ]
    for key, label in _trend_keys:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")

    L("### نوسان")
    _vol_keys = [
        ("atr", "ATR(14)"),
        ("bb_upper", "Bollinger Upper"),
        ("bb_lower", "Bollinger Lower"),
    ]
    for key, label in _vol_keys:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")

    L("### حجم و جریان پول")
    _has_vol = False
    _vwap = analysis.get("vwap")
    if _vwap is not None:
        L(f"- VWAP: {_vwap}")
        _has_vol = True
    if not _has_vol:
        L("- (داده‌ی حجم در دسترس نیست)")
    L("")

    # ═══ سطوح کلیدی ═══
    support = analysis.get("support")
    resistance = analysis.get("resistance")
    L("## سطوح کلیدی")
    if resistance is not None and price:
        L(f"- مقاومت نزدیک: {resistance} ({(resistance - price) / price * 100:+.3f}%)")
    if support is not None and price:
        L(f"- حمایت نزدیک: {support} ({(support - price) / price * 100:+.3f}%)")

    pivots = analysis.get("pivots") or {}
    if pivots:
        L("- Pivot Points:")
        for k, v in pivots.items():
            L(f"  - {k}: {v}")
    L("")

    # ═══ ATR ═══
    atr = analysis.get("atr")
    if atr:
        L("## ATR (نوسان)")
        L(f"- ATR: {atr}")
        if price:
            L(f"- ATR%: {atr / price * 100:.3f}%")
        L("")

    # ═══ عمق بازار ═══
    ob = analysis.get("orderbook")
    if ob and ob.get("imbalance") is not None:
        L("## عمق بازار")
        L(f"- imbalance: {ob['imbalance']}")
        L(f"- فشار: {ob.get('pressure_fa', '—')}")
        L(f"- spread_pct: {ob.get('spread_pct', 0)}%")
        bb = ob.get("best_bid")
        ba = ob.get("best_ask")
        if bb:
            L(f"- best_bid: {bb}")
        if ba:
            L(f"- best_ask: {ba}")
        wall = ob.get("wall")
        if wall:
            L(
                f"- دیوار سفارش: سمت {wall.get('side')} در "
                f"{wall.get('price')} ({wall.get('ratio')}x)"
            )
        L("")

    # ═══ اقتصاد معامله ═══
    L("## اقتصاد معامله")
    fee_pct = analysis.get("fee_pct")
    if fee_pct is not None:
        L(f"- کارمزد رفت‌وبرگشتی: {fee_pct}%")
        exec_cost = analysis.get("execution_cost")
        if exec_cost:
            L(f"- کارمزد خالص: {exec_cost.get('fee_pct')}%")
            L(f"- هزینه اسپرد: {exec_cost.get('spread_cost_pct')}%")
            L(f"- اسلیپیج: {exec_cost.get('slippage_pct')}%")
            L(f"- مجموع هزینه: {exec_cost.get('total_pct')}%")
        be = analysis.get("breakeven_pct")
        if be is not None:
            L(f"- نقطه سربه‌سر: {be}%")
    else:
        L("- (سیگنال خنثی — هزینه‌ی معامله محاسبه نشد)")
    L("")

    # ═══ SL/TP ═══
    sl = analysis.get("sl")
    tp = analysis.get("tp")
    if sl is not None and tp is not None and price:
        L("## SL/TP")
        L(f"- ورود: {price}")
        L(f"- حد ضرر: {sl} ({(sl - price) / price * 100:+.2f}%)")
        L(f"- هدف: {tp} ({(tp - price) / price * 100:+.2f}%)")
        rr_gross = analysis.get("rr_gross") or analysis.get("rr")
        rr_net = analysis.get("rr_net")
        if rr_gross is not None:
            L(f"- R:R خام: {rr_gross}")
        if rr_net is not None:
            L(f"- R:R خالص: {rr_net}")
        L("")

    # ═══ موقعیت در بازه ═══
    fundamental = analysis.get("fundamental_lines") or []
    fund_raw = [f for f in fundamental if "📍" in f or "سقف" in f or "فضای" in f]
    if fund_raw:
        L("## موقعیت و فضای حرکت")
        for line in fund_raw:
            clean = line.replace("**", "").replace("*", "").replace("ℹ️", "").strip()
            if clean:
                L(f"- {clean}")
        L("")

    # ═══ تله‌ها ═══
    traps = analysis.get("traps") or {}
    active_traps = [
        k for k, v in traps.items() if isinstance(v, dict) and v.get("active")
    ]
    if active_traps:
        L("## تله‌های شناسایی‌شده")
        for k in active_traps:
            info = traps[k]
            L(f"- {k}: {info.get('reason', '')}")
        L("")

    L("---")
    L("⚠️ این داده خام است. تحلیل نهایی رو خودت بر اساس این اعداد و دانش انجام بده.")

    return "\n".join(lines)


def _refresh_live_fields(cached: dict, df) -> dict:
    """فیلدهای قیمت‌محور را از دیتافریم تازه به نتیجه‌ی کش‌شده می‌چسباند."""
    try:
        if df is None or df.empty:
            return cached

        # 🔴 فاز ۸ — برای TSETMC، قیمت زنده از endpoint جدا
        ticker_for_quote = cached.get("ticker", "")
        source_for_quote = cached.get("source_used") or cached.get("source", "")
        if source_for_quote == "tsetmc" or (
            ticker_for_quote and not ticker_for_quote[0].isascii()
        ):
            try:
                from core.tsetmc_fetcher import fetch_tsetmc_live_quote

                live = fetch_tsetmc_live_quote(ticker_for_quote)
                if live and live.get("price"):
                    fresh_price = float(live["price"])
                else:
                    fresh_price = float(df["close"].iloc[-1])
            except Exception:
                fresh_price = float(df["close"].iloc[-1])
        else:
            fresh_price = float(df["close"].iloc[-1])
    except Exception:
        return cached

    out = dict(cached)
    out["price"] = fresh_price

    try:
        out["close_series"] = [float(x) for x in df["close"].tail(30).tolist()]
    except Exception as e:
        logger.warning(f"[Analyzer] _refresh: {e!r}")

    # ═══ زمینه‌ی بنیادی/ساختاری ═══
    try:
        from core.analyzer import _build_fundamental_context
        from core.contracts import get_fee_rate as _gfr

        _fee = cached.get("fee_pct")
        if _fee is None:
            _mt = cached.get("market_type", "spot")
            _fee = (
                _gfr(
                    cached.get("source_used") or cached.get("source") or "nobitex",
                    market_type=_mt,
                    ticker=cached.get("ticker", ""),
                )
                * 100
            )

        out["fundamental_lines"] = _build_fundamental_context(
            df=df,
            r_main=cached,
            ticker=cached.get("ticker", ""),
            is_iranian=_is_iranian(cached.get("ticker", "")),
            unit="تومان",
            fee_pct=_fee,
        )
    except Exception as e:
        logger.warning(f"[Analyzer] _refresh fundamental: {e!r}")

    # ═══ ai_export بازتولید ═══
    try:
        out["ai_export"] = _build_ai_export(
            ticker=cached.get("ticker", ""),
            name=cached.get("name", ""),
            tf_name=cached.get("timeframe", "۵ دقیقه"),
            analysis=out,
            tfs_data=None,
        )
    except Exception as e:
        logger.warning(f"[Analyzer] _refresh ai_export: {e!r}")

    return out


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


# ═══════════════════════════════════════════════════════════
# ثبت سیگنال — تابع امن برای استفاده در چندجا
# ═══════════════════════════════════════════════════════════
def _record_signal_safe(
    ticker: str,
    ticker_name: str,
    tf_name: str,
    source: str,
    market_type: str,
    risk_profile: str,
    output: dict,
    skip_record: bool,
) -> None:
    """ثبت سیگنال با catch خطا — برای cache miss و cache hit."""
    if skip_record:
        return

    try:
        from services.signal_recorder import record_signal

        _is_irt = bool(ticker) and (
            "-IRT" in ticker.upper()
            or "-RLS" in ticker.upper()
            or (ticker and not ticker[0].isascii())
        )

        record_signal(
            ticker=ticker,
            name=ticker_name or ticker,
            signal=output.get("signal", ""),
            price=output.get("price", 0),
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
            rr_net=output.get("rr_net"),
            fee_pct=output.get("fee_pct"),
            fee_ratio=output.get("fee_ratio"),
            breakeven_pct=output.get("breakeven_pct"),
            is_worthwhile=output.get("is_worthwhile"),
            timeframe_viable=output.get("timeframe_viable"),
            rr_decay_pct=output.get("rr_decay_pct"),
            execution_cost=output.get("execution_cost"),
            orderbook_available=bool(output.get("orderbook")),
            trade_side_irt=_is_irt,
        )
    except Exception as e:
        logger.debug(f"[Analyzer] record_signal: {e}")


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
    skip_record: bool = False,
) -> Optional[dict]:
    """تحلیل یک نماد در یک تایم‌فریم — با کش بر پایه‌ی fingerprint کندل بسته."""
    if not ticker:
        return None

    # ═══ ۰. اعتبارسنجی منبع ═══
    from core.contracts import is_active_source, is_planned_source

    if not is_active_source(source) and not is_planned_source(source):
        logger.warning(f"[Analyzer] منبع ناشناخته «{source}» — تحلیل رد شد")
        return None

    # ═══ ۰.۱ TSETMC: فقط روزانه ═══
    is_iranian_stock = not ticker[0].isascii()
    if is_iranian_stock:
        if tf_name != "روزانه":
            logger.debug(f"[Analyzer] TSETMC فقط روزانه — رد {ticker} {tf_name}")
            return None
        source = "tsetmc"

    # ═══ ۱. دیتا ═══
    df = fetch_ohlcv(ticker, tf_name, source, use_cache=use_cache)
    if df is None or df.empty:
        return None

    data_source = get_data_source(df, source)

    # ═══ ۲. fingerprint ═══
    fingerprint = make_fingerprint(df, tf_name) if use_cache else ""
    cache_key = f"analysis:{ticker}:{source}:{tf_name}:{market_type}:{risk_profile}"
    fp_key = f"{cache_key}:fp"

    if use_cache:
        cached_fp = analysis_cache.get(fp_key)
        if cached_fp == fingerprint:
            cached_result = analysis_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"[Analyzer] کش hit: {ticker} {tf_name}")
                out = _refresh_live_fields(cached_result, df)
                out["source_used"] = data_source
                out["is_fallback"] = data_source != source
                out.pop("orderbook", None)

                # 🔴 نسخه ۳.۰: روی cache hit هم ثبت کن
                # dedup_key جلوی تکرار رو می‌گیره
                _record_signal_safe(
                    ticker,
                    ticker_name,
                    tf_name,
                    source,
                    market_type,
                    risk_profile,
                    out,
                    skip_record,
                )

                return out

    # ═══ ۲.۵ عمق بازار ═══
    orderbook = None
    if include_extras and _orderbook_enabled():
        try:
            from core.orderbook import get_orderbook

            orderbook = get_orderbook(ticker, data_source, depth=20)
        except Exception:
            logger.debug(f"[Analyzer] عمق بازار {ticker} در دسترس نبود")

    # ═══ ۳. تحلیل ═══
    try:
        result = analyze_symbol(
            df=df,
            risk_profile=risk_profile,
            tf_name=tf_name,
            tfs_data=None,
            market_type=market_type,
            ticker=ticker,
            source=data_source,
            orderbook=orderbook,
        )
    except Exception as e:
        logger.error(f"[Analyzer] خطا در analyze_symbol: {e}")
        return None

    if result is None:
        return None

    sl_tp = result.get("sl_tp") or {}

    # ═══ زمینه‌ی بنیادی/ساختاری ═══
    if include_extras:
        try:
            from core.analyzer import _build_fundamental_context
            from core.contracts import get_fee_rate as _gfr

            effective_fee_pct = sl_tp.get("fee_pct")
            if effective_fee_pct is None:
                effective_fee_pct = (
                    _gfr(
                        data_source or "nobitex",
                        market_type=market_type,
                        ticker=ticker,
                    )
                    * 100
                )

            result["fundamental_lines"] = _build_fundamental_context(
                df=df,
                r_main=result,
                ticker=ticker,
                is_iranian=_is_iranian(ticker),
                unit="تومان",
                fee_pct=effective_fee_pct,
            )
        except Exception as e:
            logger.warning(f"[Analyzer] زمینه‌ی بنیادی محاسبه نشد: {e!r}")

    output = {
        "ok": True,
        "ticker": ticker,
        "name": ticker_name or ticker,
        "source": source,
        "source_requested": source,
        "source_used": data_source,
        "is_fallback": data_source != source,
        "timeframe": tf_name,
        "market_type": market_type,
        "risk_profile": risk_profile,
        "price": _resolve_live_price(ticker, data_source, result.get("price", 0.0)),
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
        "rr_gross": sl_tp.get("rr_gross"),
        "rr_net": sl_tp.get("rr_net"),
        "fee_pct": sl_tp.get("fee_pct"),
        "fee_ratio": sl_tp.get("fee_ratio"),
        "breakeven_pct": sl_tp.get("breakeven_pct"),
        "is_worthwhile": sl_tp.get("is_worthwhile"),
        "timeframe_viable": sl_tp.get("timeframe_viable"),
        "sl_tp_scaled": sl_tp.get("sl_tp_scaled", False),
        "scale_factor": sl_tp.get("scale_factor"),
        "scale_reason": sl_tp.get("scale_reason"),
        "original_sl": sl_tp.get("original_sl"),
        "original_tp": sl_tp.get("original_tp"),
        "rr_decay_pct": sl_tp.get("rr_decay_pct"),
        "execution_cost": sl_tp.get("execution_cost"),
        "sl_tp_type": sl_tp.get("type"),
        "atr": float(result.get("atr") or 0.0),
        "atr_mult_sl": float(sl_tp.get("effective_sl_mult") or 1.0),
        "atr_mult_tp": float(sl_tp.get("effective_tp_mult") or 1.5),
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
        "orderbook": result.get("orderbook"),
        "fundamental_lines": result.get("fundamental_lines") or [],
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
                analysis={**result, **output},
                tfs_data={tf_name: result},
            )
        except Exception as e:
            logger.warning(f"[Analyzer] ai_export: {e}")

    output["market_type"] = market_type
    output["risk_profile"] = risk_profile

    # ═══ ثبت خودکار سیگنال ═══
    _record_signal_safe(
        ticker,
        ticker_name,
        tf_name,
        source,
        market_type,
        risk_profile,
        output,
        skip_record,
    )

    if use_cache:
        ttl = get_ttl(tf_name)
        if include_extras:
            analysis_cache.set(cache_key, output, ttl)
        analysis_cache.set(fp_key, fingerprint, ttl)

    return output


_MAX_TF_WORKERS = 4


def analyze_multi_tf(
    ticker: str,
    source: str = "nobitex",
    tf_list: list[str] = None,
    market_type: str = "spot",
    risk_profile: str = "aggressive",
    ticker_name: str = "",
) -> dict:
    """تحلیل نماد در چند تایم‌فریم — به‌صورت موازی."""
    if tf_list is None:
        tf_list = list(TF_NAMES)

    if not ticker or not tf_list:
        return {}

    if len(tf_list) == 1:
        tf = tf_list[0]
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
            return {tf: r} if r else {}
        except Exception:
            logger.warning(f"[Analyzer] {tf} شکست خورد", exc_info=True)
            return {}

    def _one(tf: str):
        try:
            return analyze(
                ticker=ticker,
                source=source,
                tf_name=tf,
                market_type=market_type,
                risk_profile=risk_profile,
                ticker_name=ticker_name,
                include_extras=False,
            )
        except Exception:
            logger.warning(f"[Analyzer] {tf} شکست خورد", exc_info=True)
            return None

    raw: dict[str, Optional[dict]] = {}
    try:
        with ThreadPoolExecutor(
            max_workers=min(_MAX_TF_WORKERS, len(tf_list))
        ) as executor:
            future_to_tf = {executor.submit(_one, tf): tf for tf in tf_list}
            for future in as_completed(future_to_tf):
                tf = future_to_tf[future]
                try:
                    raw[tf] = future.result()
                except Exception:
                    logger.warning(f"[Analyzer] future {tf} شکست خورد", exc_info=True)
                    raw[tf] = None
    except Exception:
        logger.exception("[Analyzer] خطا در اجرای موازی TFها")

    results: dict[str, dict] = {}
    for tf in tf_list:
        r = raw.get(tf)
        if r:
            if r:
                # ─── اطمینان از وجود close_series ───
                if "close_series" not in r or not r["close_series"]:
                    r["close_series"] = []
                results[tf] = r

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
    """
    شاخص ترس و طمع.

    ⚠️ TSETMC فقط روزانه دارد — پس برای نمادهای بورس،
       tf_name خودکار "روزانه" می‌شود.
    """
    # ─── تشخیص نماد بورس ───
    is_iranian_stock = bool(ticker) and not ticker[0].isascii()
    tf_name = "روزانه" if (source == "tsetmc" or is_iranian_stock) else "۱ ساعت"

    df = fetch_ohlcv(ticker, tf_name, source)
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
    """
    قیمت لحظه‌ای — سبک و سریع.

    ⚠️ برای TSETMC از endpoint زنده استفاده می‌کند
    (نه کندل دیروز).
    """
    # ─── TSETMC: قیمت زنده ───
    is_iranian_stock = bool(ticker) and not ticker[0].isascii()
    if source == "tsetmc" or is_iranian_stock:
        try:
            from core.tsetmc_fetcher import fetch_tsetmc_live_quote

            live = fetch_tsetmc_live_quote(ticker)
            if live and live.get("price"):
                return live
        except Exception as e:
            logger.debug(f"[Analyzer] live quote {ticker}: {e!r}")

    # ─── بقیه صرافی‌ها: مسیر معمولی ───
    return fetch_quote(ticker, source)


def sparkline(
    ticker: str,
    source: str = "nobitex",
    tf_name: str = "۵ دقیقه",
    limit: int = 30,
) -> Optional[dict]:
    """
    سری قیمت برای نمودار کارت سیگنال — سبک و سریع.

    ⚠️ چرا جدا از analyze:
        ``analyze`` برای sparkline اورکیل است: ۲۰+ اندیکاتور،
        ۵ گروه، checklist، AI export. اینجا فقط OHLCV را
        می‌گیریم و close را برمی‌گردانیم (~۲۰x سریع‌تر).

    Returns:
        dict با close_series و price، یا None
    """
    if not ticker:
        return None

    # ─── اعتبارسنجی منبع ───
    from core.contracts import is_active_source, is_planned_source

    if not is_active_source(source) and not is_planned_source(source):
        return None

    # ─── TSETMC: فقط روزانه ───
    is_iranian_stock = not ticker[0].isascii()
    if is_iranian_stock:
        if tf_name != "روزانه":
            return None
        source = "tsetmc"

    # ─── OHLCV سبک (کش‌شده) ───
    df = fetch_ohlcv(ticker, tf_name, source, use_cache=True)
    if df is None or df.empty:
        return None

    try:
        # ─── ۳۰ کندل آخر close ───
        close_series = [float(x) for x in df["close"].tail(limit).tolist()]
        if not close_series:
            return None

        # ─── قیمت زنده برای TSETMC ───
        from core.data_fetcher import get_data_source

        data_source = get_data_source(df, source)
        price = close_series[-1]

        if data_source == "tsetmc" or is_iranian_stock:
            try:
                from core.tsetmc_fetcher import fetch_tsetmc_live_quote

                live = fetch_tsetmc_live_quote(ticker)
                if live and live.get("price"):
                    price = float(live["price"])
            except Exception:
                pass

        return {
            "ok": True,
            "ticker": ticker,
            "source": source,
            "timeframe": tf_name,
            "close_series": close_series,
            "price": price,
        }
    except Exception as e:
        logger.warning(f"[Analyzer] sparkline {ticker}: {e!r}")
        return None
