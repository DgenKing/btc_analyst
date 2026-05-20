# BTC Analyst — Verified Free Data Sources (Reviewed)

Last reviewed: 2026-05-17

## Summary
This document is the corrected/operational version of the free-source stack.
Main corrections from prior draft:
- OKX Rubik long/short endpoint does **not** support `4H`; use `5m|1H|1D`.
- OKX Rubik rows may return as arrays (`[ts, ratio]`) not only dict objects.
- Binance access is **environment-dependent** (not universally blocked).
- CoinGlass is removed entirely from this repo.

## Tier A — No key, no signup
- Bybit public REST/WS (klines, funding history, OI, account ratio, orderbook, trades)
- OKX public REST/WS (klines, funding, OI, Rubik ratios, taker volume, liquidations)
- Hyperliquid `/info` + WS (funding/OI divergence context)
- Deribit public v2 (options OI + put/call + DVOL)
- Alternative.me Fear & Greed
- Mempool.space API
- Reddit JSON (with explicit User-Agent)

## Tier B — Free key/signup (optional enrichers)
- CoinGecko (global context / BTC dominance)
- CryptoCompare/CoinDesk (news + social)

## Operational requirements (must-have)
1. Retry/backoff policy per source:
   - retry on 429/5xx with exponential backoff + jitter
   - fail-fast on non-retriable 4xx
2. Source-health tracking in snapshots/report:
   - source availability map
   - coverage score = available_sources / expected_sources
   - missing source list surfaced in report
3. Normalization:
   - funding as decimal per 8h-equivalent
   - OI normalized to comparable unit before aggregation
   - timestamps UTC
4. Degrade gracefully:
   - any single source failure must not stop snapshot/report generation.

## CoinGlass replacement map
- Aggregate funding: OI-weighted from Bybit + OKX (+ Hyperliquid if normalized)
- Aggregate L/S: blend Bybit account ratio + OKX position/account ratio (document formula)
- Liquidations: Bybit/OKX direct liquidation streams/history
- Options OI: Deribit (native source)

## Notes for this repository
- CoinGlass code/config/secrets have been removed.
- OKX long/short fetcher patched for:
  - period mapping (`4H -> 1H` fallback)
  - array-row parser support
  - browser-like headers to reduce false blocks
- Shared HTTP utility now includes retry/backoff on transient errors.
