# Autopilot Persistent State

This file is the autopilot's memory across iterations. Both lanes (main +
test) read it before picking a gap and write to it after each iteration.

**Do not edit manually unless you know what you're doing** — the autopilot
treats this as its working memory.

---

## In progress

<!-- Each iteration appends one line here when it starts, removes it when done.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <one-line gap description> -->
---

## Done

- 2026-05-22T05:28:04Z [TEST] b395454 TEST: MTF confluence should reject aligned daily/12h/8h long when 4h momentum conflicts

- 2026-05-22T05:24:00Z [MAIN] a4c6e57 framework gap: probability late-week de-risk should include Thursday directional dampening parity test

- 2026-05-22T05:01:25Z [TEST] 8913f23 TEST: weekly cycle should de-risk Friday directional probability vs midweek

- 2026-05-22T04:27:27Z [MAIN] 1627a7a framework gap: setup trade-frequency cap should honor config key max_trades_per_week

- 2026-05-22T04:14:21Z [TEST] a9a1c35 TEST: bullish acceptance RSI reclaim should require RSI >= 45 at support

- 2026-05-22T04:09:58Z [MAIN] 5e813fd framework gap: probability directional weekday boost should include Monday alongside Tuesday preferred window

- 2026-05-22T03:49:28Z [MAIN] 6bfdf02 framework gap: probability weekly pattern should not boost Sunday before 22:00 UTC futures open

- 2026-05-22T03:47:44Z [TEST] 038df5e TEST: current-range detection should reject distant boundaries (>10%) to avoid forced mid-range framing

- 2026-05-22T03:22:39Z [TEST] 2fb5569 TEST: MTF confluence should reject long setups when both 12h and 8h conflict with bullish daily bias

- 2026-05-22T03:12:48Z [MAIN] c4d37a0 add ATR boundary-pass behavior test for equality at min/max thresholds

- 2026-05-22T02:58:52Z [TEST] 4fe6a47 TEST: diagonal trendline should produce resistance zone on descending swing-high structure

- 2026-05-22T02:55:15Z [MAIN] f742572 enforce minimum RR hard filter reason parity via behavior test

- 2026-05-22T02:34:39Z [TEST] 3114808 TEST: setup tiering should keep B setups pending until A-lockout window expires

- 2026-05-22T02:09:17Z [TEST] 75d512d TEST: ATR risk bounds must reject setups when daily volatility is outside configured range

- 2026-05-22T01:45:40Z [TEST] a06239f TEST: POC definition should pick highest-volume price bin as acceptance level

- 2026-05-22T01:40:22Z [MAIN] f9a8fe0 probability weekly pattern should align with framework Sunday/Monday/Tuesday preferred window

- 2026-05-22T01:17:18Z [TEST] b1bf45a TEST: range-trading context should score range lows as support bias and highs as resistance bias

- 2026-05-22T00:54:00Z [TEST] 0d241af TEST: value area bounds (VAL/VAH) should map to directional support/resistance by current price

- 2026-05-22T00:29:06Z [TEST] 6957c66 TEST: macro event risk should block new setups via hard filters

- 2026-05-22T00:06:33Z [TEST] e017e9c TEST: invalid direction should be rejected by hard filters (only long/short allowed)

- 2026-05-21T23:44:01Z [TEST] 78b6831 TEST: leverage risk control should block setups when funding is crowded in setup direction

- 2026-05-21T23:40:59Z [MAIN] a310268 sanity-check should surface health_status and stale_components in CLI output contract

- 2026-05-21T22:53:16Z [TEST] ddd59e4 TEST: trade-frequency cap should count existing weekly qualified setups before persisting new ones

- 2026-05-21T22:31:03Z [MAIN] 2995451 enforce framework trade-frequency cap: persist at most two qualified setups per week
- 2026-05-21T22:26:45Z [TEST] 448ca60 TEST: trade-frequency rule should cap framework-qualified setups to max two per week (xfail)
- 2026-05-21T22:11:39Z [MAIN] 04da90c add framework trade-frequency defaults (ideal=1/week, max=2/week) to config contract
- 2026-05-21T22:01:54Z [TEST] fefc941 TEST: add bearish rejection momentum behavior test (resistance RSI rejection requires weak momentum threshold)
- 2026-05-21T21:38:35Z [TEST] 326a28e TEST: add session-quality behavior test (London/NY overlap scores above single-session windows)
- 2026-05-21T21:34:11Z [MAIN] 56fb081 setup engine queries should use configured symbol (BTCUSDC), not hardcoded BTCUSDT
- 2026-05-21T21:13:41Z [MAIN] 6c0a78e report source label should reflect configured primary venue in daily report
- 2026-05-21T21:07:50Z [TEST] 3210606 TEST: add reaction behavior test (framework acceptance/rejection requires rejection at resistance zone)
- 2026-05-21T20:53:47Z [MAIN] 7654102 default symbol should align with framework BTC-USDC perpetual pair

- 2026-05-21T20:44:51Z [TEST] f1ed424 TEST: add direction behavior test (framework supports both long and short setups)
- 2026-05-21T20:35:59Z [MAIN] 47b4223 add explicit config default test for Hyperliquid derivatives venue alignment
- 2026-05-21T20:21:32Z [TEST] 3533d5e TEST: add bearish MTF alignment behavior test (daily neutral short requires 12h/8h bearish agreement)
- 2026-05-21T20:17:03Z [MAIN] 0ac1ec4 add explicit test that default config includes 3d timeframe from Daily/3-Day section
- 2026-05-21T19:55:41Z [TEST] 5845e6e TEST: add MTF alignment behavior test (daily neutral requires 12h/8h directional agreement)
- 2026-05-21T19:40:08Z [MAIN] 0be4197 Enforce Sunday 22:00 UTC timing gate in setup engine weekly timing quality (pre-open Sunday should be midweek)
- 2026-05-21T19:32:11Z [TEST] ae6dfa9 TEST: add range-structure behavior test (range edge scores above range midpoint)
- 2026-05-21T19:21:28Z [MAIN] 1f1da02 Add POC directional behavior test (support below price, resistance above price)
- 2026-05-21T19:09:30Z [TEST] c2ca4c4 TEST: add volume profile HVN behavior test (support below price / resistance above price)
- 2026-05-21T19:01:15Z [MAIN] be99e6e Replace skipped backtest placeholder with executable behavior tests for walk-forward harness
- 2026-05-21T18:45:43Z [TEST] 9e2f661 TEST: add trigger behavior test for reclaim/reject confirmation gating
- 2026-05-21T18:41:52Z [MAIN] 86b057c Enforce Sunday preferred-window boost only after 22:00 UTC per framework timing
- 2026-05-21T18:23:46Z [MAIN] 55adf5a Add scorer parity test: Saturday should be de-risked same as Friday
- 2026-05-21T18:18:51Z [TEST] e85ff38 TEST: add weekly timing quality behavior test (Sun-Mon-Tue optimal; Fri-Sat de-risked)
- 2026-05-21T18:01:32Z [MAIN] c28ec71 Add Thursday de-risk multiplier parity test + scorer alignment
- 2026-05-21T17:43:03Z [MAIN] cb25a40 Add Sun/Mon/Tue preferred-window parity test
- 2026-05-21T17:23:29Z [MAIN] 56aeb04 Add unit test for MA cluster coverage including 100 MA per framework
<!-- Iterations that successfully closed a gap. Format:
     - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <sha-short> <one-line summary> -->
- 2026-05-21T17:03:53Z [MAIN] 9f8b64f Add weekly-cycle scoring multiplier test coverage (Sun/Mon/Tue boost vs Fri/Sat penalty)
- 2026-05-21T17:17:26Z [TEST] 3db4d5b TEST: add acceptance/rejection invalidation behavior test (close beyond zone + body > ATR4H)
- 2026-05-21T17:32:47Z [TEST] a82257d TEST: add hard-filter behavior test for counter-trend high-conviction threshold (requires score >= 85)
- 2026-05-21T17:56:16Z [TEST] 716eaff TEST: add tier boundary behavior test (strong >=70 from framework scoring thresholds)

---

## Considered but rejected

- 2026-05-21T22:49:51Z [MAIN] framework gap candidate: add 3-day timeframe support for Daily/3-Day analysis -- already implemented in src/btc_analyst/data/ohlcv_store.py (INTERVAL_MAP/BINANCE_INTERVAL_MAP include 3d) and covered by config default parity test
- 2026-05-21T21:53:15Z [MAIN] framework gap candidate: explicit Friday de-risk timing behavior parity test -- already implemented in tests/unit/test_setup_engine_timing.py::test_weekly_timing_quality_windows_follow_framework_cycle
- 2026-05-21T19:59:28Z [MAIN] framework gap candidate: horizontal-vs-diagonal trendline weighting test -- already implemented in tests/unit/test_scoring.py::test_horizontal_levels_outweigh_trendline_when_strength_is_equal

<!-- Candidates the autopilot looked at and decided NOT to pursue.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <candidate> -- <reason> -->
