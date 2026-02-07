---
name: clickhouse-antipatterns
description: ClickHouse SQL anti-patterns and performance constraints discovered during Gen200-202 triple barrier framework. Use when writing ClickHouse SQL, creating new barrier/pattern generations, modifying array functions, window functions, parameter sweeps, or encountering slow queries, OOM, NULL entry prices, wrong barrier detection, or arrayFirstIndex returning 0. TRIGGERS - ClickHouse SQL, barrier SQL, array function, window function, trailing stop SQL, parameter sweep, slow query, OOM, arrayFirstIndex, leadInFrame, groupArray, arrayFold, arrayScan, threshold-relative, anti-pattern, performance constraint.
---

# ClickHouse Anti-Patterns for Range Bar Pattern SQL

Discovered during Gen200-202 Triple Barrier + Trailing Stop framework implementation. Each anti-pattern has been validated through production failures and resolved with tested workarounds.

**GitHub Issue**: [#8 - Anti-Pattern Registry](https://github.com/terrylica/rangebar-patterns/issues/8)

## Quick Lookup

| ID    | Anti-Pattern                                  | Severity      | Section                                                                   |
| ----- | --------------------------------------------- | ------------- | ------------------------------------------------------------------------- |
| AP-01 | groupArray memory explosion (2.36 GB)         | CRITICAL      | [Array Functions](#ap-01-grouparray-memory-explosion)                     |
| AP-02 | Lambda closure over outer columns (CH #45028) | HIGH          | [Array Functions](#ap-02-lambda-closure-over-outer-columns)               |
| AP-03 | arrayFirstIndex returns 0 for not-found       | HIGH          | [Array Functions](#ap-03-arrayfirstindex-returns-0-for-not-found)         |
| AP-04 | arrayMap + arrayReduce O(n^2) complexity      | MEDIUM        | [Array Functions](#ap-04-arraymap--arrayreduce-on2-complexity)            |
| AP-05 | arrayScan does not exist in ClickHouse        | LOW           | [Array Functions](#ap-05-arrayscan-does-not-exist)                        |
| AP-06 | arrayFold returns only final value            | LOW           | [Array Functions](#ap-06-arrayfold-returns-only-final-value)              |
| AP-07 | leadInFrame default frame excludes next row   | HIGH          | [Window Functions](#ap-07-leadinframe-default-frame-excludes-next-row)    |
| AP-08 | arraySlice before arrayFirstIndex             | MEDIUM        | [Search Efficiency](#ap-08-arrayslice-before-arrayfirstindex)             |
| AP-09 | Absolute % params across thresholds           | HIGH          | [Parameter Grid](#ap-09-absolute-percentage-parameters-across-thresholds) |
| AP-10 | Expanding vs rolling p95 divergence           | ARCHITECTURAL | [Signal Detection](#ap-10-expanding-vs-rolling-p95-signal-divergence)     |
| AP-11 | TP/SL from signal close, not entry price      | MEDIUM        | [Barrier Alignment](#ap-11-tpsl-from-signal-close-not-entry-price)        |
| AP-12 | Same-bar TP+SL ambiguity (SL wins)            | MEDIUM        | [Barrier Alignment](#ap-12-same-bar-tpsl-ambiguity)                       |
| AP-13 | Gap-down SL execution price                   | MEDIUM        | [Barrier Alignment](#ap-13-gap-down-sl-execution-price)                   |

For detailed descriptions with code examples, see [references/anti-patterns.md](./references/anti-patterns.md).
For infrastructure-specific issues, see [references/infrastructure.md](./references/infrastructure.md).

## Critical Rules (Never Violate)

### 1. Signals BEFORE Arrays

```sql
-- CORRECT: Filter to signals first, THEN collect forward arrays
signals AS (SELECT * FROM signal_detection WHERE <conditions>),
forward_arrays AS (
    SELECT s.*, groupArray(b.high) AS fwd_highs ...
    FROM signals s INNER JOIN base_bars b ON b.rn BETWEEN s.rn + 1 AND s.rn + 51
    GROUP BY ...
)

-- WRONG: Collect arrays on ALL bars (1.4M x 4 arrays x 51 = 2.36 GB)
forward_arrays AS (
    SELECT *, groupArray(high) OVER (ROWS BETWEEN 1 FOLLOWING AND 51 FOLLOWING) ...
    FROM base_bars  -- 1.4M rows!
)
```

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

## Post-Change Checklist

After modifying ANY Gen200+ SQL file:

- [ ] Forward arrays collected on SIGNALS only (not all bars)
- [ ] tp_price/sl_price pre-computed as columns (not in lambda)
- [ ] All arrayFirstIndex comparisons have `> 0` guards
- [ ] leadInFrame uses `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`
- [ ] Parameters use threshold-relative multipliers
- [ ] SL exit price uses `least(open, sl_price)` for gap-down
- [ ] TP exit price is exactly `tp_price` (limit fill)
- [ ] Same-bar TP+SL: SL wins (raw_sl_bar <= raw_tp_bar)
- [ ] arraySlice applied before arrayFirstIndex search
- [ ] Query completes < 60s on @500dbps (~1,900 signals)
