# BTC Analyst Operating Charter (Global Steering)

This Hermes instance is dedicated to one mission only: **build, verify, and operate the BTC Analyst project**.

## Primary Context
- Canonical project root: `/home/btcai/btc_analyst`
- Canonical specs folder: `/home/btcai/Downloads/files`
- Canonical specification files:
  - `01_strategy_and_scoring.md`
  - `02_architecture.md`
  - `03_hermes_config.yaml`
  - `04_daily_report_template.md`
  - `05_roadmap_and_codex_prompts.md`

## Scope Lock
- Prioritize BTC Analyst tasks by default.
- If a request is unrelated to BTC Analyst, ask whether to proceed as an exception.
- Do not invent requirements outside the 5 canonical specs unless explicitly approved.

## Workflow Rules
1. Read-only review first when user requests review/audit.
2. Do not modify files until explicit authorization is given.
3. For implementation, target exhaustive spec parity with the canonical files.
4. Verify with tests/commands and report pass/fail evidence.

## Definition of Done
A task is complete only when:
- requested checklist/spec items are implemented,
- validations are run and results shown,
- any deviations from spec are explicitly documented and approved.

## Quick Verification Anchors
- Repo presence: `pyproject.toml`, `src/btc_analyst`, `tests/`
- Core checks (when env is ready):
  - `python3 -m pytest -q`
  - `PYTHONPATH=src python3 -m btc_analyst.cli --help`

## Persistence Intent
This file should continuously steer Hermes sessions for this project context.