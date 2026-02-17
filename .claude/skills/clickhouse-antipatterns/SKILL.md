---
name: clickhouse-antipatterns
description: ClickHouse SQL anti-patterns and performance constraints discovered during Gen200-Gen600 barrier framework. Use when writing ClickHouse SQL, creating new barrier/pattern generations, modifying array functions, window functions, parameter sweeps, forward arrays, or encountering slow queries, OOM, NULL entry prices, wrong barrier detection, arrayFirstIndex returning 0, or aligning SQL results with backtesting.py. TRIGGERS - ClickHouse SQL, barrier SQL, array function, window function, trailing stop SQL, parameter sweep, slow query, OOM, arrayFirstIndex, leadInFrame, groupArray, arrayFold, arrayScan, threshold-relative, anti-pattern, performance constraint, forward arrays, self-join, O(N×M), SQL vs Python, SQL vs backtesting.
---

# ClickHouse Anti-Patterns for Range Bar Pattern SQL

Discovered during Gen200-Gen600 Triple Barrier + Hybrid Feature Sweep framework implementation. Each anti-pattern has been validated through production failures and resolved with tested workarounds.

**Companion skills**: `quant-research:backtesting-py-oracle` (Python-side anti-patterns) | [sweep-methodology](../sweep-methodology/SKILL.md) (sweep design)

**GitHub Issue**: [#8 - Anti-Pattern Registry](https://github.com/terrylica/rangebar-patterns/issues/8)

## Quick Lookup

| ID    | Anti-Pattern                                  | Severity | Section                                                                            |
| ----- | --------------------------------------------- | -------- | ---------------------------------------------------------------------------------- |
| AP-01 | groupArray memory explosion (2.36 GB)         | CRITICAL | [Array Functions](#ap-01-grouparray-memory-explosion)                              |
| AP-02 | Lambda closure over outer columns (CH #45028) | HIGH     | [Array Functions](#ap-02-lambda-closure-over-outer-columns)                        |
| AP-03 | arrayFirstIndex returns 0 for not-found       | HIGH     | [Array Functions](#ap-03-arrayfirstindex-returns-0-for-not-found)                  |
| AP-04 | arrayMap + arrayReduce O(n^2) complexity      | MEDIUM   | [Array Functions](#ap-04-arraymap--arrayreduce-on2-complexity)                     |
| AP-05 | arrayScan does not exist in ClickHouse        | LOW      | [Array Functions](#ap-05-arrayscan-does-not-exist)                                 |
| AP-06 | arrayFold returns only final value            | LOW      | [Array Functions](#ap-06-arrayfold-returns-only-final-value)                       |
| AP-07 | leadInFrame default frame excludes next row   | HIGH     | [Window Functions](#ap-07-leadinframe-default-frame-excludes-next-row)             |
| AP-08 | arraySlice before arrayFirstIndex             | MEDIUM   | [Search Efficiency](#ap-08-arrayslice-before-arrayfirstindex)                      |
| AP-09 | Absolute % params across thresholds           | HIGH     | [Parameter Grid](#ap-09-absolute-percentage-parameters-across-thresholds)          |
| AP-10 | NEVER expanding window, always rolling 1000   | CRITICAL | [Signal Detection](#ap-10-never-use-expanding-window--always-rolling-1000-bar)     |
| AP-11 | TP/SL from signal close, not entry price      | MEDIUM   | [Barrier Alignment](#ap-11-tpsl-from-signal-close-not-entry-price)                 |
| AP-12 | Same-bar TP+SL ambiguity (SL wins)            | MEDIUM   | [Barrier Alignment](#ap-12-same-bar-tpsl-ambiguity)                                |
| AP-13 | Gap-down SL execution price                   | MEDIUM   | [Barrier Alignment](#ap-13-gap-down-sl-execution-price)                            |
| AP-14 | Self-join forward arrays O(N×M) bottleneck    | CRITICAL | [Forward Arrays](#ap-14-self-join-forward-arrays-onm-bottleneck)                   |
| AP-15 | Signal timing off-by-one with lagInFrame      | HIGH     | [Signal Detection](#ap-15-signal-timing-off-by-one-with-laginframe)                |
| AP-16 | backtesting.py multi-position mode for oracle | HIGH     | [Barrier Alignment](#ap-16-backtestingpy-multi-position-mode-for-sql-oracle-match) |

For detailed descriptions with code examples, see [references/anti-patterns.md](./references/anti-patterns.md).
For infrastructure-specific issues, see [references/infrastructure.md](./references/infrastructure.md).

## Critical Rules (Never Violate)

### 1. Window-Based Forward Arrays (NOT Self-Join)

```sql
-- CORRECT: Pre-compute forward arrays as window functions in base_bars (11s, 1.5 GB)
base_bars AS (
    SELECT *,
        arraySlice(groupArray(high) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_highs,
        arraySlice(groupArray(low) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_lows,
        -- same for fwd_opens, fwd_closes
    FROM range_bars WHERE ...
)
-- Then carry fwd_* arrays through CTEs, no self-join needed

-- WRONG: Self-join for forward arrays (133s, 165 MB but 11x slower)
forward_arrays AS (
    SELECT s.*, groupArray(b.high) AS fwd_highs ...
    FROM signals s INNER JOIN base_bars b ON b.rn BETWEEN s.rn + 1 AND s.rn + 101
    GROUP BY ...
)
-- The range join ON b.rn BETWEEN s.rn + 1 AND s.rn + 101 is O(N×M) — ClickHouse
-- cannot index into a CTE and does a nested loop scan.
```

**Memory tradeoff**: Window approach uses ~10x more memory (1.5 GB vs 165 MB) because it computes arrays for ALL bars, not just signals. At 16 parallel queries: 1.5 GB × 16 = 24 GB — safe on 61 GB hosts. For memory-constrained hosts, the self-join is acceptable for sparse patterns (<2% signal coverage).

**Gen600 Production Confirmation** (2026-02-11): AP-14 window approach confirmed at scale — 284K+ results collected at 3.2 queries/sec (xargs -P16), 3-5s per query regardless of pattern density (sparse 1.2% to dense 49%), zero errors, memory stable at ~24 GB peak (1.5 GB/query × 16 parallel).

**Historical note**: AP-01 originally recommended self-join over window approach because Gen200 had 1.4M bars × 51 elements = 2.36 GB with the WRONG window frame (`ROWS BETWEEN 1 FOLLOWING AND 51 FOLLOWING` on ALL bars). The CORRECT window approach uses `arraySlice(..., 2, 101)` on `ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING` — slicing off the current row. Gen600 benchmarking proved the window approach is 11x faster for dense patterns (36K+ signals) where the self-join becomes the dominant bottleneck.

### 2. Pre-Compute Barrier Prices as Columns

```sql
-- CORRECT: Pre-compute in separate CTE (avoids CH bug #45028)
param_with_prices AS (
    SELECT *, entry_price * (1.0 + tp_mult * 0.025) AS tp_price FROM param_expanded
),
barrier_scan AS (
    SELECT arrayFirstIndex(x -> x >= tp_price, ...) AS raw_tp_bar FROM param_with_prices
)

-- WRONG: Lambda closure over outer column
SELECT arrayFirstIndex(x -> x >= entry_price * (1.0 + tp_mult * 0.025), fwd_highs)
```

### 3. Always Guard arrayFirstIndex with > 0

```sql
-- CORRECT: Explicit 0-not-found guards
CASE
    WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
    WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
    WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN 'SL'
    WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN 'TP'
    WHEN window_bars >= max_bars THEN 'TIME'
    ELSE 'INCOMPLETE'
END

-- WRONG: No guard (0 < any positive = always true)
CASE WHEN raw_tp_bar <= raw_sl_bar THEN 'TP' ELSE 'SL' END
```

### 4. leadInFrame Requires UNBOUNDED FOLLOWING

```sql
-- CORRECT: Explicit frame includes next row
leadInFrame(open, 1) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
) AS entry_price

-- WRONG: Default frame excludes next row, returns NULL
leadInFrame(open, 1) OVER (ORDER BY timestamp_ms) AS entry_price
```

### 5. Threshold-Relative Parameters

```sql
-- CORRECT: Multipliers scale with threshold
entry_price * (1.0 + tp_mult * 0.025) AS tp_price  -- @250dbps
entry_price * (1.0 + tp_mult * 0.05)  AS tp_price  -- @500dbps

-- WRONG: Absolute percentages (don't scale)
entry_price * (1.0 + 0.01) AS tp_price  -- Same 1% regardless of threshold
```

### 6. NEVER Expanding Window — Always Rolling 1000-Bar

```sql
-- CORRECT: Rolling 1000-bar window
quantileExactExclusive(0.95)(trade_intensity) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
) AS ti_p95_rolling

-- WRONG: Expanding window (inflates early-data quality, produces false-positive Kelly)
quantileExactExclusive(0.95)(trade_intensity) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
) AS ti_p95_expanding
```

## Post-Change Checklist

After modifying ANY Gen200+ SQL file:

- [ ] Forward arrays use window-based approach in base_bars (NOT self-join) — see AP-14 / Critical Rule #1
- [ ] tp_price/sl_price pre-computed as columns (not in lambda)
- [ ] All arrayFirstIndex comparisons have `> 0` guards
- [ ] leadInFrame uses `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`
- [ ] Parameters use threshold-relative multipliers
- [ ] **ALL quantiles use rolling 1000-bar window (`ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`), NEVER expanding (`UNBOUNDED PRECEDING`)**
- [ ] Warmup guard `rn > 1000` present for rolling window stability
- [ ] SL exit price uses `least(open, sl_price)` for gap-down
- [ ] TP exit price is exactly `tp_price` (limit fill)
- [ ] Same-bar TP+SL: SL wins (raw_sl_bar <= raw_tp_bar)
- [ ] arraySlice applied before arrayFirstIndex search
- [ ] Query completes < 10s on any pattern density (AP-14 window approach)
- [ ] `lagInFrame` direction lags are correct — current bar uses `direction` directly, not `lagInFrame(direction, 1)` (AP-15)
- [ ] backtesting.py oracle uses `hedging=True, exclusive_orders=False` for multi-position SQL match (AP-16)
- [ ] Derived artifacts (Parquet chunks, combo JSONs) include ALL category dimensions in filename — `_chunk_{direction}_{fmt}_{sym}_{thr}` not `_chunk_{fmt}_{sym}_{thr}` (INV-9)
