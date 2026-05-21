# Autopilot Persistent State

This file is the autopilot's memory across iterations. Both lanes (main +
test) read it before picking a gap and write to it after each iteration.

**Do not edit manually unless you know what you're doing** — the autopilot
treats this as its working memory.

---

## In progress

- 2026-05-21T17:22:55Z [MAIN] Add unit test for MA cluster coverage including 100 MA per framework
<!-- Each iteration appends one line here when it starts, removes it when done.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <one-line gap description> -->

---

## Done

<!-- Iterations that successfully closed a gap. Format:
     - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <sha-short> <one-line summary> -->
- 2026-05-21T17:03:53Z [MAIN] 9f8b64f Add weekly-cycle scoring multiplier test coverage (Sun/Mon/Tue boost vs Fri/Sat penalty)
- 2026-05-21T17:17:26Z [TEST] 3db4d5b TEST: add acceptance/rejection invalidation behavior test (close beyond zone + body > ATR4H)

---

## Considered but rejected

<!-- Candidates the autopilot looked at and decided NOT to pursue.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <candidate> -- <reason> -->
