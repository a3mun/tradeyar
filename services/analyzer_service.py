"""
services/analyzer_service.py
لایه تحلیل — با کش + fingerprint + analyzer_version
============================================================
نسخه ۴.۳:
  • اضافه کردن trend_predicted_at_entry به output
  • حفظ ساختار قبلی
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from core.analyzer import (
    ANALYZER_VERSION,
    _build_ai_export,
    _build_fundamental_context,
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


_ORDERBOOK_ENABLED = True


def _orderbook_enabled() -> bool:
    return _ORDERBOOK_ENABLED


def set_orderbook_enabled(enabled: bool) -> None:
    global _ORDERBOOK_ENABLED
    _ORDERBOOK_ENABLED = bool(enabled)


def _is_iranian(ticker: str) -> bool:
    if not ticker:
        return False
    upper = ticker.upper()
    if upper.endswith("-IRT") or upper.endswith("-RLS"):
        return True
    return not ticker[0].isascii()


def _resolve_live_price(ticker: str, source: str, fallback: float) -> float:
    is_iranian_stock = bool(ticker) and not ticker[0].isascii()
    if not (source == "tsetmc" or is_iranian_stock):
        return float(fallback or 0.0)
    try:
        from core.tsetmc_fetcher import fetch_tsetmc_live_quote

        live = fetch_tsetmc_live_quote(ticker)
        if live and live.get("price"):
            return float(live["price"])
    except Exception:
        pass
    return float(fallback or 0.0)


def _make_cache_key(
    ticker: str, source: str, tf_name: str, market_type: str, risk_profile: str
) -> str:
    return f"analysis:v{ANALYZER_VERSION}:{ticker}:{source}:{tf_name}:{market_type}:{risk_profile}"


def _make_versioned_fingerprint(df, tf_name: str) -> str:
    raw_fp = make_fingerprint(df, tf_name)
    return f"v{ANALYZER_VERSION}:{raw_fp}"


def _refresh_live_fields(cached: dict, df) -> dict:
    try:
        if df is None or df.empty:
            return cached

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

    try:
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

    try:
        out["ai_export"] = _build_ai_export(
            ticker=cached.get("ticker", ""),
            name=cached.get("name", ""),
            tf_name=cached.get("timeframe", "۵ دقیقه"),
            analysis=out,
            tfs_data=None,
            df=df,
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
    if skip_record:
        return
    if output.get("is_fallback"):
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
            trend_predicted_at_entry=output.get("trend_predicted_at_entry", "flat"),
        )
    except Exception as e:
        logger.debug(f"[Analyzer] record_signal: {e}")


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
    if not ticker:
        return None

    from core.contracts import is_active_source, is_planned_source

    if not is_active_source(source) and not is_planned_source(source):
        return None

    is_iranian_stock = not ticker[0].isascii()
    if is_iranian_stock:
        if tf_name != "روزانه":
            return None
        source = "tsetmc"

    df = fetch_ohlcv(ticker, tf_name, source, use_cache=use_cache)
    if df is None or df.empty:
        return None

    data_source = get_data_source(df, source)
    fingerprint = _make_versioned_fingerprint(df, tf_name) if use_cache else ""
    cache_key = _make_cache_key(ticker, source, tf_name, market_type, risk_profile)
    fp_key = f"{cache_key}:fp"

    if use_cache:
        cached_fp = analysis_cache.get(fp_key)
        if cached_fp == fingerprint:
            cached_result = analysis_cache.get(cache_key)
            if cached_result is not None:
                out = _refresh_live_fields(cached_result, df)
                out["source_used"] = data_source
                out["is_fallback"] = data_source != source
                out.pop("orderbook", None)

                if not skip_record and tf_name != "۱ دقیقه":
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

    orderbook = None
    if include_extras and _orderbook_enabled():
        try:
            from core.orderbook import get_orderbook

            orderbook = get_orderbook(ticker, data_source, depth=20)
        except Exception:
            pass

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

    if include_extras:
        try:
            from core.contracts import get_fee_rate as _gfr

            effective_fee_pct = sl_tp.get("fee_pct")
            if effective_fee_pct is None:
                effective_fee_pct = (
                    _gfr(
                        data_source or "nobitex", market_type=market_type, ticker=ticker
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
        except Exception:
            pass

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
        "is_golden": result.get("is_golden", False),
        "consensus": result.get("consensus", "neutral"),
        "regime": result.get("regime", "range"),
        "session_label": result.get("session_label", ""),  # 🔴 این خط را اضافه کن
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
        "analyzer_version": ANALYZER_VERSION,
        "pre_breakout": result.get("pre_breakout", {}),
        "pre_breakout_score": result.get("pre_breakout_score", 0),
        "is_pre_breakout": result.get("is_pre_breakout", False),
        # 🔴 فاز ۱۳.۰ — رفع باگ trend_accuracy
        "trend_predicted_at_entry": result.get("trend_predicted_at_entry", "flat"),
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
                df=df,
            )
        except Exception as e:
            logger.warning(f"[Analyzer] ai_export: {e}")

    output["market_type"] = market_type
    output["risk_profile"] = risk_profile

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
                    raw[tf] = None
    except Exception:
        pass

    results: dict[str, dict] = {}
    for tf in tf_list:
        r = raw.get(tf)
        if r:
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
    except Exception:
        return "خطا در تولید تحلیل."


def checklist(tfs, main_tf="۵ دقیقه"):
    try:
        items, pct, final, color = build_checklist_weighted(tfs, main_tf)
        return {"items": items, "percentage": pct, "final": final, "final_color": color}
    except Exception:
        return {"items": [], "percentage": 0, "final": "", "final_color": "yellow"}


def fear_greed(ticker, source="nobitex"):
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
    except Exception:
        return None


def quote(ticker, source="nobitex"):
    is_iranian_stock = bool(ticker) and not ticker[0].isascii()
    if source == "tsetmc" or is_iranian_stock:
        try:
            from core.tsetmc_fetcher import fetch_tsetmc_live_quote

            live = fetch_tsetmc_live_quote(ticker)
            if live and live.get("price"):
                return live
        except Exception:
            pass
    return fetch_quote(ticker, source)


def sparkline(
    ticker: str, source: str = "nobitex", tf_name: str = "۵ دقیقه", limit: int = 30
) -> Optional[dict]:
    if not ticker:
        return None
    from core.contracts import is_active_source, is_planned_source

    if not is_active_source(source) and not is_planned_source(source):
        return None
    is_iranian_stock = not ticker[0].isascii()
    if is_iranian_stock:
        if tf_name != "روزانه":
            return None
        source = "tsetmc"
    df = fetch_ohlcv(ticker, tf_name, source, use_cache=True)
    if df is None or df.empty:
        return None
    try:
        close_series = [float(x) for x in df["close"].tail(limit).tolist()]
        if not close_series:
            return None
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
    except Exception:
        return None
