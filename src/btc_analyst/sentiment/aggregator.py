from __future__ import annotations

import json
import logging
import time

from .bybit_longshort import fetch_bybit_longshort
from .okx_longshort import fetch_okx_longshort
from .fear_greed import fetch_fear_greed
from .reddit_sentiment import fetch_reddit_sentiment
from .coingecko_context import fetch_coingecko_context

log = logging.getLogger(__name__)


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log.warning("sentiment source call failed: %s", e)
        return None


def _latest_bybit_funding_and_oi(conn, venue='bybit_perp'):
    r1 = conn.execute(
        "SELECT funding_rate FROM funding WHERE symbol='BTCUSDT' AND venue=? ORDER BY funding_time DESC LIMIT 1",
        (venue,),
    ).fetchone()
    funding = float(r1[0]) if r1 else None

    rows = conn.execute(
        "SELECT oi FROM open_interest WHERE symbol='BTCUSDT' AND venue=? ORDER BY ts DESC LIMIT 24",
        (venue,),
    ).fetchall()
    oi_delta = None
    if len(rows) >= 2:
        latest = float(rows[0][0])
        old = float(rows[-1][0])
        if old != 0:
            oi_delta = ((latest - old) / old) * 100.0
    return funding, oi_delta


def aggregate_label_from_signals(row: dict, cfg: dict):
    s_cfg = (cfg or {}).get("sentiment") or {}
    th = s_cfg.get("extreme_thresholds") or {}
    rule = s_cfg.get("aggregate_rule") or {}

    funding_abs = float(th.get("funding_8h_abs", 0.0005))
    ls_hi = float(th.get("long_short_ratio_high", 2.0))
    ls_lo = float(th.get("long_short_ratio_low", 0.5))
    fg_lo = int(th.get("fear_greed_extreme_low", 20))
    fg_hi = int(th.get("fear_greed_extreme_high", 80))

    ex_req = int(rule.get("extreme_signals_required", 3))
    mild_req = int(rule.get("mild_signals_required", 2))

    ex_long = ex_short = mild_long = mild_short = signals_total = 0

    def _consume_ls(v):
        nonlocal ex_long, ex_short, mild_long, mild_short, signals_total
        if v is None:
            return
        signals_total += 1
        vv = float(v)
        if vv >= ls_hi:
            ex_long += 1
        elif vv <= ls_lo:
            ex_short += 1
        elif vv > 1.0:
            mild_long += 1
        elif vv < 1.0:
            mild_short += 1

    _consume_ls(row.get("bybit_long_short_ratio"))
    _consume_ls(row.get("okx_long_short_ratio"))

    f = row.get("bybit_funding_8h")
    if f is not None:
        signals_total += 1
        ff = float(f)
        if ff >= funding_abs:
            ex_long += 1
        elif ff <= -funding_abs:
            ex_short += 1
        elif ff > 0:
            mild_long += 1
        elif ff < 0:
            mild_short += 1

    fg = row.get("fear_greed_value")
    if fg is not None:
        signals_total += 1
        fv = int(fg)
        if fv >= fg_hi:
            ex_long += 1
        elif fv <= fg_lo:
            ex_short += 1
        elif fv > 50:
            mild_long += 1
        elif fv < 50:
            mild_short += 1

    if ex_long >= ex_req and ex_long > ex_short:
        return "extreme_long_crowd", 1, {"extreme_long": ex_long, "extreme_short": ex_short, "signals_total": signals_total}
    if ex_short >= ex_req and ex_short > ex_long:
        return "extreme_short_crowd", 1, {"extreme_long": ex_long, "extreme_short": ex_short, "signals_total": signals_total}
    if (ex_long + mild_long) >= mild_req and (ex_long + mild_long) > (ex_short + mild_short):
        return "mild_long", 0, {"extreme_long": ex_long, "extreme_short": ex_short, "signals_total": signals_total}
    if (ex_short + mild_short) >= mild_req and (ex_short + mild_short) > (ex_long + mild_long):
        return "mild_short", 0, {"extreme_long": ex_long, "extreme_short": ex_short, "signals_total": signals_total}
    return "neutral", 0, {"extreme_long": ex_long, "extreme_short": ex_short, "signals_total": signals_total}


def refresh_crowd_positioning(conn, cfg: dict):
    s_cfg = (cfg or {}).get("sentiment") or {}
    if not s_cfg.get("enabled", False):
        return {"ok": False, "reason": "sentiment_disabled"}

    sources_cfg = s_cfg.get("sources") or {}
    now = int(time.time())

    data_cfg = (cfg or {}).get('data') or {}
    deriv_venue = data_cfg.get('derivatives_venue', data_cfg.get('primary_venue', 'bybit_perp'))
    bybit_funding_8h, bybit_oi_24h_delta_pct = _latest_bybit_funding_and_oi(conn, venue=deriv_venue)

    bybit_ls = _safe_call(fetch_bybit_longshort) if (sources_cfg.get("bybit_longshort") or {}).get("enabled", True) else None
    okx_ls = _safe_call(fetch_okx_longshort) if (sources_cfg.get("okx_longshort") or {}).get("enabled", True) else None

    # CoinGlass removed: keep fields nullable for backward DB compatibility.
    cg_bundle = {}

    fng = _safe_call(fetch_fear_greed) if (sources_cfg.get("fear_greed") or {}).get("enabled", True) else None

    reddit_cfg = sources_cfg.get("reddit") or {}
    reddit = _safe_call(fetch_reddit_sentiment, user_agent=reddit_cfg.get("user_agent", "btc_analyst/1.0")) if reddit_cfg.get("enabled", False) else None

    cgk = _safe_call(fetch_coingecko_context) if (sources_cfg.get("coingecko") or {}).get("enabled", True) else None

    row = {
        "ts": now,
        "bybit_funding_8h": bybit_funding_8h,
        "bybit_oi_24h_delta_pct": bybit_oi_24h_delta_pct,
        "bybit_long_short_ratio": (bybit_ls or {}).get("long_short_ratio") if bybit_ls else None,
        "okx_long_short_ratio": (okx_ls or {}).get("long_short_ratio") if okx_ls else None,
        "coinglass_funding_aggregate": cg_bundle.get("funding_aggregate"),
        "coinglass_oi_aggregate": cg_bundle.get("oi_aggregate"),
        "coinglass_long_short_aggregate": cg_bundle.get("long_short_aggregate"),
        "coinglass_liquidations_24h_long_usd": cg_bundle.get("liquidations_24h_long_usd"),
        "coinglass_liquidations_24h_short_usd": cg_bundle.get("liquidations_24h_short_usd"),
        "fear_greed_value": (fng or {}).get("value") if fng else None,
        "fear_greed_label": (fng or {}).get("label") if fng else None,
        "reddit_sentiment_score": (reddit or {}).get("score") if reddit else None,
        "btc_dominance_pct": (cgk or {}).get("btc_dominance_pct") if cgk else None,
    }

    label, extreme_flag, _ = aggregate_label_from_signals(row, cfg)
    row["aggregate_label"] = label
    row["extreme_flag"] = extreme_flag

    availability = {
        "bybit_funding_oi": bybit_funding_8h is not None or bybit_oi_24h_delta_pct is not None,
        "bybit_longshort": bybit_ls is not None,
        "okx_longshort": okx_ls is not None,
        "coinglass": False,
        "fear_greed": fng is not None,
        "reddit": reddit is not None,
        "coingecko": cgk is not None,
    }
    row["sources_available_json"] = json.dumps(availability)

    conn.execute(
        """
        INSERT INTO crowd_positioning_snapshots(
            ts, bybit_funding_8h, bybit_oi_24h_delta_pct, bybit_long_short_ratio,
            okx_long_short_ratio, coinglass_funding_aggregate, coinglass_oi_aggregate,
            coinglass_long_short_aggregate, coinglass_liquidations_24h_long_usd,
            coinglass_liquidations_24h_short_usd, fear_greed_value, fear_greed_label,
            reddit_sentiment_score, btc_dominance_pct, aggregate_label, extreme_flag,
            sources_available_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            row["ts"], row["bybit_funding_8h"], row["bybit_oi_24h_delta_pct"], row["bybit_long_short_ratio"],
            row["okx_long_short_ratio"], row["coinglass_funding_aggregate"], row["coinglass_oi_aggregate"],
            row["coinglass_long_short_aggregate"], row["coinglass_liquidations_24h_long_usd"],
            row["coinglass_liquidations_24h_short_usd"], row["fear_greed_value"], row["fear_greed_label"],
            row["reddit_sentiment_score"], row["btc_dominance_pct"], row["aggregate_label"], row["extreme_flag"],
            row["sources_available_json"],
        ),
    )
    conn.commit()
    return {"ok": True, "snapshot": row}


def get_latest_crowd_positioning(conn):
    row = conn.execute("SELECT * FROM crowd_positioning_snapshots ORDER BY ts DESC LIMIT 1").fetchone()
    if not row:
        return None
    cols = [x[1] for x in conn.execute("PRAGMA table_info(crowd_positioning_snapshots)").fetchall()]
    out = dict(zip(cols, row))
    try:
        out["sources_available"] = json.loads(out.get("sources_available_json") or "{}")
    except Exception:
        out["sources_available"] = {}

    # Derived source-health stats for report quality gating.
    avail = out.get("sources_available") or {}
    known = [k for k in avail.keys() if k != "coinglass"]
    up = [k for k in known if bool(avail.get(k))]
    down = [k for k in known if not bool(avail.get(k))]
    out["sources_up_count"] = len(up)
    out["sources_total_count"] = len(known)
    out["coverage_score"] = (len(up) / len(known)) if known else 0.0
    out["missing_sources_list"] = down
    return out
