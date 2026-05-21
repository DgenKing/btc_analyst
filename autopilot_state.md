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

- 2026-05-21T19:59:28Z [MAIN] framework gap candidate: horizontal-vs-diagonal trendline weighting test -- already implemented in tests/unit/test_scoring.py::test_horizontal_levels_outweigh_trendline_when_strength_is_equal

<!-- Candidates the autopilot looked at and decided NOT to pursue.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <candidate> -- <reason> -->
