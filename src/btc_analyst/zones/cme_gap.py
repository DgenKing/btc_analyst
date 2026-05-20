from __future__ import annotations

from datetime import datetime, timezone

from btc_analyst.zones.registry import Zone


def _weekday_from_ms(ms: int) -> int:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).weekday()


def detect_cme_gaps(df_4h, symbol='BTCUSDT', timeframe='4h'):
    """
    Proxy CME gap detection from BTC 4H candles:
    - Friday close (late UTC Friday session)
    - Sunday reopen (late UTC Sunday session)
    Creates support/resistance zones around unfilled weekend jump.
    """
    if df_4h is None or df_4h.empty or len(df_4h) < 20:
        return []

    d = df_4h[['open_time', 'open', 'high', 'low', 'close']].copy().sort_values('open_time')
    out = []

    # scan recent 8 weeks only to avoid stale gaps flooding output
    recent = d.tail(8 * 7 * 6)
    fridays = recent[recent['open_time'].apply(_weekday_from_ms) == 4]
    sundays = recent[recent['open_time'].apply(_weekday_from_ms) == 6]

    if fridays.empty or sundays.empty:
        return []

    # pair each sunday with nearest prior friday
    for _, s in sundays.iterrows():
        prior_f = fridays[fridays['open_time'] < s['open_time']]
        if prior_f.empty:
            continue
        f = prior_f.iloc[-1]
        friday_close = float(f['close'])
        sunday_open = float(s['open'])
        gap_abs = abs(sunday_open - friday_close)
        if friday_close <= 0:
            continue
        gap_pct = gap_abs / friday_close

        # ignore tiny discontinuities
        if gap_pct < 0.002:
            continue

        low = min(friday_close, sunday_open)
        high = max(friday_close, sunday_open)
        direction = 'up' if sunday_open > friday_close else 'down'
        ztype = 'support' if direction == 'up' else 'resistance'
        out.append(
            Zone(
                symbol=symbol,
                price_low=low,
                price_high=high,
                zone_type=ztype,
                source='cme_gap_proxy',
                timeframe=timeframe,
                factors={
                    'cme_gap_strength': min(1.0, max(0.0, gap_pct / 0.01)),
                    'cme_gap_pct': round(gap_pct * 100.0, 3),
                    'gap_direction': direction,
                },
            )
        )

    return out
