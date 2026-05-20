from __future__ import annotations

import math
import time
from collections import defaultdict

from btc_analyst.data.hyperliquid_client import HyperliquidClient


def _liq_price(entry: float, lev: float, side: str, mmr: float = 0.005) -> float:
    lev = max(float(lev or 1.0), 1.0)
    if side == 'long':
        return float(entry) * (1 - 1 / lev + mmr)
    return float(entry) * (1 + 1 / lev - mmr)


def refresh_hyperliquid_heatmap(conn, bucket_size: int = 250, top_n_addresses: int = 200) -> dict:
    hc = HyperliquidClient()
    now = int(time.time())

    addresses = []

    # Primary discovery: recent BTC trades (works without auth and includes user addresses)
    try:
        rt = hc.recent_trades('BTC') or []
        for row in rt:
            users = row.get('users') or []
            if isinstance(users, list):
                for a in users:
                    if not a:
                        continue
                    addresses.append(a)
                    conn.execute(
                        "INSERT OR REPLACE INTO hyperliquid_addresses(address,source,last_seen_ts) VALUES (?,?,?)",
                        (a, 'recentTrades', now),
                    )
    except Exception:
        pass

    # Secondary discovery: leaderboard (if endpoint format is accepted)
    if len(addresses) < 10:
        try:
            lb = hc.leaderboard() or []
            for row in lb:
                a = row.get('ethAddress') or row.get('address')
                if a:
                    addresses.append(a)
                    conn.execute(
                        "INSERT OR REPLACE INTO hyperliquid_addresses(address,source,last_seen_ts) VALUES (?,?,?)",
                        (a, 'leaderboard', now),
                    )
        except Exception:
            pass

    # de-dup + cap
    addresses = list(dict.fromkeys(addresses))[: int(top_n_addresses)]

    if not addresses:
        rows = conn.execute("SELECT address FROM hyperliquid_addresses ORDER BY last_seen_ts DESC LIMIT ?", (int(top_n_addresses),)).fetchall()
        addresses = [r[0] for r in rows]

    if not addresses:
        conn.commit()
        return {'ok': False, 'reason': 'no_hyperliquid_addresses', 'addresses': 0, 'positions': 0, 'buckets': 0, 'snapshot_time': now}

    buckets = defaultdict(lambda: {'long': 0.0, 'short': 0.0})
    positions = 0
    for a in addresses:
        try:
            st = hc.clearinghouse_state(a) or {}
        except Exception:
            continue
        for p in st.get('assetPositions', []) or []:
            pos = p.get('position', p)
            if str(pos.get('coin', '')).upper() not in ('BTC', 'BTC-PERP'):
                continue
            szi = float(pos.get('szi', 0) or 0)
            if szi == 0:
                continue
            entry = float(pos.get('entryPx', 0) or 0)
            lev = float(((pos.get('leverage') or {}).get('value', 0)) or 0)
            side = 'long' if szi > 0 else 'short'
            mark = float(pos.get('markPx', entry) or entry)
            notional = abs(szi) * mark
            lp = _liq_price(entry, lev if lev > 0 else 5.0, side)
            b = math.floor(lp / bucket_size) * bucket_size
            if side == 'long':
                buckets[b]['long'] += notional
            else:
                buckets[b]['short'] += notional
            positions += 1

    conn.execute("DELETE FROM liquidation_heatmap_snapshots WHERE snapshot_time < ?", (now - 7 * 24 * 3600,))
    rows = 0
    for low, agg in buckets.items():
        high = low + bucket_size
        ll = float(agg['long'])
        sl = float(agg['short'])
        conn.execute(
            """
            INSERT INTO liquidation_heatmap_snapshots(
              snapshot_time, price_bucket_low, price_bucket_high, long_liq_usd, short_liq_usd, net_liq_usd, source
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (now, low, high, ll, sl, sl - ll, 'hyperliquid'),
        )
        rows += 1
    conn.commit()
    return {'ok': True, 'addresses': len(addresses), 'positions': positions, 'buckets': rows, 'snapshot_time': now}


def get_latest_heatmap(conn, near_price: float | None = None, limit: int = 10):
    row = conn.execute("SELECT MAX(snapshot_time) FROM liquidation_heatmap_snapshots").fetchone()
    if not row or not row[0]:
        return []
    ts = int(row[0])
    if near_price is None:
        q = "SELECT price_bucket_low,price_bucket_high,long_liq_usd,short_liq_usd,net_liq_usd FROM liquidation_heatmap_snapshots WHERE snapshot_time=? ORDER BY (long_liq_usd+short_liq_usd) DESC LIMIT ?"
        rs = conn.execute(q, (ts, limit)).fetchall()
    else:
        q = "SELECT price_bucket_low,price_bucket_high,long_liq_usd,short_liq_usd,net_liq_usd FROM liquidation_heatmap_snapshots WHERE snapshot_time=? ORDER BY ABS(((price_bucket_low+price_bucket_high)/2)-?) ASC LIMIT ?"
        rs = conn.execute(q, (ts, float(near_price), limit)).fetchall()
    return [
        {'price_low': r[0], 'price_high': r[1], 'long_liq_usd': r[2], 'short_liq_usd': r[3], 'net_liq_usd': r[4]}
        for r in rs
    ]
