# Autopilot Persistent State

This file is the autopilot's memory across iterations. Both lanes (main +
test) read it before picking a gap and write to it after each iteration.

**Do not edit manually unless you know what you're doing** — the autopilot
treats this as its working memory.

---

## In progress

<!-- Each iteration appends one line here when it starts, removes it when done.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <one-line gap description> -->
- 2026-05-21T17:16:00Z [TEST] TEST: volume-profile acceptance/rejection invalidation requires close beyond zone with body > ATR4H

---

## Done

<!-- Iterations that successfully closed a gap. Format:
     - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <sha-short> <one-line summary> -->
- 2026-05-21T17:03:53Z [MAIN] 9f8b64f Add weekly-cycle scoring multiplier test coverage (Sun/Mon/Tue boost vs Fri/Sat penalty)

---

## Considered but rejected

<!-- Candidates the autopilot looked at and decided NOT to pursue.
     Format: - YYYY-MM-DDTHH:MM:SSZ [MAIN|TEST] <candidate> -- <reason> -->
