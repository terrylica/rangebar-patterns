# SQL Patterns - AI Context

**Scope**: ClickHouse SQL brute-force pattern discovery across 8 generations + no-lookahead corrections.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## ClickHouse Connection

```
ssh bigblack 'clickhouse-client'
-- Database: rangebar_cache
-- Table: range_bars
-- Column: threshold_decimal_bps (NOT threshold_dbps)
```

## Generation Evolution

| Gen | File                         | Theme                          | Champion Hit Rate         |
| --- | ---------------------------- | ------------------------------ | ------------------------- |
| 01  | gen01_single_feature.sql     | Single feature predictability  | 52.18%                    |
| 02  | gen02_two_feature.sql        | Two-feature combinations       | 52.98%                    |
| 03  | gen03_three_feature.sql      | Three-feature + temporal       | ~53%                      |
| 04  | gen04_temporal.sql           | Year-by-year stability         | Stability check           |
| 05  | gen05_crossasset.sql         | Cross-asset validation         | ETH inverted!             |
| 06  | gen06_lookback.sql           | 2/3-bar lag patterns           | Momentum regimes          |
| 07  | gen07_meanrev.sql            | Mean reversion (breakthrough!) | 60.90%                    |
| 08  | gen08_divergence.sql         | Divergence & composite         | 68.32% (biased)           |
| 108 | gen108_nolookahead.sql       | Year-specific percentiles      | 66.76%                    |
| 109 | gen109_nla_temporal.sql      | NLA temporal stability         | Per-year z-scores         |
| 110 | gen110_nla_crossasset.sql    | NLA cross-asset                | BNB 71.72%, BTC 62.67%    |
| 111 | gen111_true_nolookahead.sql  | TRUE expanding-window          | **62.93%** (PRODUCTION)   |
| 112 | gen112_true_nla_temporal.sql | TRUE NLA temporal              | 2024-2025 NOT significant |

## Lookahead Bug Timeline

| Phase      | Method                                                 | Bug                        |
| ---------- | ------------------------------------------------------ | -------------------------- |
| Gen01-08   | Global percentiles                                     | Full lookahead             |
| Gen108-110 | `lagInFrame(p95, 1)`                                   | Lagged by 1 BAR not 1 YEAR |
| Gen111-112 | `quantileExactExclusive OVER ROWS UNBOUNDED PRECEDING` | **FIXED**                  |

## Reproduction

```
mise run sql:reproduce
-- Expected: combo_2down_ti_p95_kyle_gt_0_long ~62.93% hit rate
```
