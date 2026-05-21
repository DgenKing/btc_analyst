# BTC Analyst

BTC swing trading analysis system for BTC-USDC perpetuals on Hyperliquid.
Analysis only — does not execute trades.

**Gospel:** `BTC Swing Trading Framework.md` — all analysis logic must comply with this document.

---

## What it does

- Detects support/resistance zones from 9 sources: horizontal pivots, volume profile (HVN/LVN/POC/VAL/VAH), trendlines, MA clusters (20/50/100/200), liquidity sweeps, CME gap proxy
- Scores zones 0–100 using weighted confluence (S/R 25 + VP 20 + structure 15 + MA 10 + trendline 8 + liquidity 7 + momentum 9 + derivatives 9 + CME 6)
- Tiers: Strong ≥70 / Medium ≥50 / Weak ≥30 / Noise <30
- Runs multi-timeframe bias (weekly / daily / 4H / 1H) with structural HH-HL logic
- Generates A/B/C setup candidates on 4H close with full MTF alignment check and R:R filter
- Sends hourly Telegram updates and a daily report at 12:00 UTC
- Tracks crowd positioning (Bybit / OKX L/S ratio, Fear & Greed, CoinGecko)
- Direction probability model (4H / 1D / 1W) with regime-aware scoring

---

## Current status (2026-05-20)

- Tests: **16 passed, 1 skipped** (backtest module pending integration)
- Active zone sources: horizontal, vp_hvn, vp_lvn, vp_poc, vp_val, vp_vah, trendline, liquidity, ma_cluster, cme_gap_proxy
- Scheduler: running via APScheduler (4H close, daily report, hourly AI review cron)
- Telegram: tool-call echo filtering active, 60-min dedupe window on zone alerts
- Bias engine: per-timeframe structural thresholds (W ≥3%, D ≥2%, 4H ≥1%) — stable, no hour-to-hour flips

---

## Key CLI commands

```bash
# Check system health
python -m btc_analyst.cli sanity-check

# Recompute zones (full augmentation — 9 sources, all factors)
python -m btc_analyst.cli zones --tier medium

# Generate today's report
python -m btc_analyst.cli report --force

# Run market monitor once
python -m btc_analyst.cli monitor-once

# Probability snapshot
python -m btc_analyst.cli probability-once --timeframe 4h

# Full state snapshot (JSON)
python -m btc_analyst.cli state-snapshot --json

# Start live scheduler loop
python -m btc_analyst.cli run

# Run tests
.venv/bin/pytest -q
```

---

## Scheduler topology (run_live.py)

| Job | Schedule |
|---|---|
| Heartbeat | Every 5 min |
| Market monitor cycle | Every 15 min |
| Crowd positioning refresh | Every 5 min |
| Liquidation heatmap refresh | Every 15 min |
| 4H close (zones + setups + probability) | 00:01 / 04:01 / 08:01 / 12:01 / 16:01 / 20:01 UTC |
| Daily close (zones + probability) | 00:01 UTC |
| Daily report | 12:00 UTC |
| Weekly review | Monday 14:00 UTC |
| CME close warning | Thursday 20:00 UTC |
| CME open check | Sunday 22:00 UTC |
| Probability retrospective | Daily 00:30 UTC |
| Probability weekly recompute | Sunday 00:00 UTC |
| DB maintenance + decay | Sunday 03:00 UTC |

---

## Configuration

`config/default.yaml` — all tunables. Key sections:
- `scoring.weights` — factor weights (must sum to ≤109)
- `scoring.multipliers` — trend/range/weekend/weekday multipliers
- `scoring.tier_thresholds` — strong/medium/weak cutoffs
- `setups.tiering` — A/B/C factor requirements and risk multipliers
- `alerts.dedupe_window_minutes` — default 60
- `telegram.enabled` — set via env vars `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
- `monitoring.interval_minutes` — default 15

Secrets: `config/secrets.env` (gitignored)

---

## Data sources

| Source | Purpose |
|---|---|
| Binance perp + spot | Primary OHLCV (all timeframes) |
| Hyperliquid | Derivatives context, liquidation heatmap |
| Bybit | Funding, OI, L/S ratio |
| OKX | L/S ratio |
| Alternative.me | Fear & Greed index |
| CoinGecko | BTC dominance |

See `verified_free_data_sources.md` for source-level operational notes.

---

## Trade framework rules (summary)

- One high-quality trade per week. Maximum two.
- Only trade when Strong or Medium zone confluence aligns with HTF bias and 4H confirmation.
- Long requires: support holding + HTF bullish + HVN/POC support + structure reclaim.
- Short requires: resistance rejection + breakdown + weak momentum + HTF bearish or neutral.
- Never force setups. Stand aside until conditions are right.
- Weekend (Fri–Sat): reduced scoring multiplier. Sunday 22:00 UTC onward: preferred entry window.

Full rules: `BTC Swing Trading Framework.md`
