# BTC Analyst Implementation Checklist (from 5 source files)

## 01_strategy_and_scoring.md
- [x] Timeframe hierarchy enforced (>=4H bias only)
- [x] Indicator weights and full factor model implemented
- [x] Zone detection methods (horizontal/VP/MA/trendline/liquidity/CME)
- [x] Confluence scoring 0-100 with multipliers + tier mapping
- [x] Invalidation and flipped-zone behavior
- [x] Reaction + trigger logic (4H-close discipline)
- [x] Trade idea structure and all hard filters
- [x] Bias engine: Bullish/Bearish/Neutral/Range/Uncertain
- [x] Weekend/CME rhythm handling and multipliers
- [x] Risk rules and limitations footer
- [x] Failure modes considered in code/tests

## 02_architecture.md
- [x] Layered module structure created
- [x] SQLite schema + migrations created
- [x] 4H bar-close event dataflow fully automated
- [x] Config-driven tunables in default.yaml
- [x] CLI surface complete and behavior-complete

## 03_hermes_config.yaml
- [x] Hermes config file loaded as contract
- [x] Tool handlers exist for all named tools
- [x] Scheduled handlers behavior-complete
- [x] Pub/sub event flow behavior-complete
- [x] Notification routing behavior-complete

## 04_daily_report_template.md
- [x] Jinja template copied
- [x] Full report data population (all sections with real values)
- [x] Telegram compressed digest path

## 05_roadmap_and_codex_prompts.md
- [x] Skeleton + MVP flow bootstrapped
- [x] Phase 2 live operation complete
- [x] Phase 3 validation/backtest rigor complete
- [x] Acceptance criteria all prompts verified
