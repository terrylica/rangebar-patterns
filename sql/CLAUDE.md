# SQL Patterns - AI Context

**Scope**: ClickHouse SQL brute-force pattern discovery across 22 generations + no-lookahead corrections.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## ClickHouse Connection

```
clickhouse-client  # local
# or: ssh $RANGEBAR_CH_HOST 'clickhouse-client'  # remote
-- Database: rangebar_cache
-- Table: range_bars
-- Column: threshold_decimal_bps (NOT threshold_dbps)
```

## Generation Evolution

| Gen | File                         | Theme                          | Key Result                    |
| --- | ---------------------------- | ------------------------------ | ----------------------------- |
| 01  | gen01_single_feature.sql     | Single feature predictability  | 52.18%                        |
| 02  | gen02_two_feature.sql        | Two-feature combinations       | 52.98%                        |
| 03  | gen03_three_feature.sql      | Three-feature + temporal       | ~53%                          |
| 04  | gen04_temporal.sql           | Year-by-year stability         | Stability check               |
| 05  | gen05_crossasset.sql         | Cross-asset validation         | ETH inverted!                 |
| 06  | gen06_lookback.sql           | 2/3-bar lag patterns           | Momentum regimes              |
| 07  | gen07_meanrev.sql            | Mean reversion (breakthrough!) | 60.90%                        |
| 08  | gen08_divergence.sql         | Divergence & composite         | 68.32% (biased)               |
| 108 | gen108_nolookahead.sql       | Year-specific percentiles      | 66.76%                        |
| 109 | gen109_nla_temporal.sql      | NLA temporal stability         | Per-year z-scores             |
| 110 | gen110_nla_crossasset.sql    | NLA cross-asset                | BNB 71.72%, BTC 62.67%        |
| 111 | gen111_true_nolookahead.sql  | TRUE expanding-window          | **62.93%** (PRODUCTION)       |
| 112 | gen112_true_nla_temporal.sql | TRUE NLA temporal              | 2024-2025 NOT significant     |
| 200 | gen200_triple_barrier.sql    | Triple barrier (TP/SL/time)    | PF=1.27 @500dbps              |
| 201 | gen201_trailing_stop.sql     | Trailing stop loss             | No improvement (PF=1.26)      |
| 202 | gen202_combined_barrier.sql  | Combined barrier = Gen201      | Fixed SL remains champion     |
| 300 | gen300 sweep (48 configs)    | Single-feature filters         | Best Kelly +0.011 (marginal)  |
| 400 | gen400 sweep (14,224)        | Multi-feature combos (2F-4F)   | Best Kelly +0.165 (160 sigs)  |
| 500 | gen500 sweep (12,096)        | Cross-asset 2F (12 assets)     | 443 positive on 3+ assets     |
| 510 | gen510 sweep (180)           | Barrier grid on top 5          | Kelly +0.157 (TP=0.25x)       |
| 520 | gen520 sweep (3,024)         | Multi-threshold (@250/750/1K)  | Kelly +0.180 (@750 threshold) |

## Lookahead Bug Timeline

| Phase      | Method                                                 | Bug                        |
| ---------- | ------------------------------------------------------ | -------------------------- |
| Gen01-08   | Global percentiles                                     | Full lookahead             |
| Gen108-110 | `lagInFrame(p95, 1)`                                   | Lagged by 1 BAR not 1 YEAR |
| Gen111-112 | `quantileExactExclusive OVER ROWS UNBOUNDED PRECEDING` | **FIXED**                  |

## Rolling Window Policy

**NEVER use expanding windows for quantiles** — always use `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING` (rolling 1000-bar). Expanding windows create early-data instability and inflate signal quality. The Gen300 "winner" (Kelly=+0.029) was an artifact of expanding window; with rolling window it has Kelly=-0.046.

## Signal Timing Policy

**Current row IS the last pattern bar** (AP-15 compliant). When using `lagInFrame(direction, N)` for pattern detection, the lag offset must place the current row as the final bar of the pattern. `lagInFrame(direction, 1)` gets bar[i-1]'s direction — to check the current bar, use `direction` directly. See [AP-15](/.claude/skills/clickhouse-antipatterns/references/anti-patterns.md#ap-15-signal-timing-off-by-one-with-laginframe).

## Reproduction

```
mise run sql:reproduce
-- Expected: combo_2down_ti_p95_kyle_gt_0_long ~62.93% hit rate
```
