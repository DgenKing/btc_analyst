# BTC Analyst Autonomous Mode (HermesAgent)

HermesAgent is configured to run autonomously on this project. Three Hermes
cron jobs iterate on the codebase forever, with the BTC Swing Trading
Framework as the sole source of truth.

---

## What's running

| Job name | Cadence | Role |
|---|---|---|
| `btc-analyst-autopilot` | every 15m | Audit framework vs. code, fix one gap, run tests, commit + push to `autopilot` branch |
| `btc-analyst-autopilot-tests` | every 20m | Add one new behavior test encoding a framework rule, commit + push |
| `btc-analyst-autopilot-watchdog` | every 5m | Re-enable paused autopilot jobs, emit heartbeat |

All three are registered in `~/.hermes/cron/jobs.json` and dispatched by the
Hermes gateway scheduler (which must be running — `hermes cron status`
confirms).

## Branching model

- `master` — clean baseline. **Autopilot never touches this branch.**
  Local rollback via `git reset --hard pre-autonomy-2026-05-21`.
- `autopilot` — all autonomous commits land here. Pushed to
  `origin/autopilot` after every successful iteration.
- `pre-autonomy-2026-05-21` — tag pinning the pre-autopilot state on
  GitHub at https://github.com/DgenKing/btc_analyst.

To review autopilot work: `git log master..autopilot --oneline`
To merge cherry-picks back: `git checkout master && git cherry-pick <sha>`

## Persistent state

`autopilot_state.md` (in this directory) is the autopilot's working memory
across iterations. Sections: `## In progress`, `## Done`,
`## Considered but rejected`. Lanes prefix entries with `[MAIN]` or
`[TEST]`. Don't edit by hand unless you know what you're doing.

A shared lock at `~/.hermes/btc_autopilot.lock` prevents the two lanes
from racing the git repo when both fire near the same minute.

## Source of truth

`BTC Swing Trading Framework.md` (in this directory). Every change the
autopilot makes must trace back to a rule in this document. Secondary
references it may read:

- `README.md` — current implementation state
- `AGENTS.md` — operating charter
- `verified_free_data_sources.md`

## Worker prompts

Hermes loads its instructions from these files each iteration. Edit them to
retune autopilot behavior **without re-registering the cron**:

- `/home/btcai/.hermes/scripts/btc_analyst_autopilot_prompt.md` — main loop
- `/home/btcai/.hermes/scripts/btc_analyst_autopilot_tests_prompt.md` — test lane
- `/home/btcai/.hermes/scripts/btc_autopilot_watchdog.sh` — watchdog script

## Log

`/home/btcai/.hermes/logs/btc_autopilot.log` — one line per iteration:
`ISO-TS [WATCHDOG|TESTS|<lane>] <commit-sha-short> <one-line summary>`

---

## One-iteration recipe (main lane)

Each cron tick, Hermes performs exactly this:

1. **Orient.** Read the framework section index. Pick the smallest
   unaddressed gap. Signals of a gap:
   - A framework concept (e.g. "POC reaction", "MTF confluence",
     "Sunday 22:00 UTC entry window") with no corresponding test.
   - A test failure, skip, or warning under `.venv/bin/pytest -q`.
   - A `monitor-once` / `sanity-check` CLI output that surfaces a missing
     field or unhealthy signal.
   - A scoring/weight constant that drifted from the framework's emphasis.

2. **Make ONE focused change.** Edit only what is required to close that
   single gap. Prefer adding a test that encodes a framework rule, then
   making it pass.

3. **Verify.**
   ```bash
   cd /home/btcai/btc_analyst
   .venv/bin/pytest -q
   PYTHONPATH=src .venv/bin/python -m btc_analyst.cli sanity-check
   ```
   Both must pass. If broken, revert via `git restore` and try smaller.

4. **Commit.** If green and something changed:
   ```bash
   git add -A
   git commit -m "autopilot: <one-line summary>"
   ```
   Local only — never push.

5. **Log.** Append a line to `~/.hermes/logs/btc_autopilot.log`.

## One-iteration recipe (test lane)

Same shape, but the lane is restricted to **adding one new test** per tick
that encodes a framework rule. Picks the framework section least covered by
existing tests. Commit message prefix `autopilot(tests):`.

---

## Hard rules (baked into the prompts)

- **Never** push to a remote. Local commits only.
- **Never** delete `.venv/`, `data/`, `reports/`, `logs/`.
- **Never** modify files outside `/home/btcai/btc_analyst/` except the
  autopilot log at `/home/btcai/.hermes/logs/btc_autopilot.log`.
- **Never** invent framework requirements. If a rule isn't in the gospel,
  it isn't a gap.
- **Never** disable, delete, or weaken tests to make them pass. Fix the
  encoding, not the existence.
- One focused change per iteration. No bulk refactors.
- If parity is reached, output `NOOP - parity reached` and stop. The cron
  re-evaluates next tick.

## Output format (each iteration)

```
ITERATION RESULT: <CHANGED:<files> | NOOP:<reason>>
TESTS: <pass/fail counts>
NEXT GAP CANDIDATES: <up to 3 bullets>
```

Test lane variant prefixes with `(TEST LANE)` and lists `NEXT UNCOVERED
SECTIONS`.

---

## Operator commands

```bash
# See all jobs, schedules, last/next run
hermes cron list

# Confirm the scheduler is running
hermes cron status

# Pause / resume a lane
hermes cron pause  btc-analyst-autopilot
hermes cron resume btc-analyst-autopilot

# Trigger an immediate run (fires on next 60s tick)
hermes cron run btc-analyst-autopilot
hermes cron run btc-analyst-autopilot-tests
hermes cron run btc-analyst-autopilot-watchdog

# Remove a lane permanently
hermes cron remove btc-analyst-autopilot

# Watch the autopilot log live
tail -f ~/.hermes/logs/btc_autopilot.log

# See what the autopilot has committed
cd /home/btcai/btc_analyst && git log --oneline -20

# Inspect per-run output (Markdown summary per fire)
ls -lt ~/.hermes/cron/output/<job-id>/ | head
```

## Re-tuning behavior

- **Change the iteration recipe** → edit the worker prompt file (changes
  take effect on the next cron tick; no re-registration needed).
- **Change the cadence** → `hermes cron edit <job-id>` (or remove + create).
- **Throttle spend** → `hermes cron pause btc-analyst-autopilot-tests`
  during heavy work, resume later.
- **Stop everything** → pause all three jobs. Cron entries remain for easy
  resume.

## Stop conditions

Per current config: **never** — runs forever. To set a stop criterion, edit
the prompt files to add a halt condition (e.g. "if `pytest -q` is green AND
every framework section has a passing test, output `NOOP - parity reached`
and stop"). The cron still ticks but emits NOOP until you reactivate work
by editing the prompts.

## Safety net

The watchdog (`btc_autopilot_watchdog.sh`, every 15m):

- Resumes any paused autopilot job (so an accidental pause auto-heals).
- Emits an hourly heartbeat to the log.
- Delivers a notification only when it had to repair something.

To make autopilot pauses **sticky** (watchdog won't re-resume), pause and
also remove the job from the watchdog's loop — edit
`~/.hermes/scripts/btc_autopilot_watchdog.sh` and drop the job name from
the `for job in ...` list.

---

## Architecture choice notes

Originally the user asked for **goal + safety cron**. Without `tmux`/`screen`
in this environment, a true long-lived interactive `/goal` REPL session is
fragile (no easy way to keep stdin open for an unattended Hermes chat). The
implemented equivalent is **two independent iteration lanes plus a
watchdog** — same always-on behavior, more robust to crashes and reboots.

If you later install `tmux` or `screen` and want a persistent `/goal`
session as the primary worker:

```bash
# rough sketch — needs tmux/screen installed
tmux new -d -s btc-autopilot 'cd /home/btcai/btc_analyst && hermes chat'
tmux send -t btc-autopilot \
  '/goal Iterate BTC Analyst toward full framework parity per BTC Swing Trading Framework.md. Never stop.' \
  Enter
```

Then keep the cron jobs as the safety net (re-launch tmux session if it
dies). The current cron-only setup is functionally equivalent and survives
reboots.
