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

<!-- Candidates the autopilot looked at and decided NOT to pursue.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <candidate> -- <reason> -->
