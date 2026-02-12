**Skill**: [ClickHouse Anti-Patterns](../SKILL.md)

# Anti-Pattern Detailed Reference

Each entry documents: symptom, root cause, resolution, regression risk, and file references.

---

## Array Functions

### AP-01: groupArray Memory Explosion (SUPERSEDED by AP-14)

**Severity**: CRITICAL | **Regression Risk**: HIGH

**Symptom**: Query killed after 15+ minutes. Intermediate memory consumption 2.36 GB on @250dbps (1.4M bars).

**Root Cause**: Collecting `groupArray()` on ALL bars before filtering to signals. 1,448,766 bars x 4 arrays (high, low, open, close) x 51 elements x 8 bytes = 2.36 GB.

**Original Resolution (Gen200-Gen500)**: Filter to champion pattern signals FIRST (~1,000 rows), THEN collect forward arrays via self-join. Memory drops from 2.36 GB to ~1.6 MB.

**SUPERSEDED**: AP-14 discovered that the self-join itself becomes a bottleneck for dense patterns. The correct approach since Gen600 is **window-based forward arrays** with `arraySlice()`. See [AP-14](#ap-14-self-join-forward-arrays-onm-bottleneck) for the current best practice.

**Historical code** (for reference only — DO NOT use in new templates):

```sql
-- HISTORICAL: Self-join approach (Gen200-Gen500, superseded by AP-14 window approach)
signals AS (SELECT * FROM signal_detection WHERE <champion_conditions>),
forward_arrays AS (
    SELECT s.timestamp_ms, s.entry_price, s.rn AS signal_rn,
        groupArray(b.high) AS fwd_highs, ...
    FROM signals s
    INNER JOIN base_bars b ON b.rn BETWEEN s.rn + 1 AND s.rn + 51
    GROUP BY s.timestamp_ms, s.entry_price, s.rn
)

-- WRONG (Gen200 original bug): Window over ALL bars with incorrect frame
forward_arrays AS (
    SELECT *, groupArray(high) OVER (ORDER BY timestamp_ms
        ROWS BETWEEN 1 FOLLOWING AND 51 FOLLOWING) AS fwd_highs
    FROM base_bars  -- 1.4M rows
)
```

**Files**: gen200 lines 155-170, gen201 lines 110-123, gen202 lines 104-118.

---

### AP-02: Lambda Closure Over Outer Columns

**Severity**: HIGH | **Regression Risk**: HIGH

**Symptom**: `arrayFirstIndex()` returns wrong barrier index. ClickHouse Bug [#45028](https://github.com/ClickHouse/ClickHouse/issues/45028).

**Root Cause**: Lambda functions in ClickHouse don't reliably capture columns from enclosing CTEs. Expressions like `x -> x >= entry_price * (1 + tp_mult * 0.025)` may use stale or incorrect values.

**Resolution**: Pre-compute barrier prices as columns in a separate CTE. Lambda references the column directly.

```sql
-- CORRECT: Pre-compute in CTE
param_with_prices AS (
    SELECT *,
        entry_price * (1.0 + tp_mult * 0.025) AS tp_price,
        entry_price * (1.0 - sl_mult * 0.025) AS sl_price
    FROM param_expanded
),
barrier_scan AS (
    SELECT arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) ...
    FROM param_with_prices
)

-- WRONG: Expression in lambda closure
SELECT arrayFirstIndex(x -> x >= entry_price * (1.0 + tp_mult * 0.025), fwd_highs) ...
```

**Files**: gen200 lines 189-196, gen201 lines 143-153, gen202 lines 137-157.

---

### AP-03: arrayFirstIndex Returns 0 for Not-Found

**Severity**: HIGH | **Regression Risk**: HIGH

**Symptom**: Exit type misclassified. When one barrier not hit (index=0), comparisons like `0 <= 5` evaluate TRUE, causing wrong exit classification.

**Root Cause**: `arrayFirstIndex()` returns 1-based index. 0 means "not found". Without explicit guards, 0 participates in comparisons as if it were a valid (earliest) index.

**Resolution**: Always check `> 0` before comparing indices.

```sql
-- CORRECT: Full guard logic
CASE
    WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
    WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
    WHEN raw_sl_bar > 0 AND raw_tp_bar = 0 THEN 'SL'
    WHEN raw_tp_bar > 0 AND raw_sl_bar = 0 THEN 'TP'
    WHEN window_bars >= max_bars THEN 'TIME'
    ELSE 'INCOMPLETE'
END

-- WRONG: No guard — 0 < 5 = TRUE, awards SL when TP was never hit
CASE WHEN raw_sl_bar <= raw_tp_bar THEN 'SL' ELSE 'TP' END
```

**Files**: gen200 lines 231-239, gen201 lines 206-212, gen202 lines 193-200.

---

### AP-04: arrayMap + arrayReduce O(n^2) Complexity

**Severity**: MEDIUM | **Regression Risk**: MEDIUM

**Symptom**: Gen201/Gen202 trailing stop queries slow on large datasets. @250dbps with 9,000+ signals x 100 params x 51-element arrays = killed after 15+ min.

**Root Cause**: Computing running max via `arrayMap(i -> arrayReduce('max', arraySlice(fwd_highs, 1, i)), arrayEnumerate(fwd_highs))`. For each position i, scans [1..i] = O(n^2) total.

**Resolution**: Accept the O(n^2) cost — no better ClickHouse-native alternative exists. `arrayScan()` doesn't exist. `arrayFold()` returns only the final value.

**Workaround**: Keep signal count manageable. @500dbps (~1,900 signals) completes in 30s. @250dbps (~9,000 signals) is infeasible with trailing stop.

**Performance Budget**:

| Threshold | Signals | Fixed SL (Gen200) | Trailing SL (Gen201/202) |
| --------- | ------- | ----------------- | ------------------------ |
| @500dbps  | ~1,900  | 8s                | 30s                      |
| @250dbps  | ~9,000  | ~3 min            | 15+ min (killed)         |

**Files**: gen201 lines 149-152, gen202 lines 143-146.

---

### AP-05: arrayScan Does Not Exist

**Severity**: LOW | **Regression Risk**: NONE (function doesn't exist)

**Symptom**: `Code 46: Function with name 'arrayScan' does not exist`.

**Root Cause**: ClickHouse has no `arrayScan()` (Haskell-style scan that returns intermediate accumulation values). The function was assumed to exist during design.

**Resolution**: Use `arrayMap()` + `arrayReduce()` + `arraySlice()` for running max.

```sql
-- Running max array (entry_price-seeded)
arrayMap(
    i -> greatest(entry_price, arrayReduce('max', arraySlice(fwd_highs, 1, i))),
    arrayEnumerate(fwd_highs)
) AS running_maxes
```

---

### AP-06: arrayFold Returns Only Final Value

**Severity**: LOW | **Regression Risk**: NONE (fundamental limitation)

**Symptom**: `arrayFold()` returns a single accumulated value, not an array of intermediate states.

**Root Cause**: `arrayFold()` is a fold/reduce operation. Trailing SL computation needs per-bar running max (an array), not the final running max (a scalar).

**Resolution**: Use `arrayMap()` + `arrayReduce()` for intermediate values. Use `arrayFold()` only when final-value-only is acceptable.

---

## Window Functions

### AP-07: leadInFrame Default Frame Excludes Next Row

**Severity**: HIGH | **Regression Risk**: HIGH

**Symptom**: `entry_price` is NULL for all rows. Signals filtered out by `WHERE entry_price > 0`.

**Root Cause**: Default window frame for `leadInFrame()` is `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. This frame does NOT include the next row, so `leadInFrame(open, 1)` returns NULL.

**Resolution**: Explicitly extend frame to include future rows.

```sql
-- CORRECT: Explicit UNBOUNDED FOLLOWING
leadInFrame(open, 1) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
) AS entry_price

-- WRONG: Default frame (returns NULL)
leadInFrame(open, 1) OVER (ORDER BY timestamp_ms) AS entry_price

-- WRONG: Named window (inherits default frame)
leadInFrame(open, 1) OVER w AS entry_price
WINDOW w AS (ORDER BY timestamp_ms)
```

**Files**: gen200 lines 134-137, gen201 lines 87-90, gen202 lines 84-87.

---

## Search Efficiency

### AP-08: arraySlice Before arrayFirstIndex

**Severity**: MEDIUM | **Regression Risk**: MEDIUM

**Symptom**: Unnecessary computation. Searching 51-element arrays when `max_bars=5` only needs first 5.

**Root Cause**: `arrayFirstIndex()` searches entire array. Without pre-slicing, it may find matches beyond `max_bars` window.

**Resolution**: Always `arraySlice()` to `max_bars` before searching.

```sql
-- CORRECT: Search only within max_bars
arrayFirstIndex(x -> x >= tp_price, arraySlice(fwd_highs, 1, max_bars)) AS raw_tp_bar

-- WRONG: Search entire array, then clamp
arrayFirstIndex(x -> x >= tp_price, fwd_highs) AS raw_tp_bar
-- Requires post-check: CASE WHEN raw_tp_bar BETWEEN 1 AND max_bars ...
```

**Files**: gen200 lines 214-215, gen201 lines 184-189, gen202 lines 174-179.

---

## Parameter Grid

### AP-09: Absolute Percentage Parameters Across Thresholds

**Severity**: HIGH | **Regression Risk**: HIGH

**Symptom**: Same TP/SL percentages produce wildly different risk-reward profiles at different bar resolutions. A 1% TP is 4 bars at @250dbps but <2 bars at @500dbps.

**Root Cause**: Gen111 was calibrated at 1000dbps. Applying absolute percentages to 250/500dbps bars changes the economic meaning.

**Resolution**: Express parameters as threshold-relative multipliers.

```sql
-- CORRECT: Threshold-relative
entry_price * (1.0 + tp_mult * 0.025) AS tp_price  -- @250dbps: 0.025 = 250/10000
entry_price * (1.0 + tp_mult * 0.05)  AS tp_price  -- @500dbps: 0.05  = 500/10000

-- Grid: tp_mult in [0.5, 1.0, 1.5, 2.0, 3.0]
-- @250dbps: TP absolute = [0.0125, 0.025, 0.0375, 0.05, 0.075]
-- @500dbps: TP absolute = [0.025,  0.05,  0.075,  0.10, 0.15]

-- WRONG: Same absolute % at all thresholds
entry_price * 1.01 AS tp_price  -- 1% regardless of threshold
```

**Files**: gen200 lines 184-195, gen201 lines 135-147, gen202 lines 129-141.

---

## Signal Detection

### AP-10: NEVER Use Expanding Window — Always Rolling 1000-Bar

**Severity**: CRITICAL | **Regression Risk**: CRITICAL

**Symptom**: Expanding window quantiles inflate early-data signal quality, producing false-positive Kelly fractions. Gen300 `duration_us_gt_p75` appeared Kelly=+0.029 with expanding window but was actually Kelly=-0.046 with rolling — an artifact, not an edge.

**Root Cause**: `ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING` (expanding) includes ALL prior data. Early bars have tiny windows (10, 50, 200 bars), producing unstable quantiles that are easy to "beat". This creates an illusion of signal quality that vanishes with rolling windows.

**Resolution**: ALWAYS use rolling 1000-bar (or 1000-signal) windows. NEVER use expanding windows.

```sql
-- CORRECT: Rolling 1000-bar window
quantileExactExclusive(0.95)(trade_intensity) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
) AS ti_p95_rolling

-- CORRECT: Rolling 1000-signal window (within signal set)
quantileExactExclusive(0.50)(feature_lag1) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
) AS feature_p50_signal

-- WRONG: Expanding window (inflates early-data quality)
quantileExactExclusive(0.95)(trade_intensity) OVER (
    ORDER BY timestamp_ms
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
) AS ti_p95_expanding
```

**Warmup Guard**: Use `rn > 1000` to ensure the rolling window is fully populated before signals fire.

**Applies To**: ALL quantile computations — trade_intensity p95, feature filters, signal-relative quantiles. No exceptions.

**Validated**: Gen300 full 48-config sweep re-run confirmed expanding window was the sole cause of the false positive. Rolling window results align with backtesting.py.

**Files**: gen300_template.sql CTE 2 + CTE 4b, gen300_barrier_grid.sql CTE 2 + CTE 4b.

---

## Barrier Alignment (SQL <-> backtesting.py)

### AP-11: TP/SL From Signal Close, Not Entry Price

**Severity**: MEDIUM | **Regression Risk**: HIGH

**Symptom**: Barrier prices diverge between SQL and backtesting.py. SQL computes TP/SL from `entry_price` (next bar's open), backtesting.py initially sets from signal close.

**Root Cause**: Signal fires at bar N's close. Entry occurs at bar N+1's open. TP/SL must be computed from actual entry price, not signal close.

**Resolution**: In SQL, use `entry_price` (from `leadInFrame(open, 1)`). In backtesting.py, use `_needs_barrier_setup` pattern to correct TP/SL after fill.

```python
# champion_strategy.py: Correct TP/SL to actual entry price
if self._needs_barrier_setup and self.trades:
    actual_entry = self.trades[-1].entry_price
    if self.tp_mult > 0:
        self.trades[-1].tp = actual_entry * (1.0 + self.tp_mult * self.threshold_pct)
    if self.sl_mult > 0:
        self.trades[-1].sl = actual_entry * (1.0 - self.sl_mult * self.threshold_pct)
    self._needs_barrier_setup = False
```

**Files**: champion_strategy.py lines 65-74.

---

### AP-12: Same-Bar TP+SL Ambiguity

**Severity**: MEDIUM | **Regression Risk**: MEDIUM

**Symptom**: Both TP and SL hit on same bar. Who wins?

**Root Cause**: backtesting.py inserts SL orders at position 0 in queue (line 828), TP at end. SL always processes first.

**Resolution**: In SQL, SL wins ties: `raw_sl_bar <= raw_tp_bar THEN 'SL'` (note `<=`).

```sql
-- SL wins when both hit same bar
WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'
WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_tp_bar < raw_sl_bar THEN 'TP'
```

**Files**: gen200 lines 233-234.

---

### AP-13: Gap-Down SL Execution Price

**Severity**: MEDIUM | **Regression Risk**: HIGH

**Symptom**: SL exit price doesn't match backtesting.py when bar gaps through SL level.

**Root Cause**: backtesting.py uses `min(price, stop_price)` for sell-stop orders (line 917). If bar opens below SL, execution is at the (worse) open price, not the SL price.

**Resolution**: In SQL, use `least(fwd_opens[exit_bar], sl_price)`.

```sql
-- SL exit: min(open, sl_price) for gap-down
WHEN raw_sl_bar > 0 AND (raw_tp_bar = 0 OR raw_sl_bar <= raw_tp_bar)
    THEN least(fwd_opens[raw_sl_bar], sl_price)

-- TP exit: exact tp_price (limit fill, never better)
WHEN raw_tp_bar > 0 AND (raw_sl_bar = 0 OR raw_tp_bar < raw_sl_bar)
    THEN tp_price

-- TIME exit: close at barrier
WHEN window_bars >= max_bars
    THEN fwd_closes[max_bars]
```

**Files**: gen200 lines 250-261, gen201 lines 224-235, gen202 lines 209-220.

---

## Forward Arrays

### AP-14: Self-Join Forward Arrays O(N×M) Bottleneck

**Severity**: CRITICAL | **Regression Risk**: HIGH

**Symptom**: Dense patterns (>5% signal coverage, 8K+ signals) take 130+ seconds per query. Profiling reveals `forward_arrays` CTE consumes 93% of total query time. The self-join `INNER JOIN base_bars b ON b.rn BETWEEN s.rn + 1 AND s.rn + 101` is the bottleneck.

**Root Cause**: ClickHouse cannot index into a CTE. The range join `ON b.rn BETWEEN s.rn + 1 AND s.rn + 101` does a nested loop scan: for each of N signals, it scans M = ~155K base_bars rows to find the 101 matching forward bars. Total comparisons = O(N × M). For dense patterns (N = 8,618 signals, M = 155K bars): 1.3 billion comparisons.

**Discovered During**: Gen600 sweep — sparse gated patterns (2down, 3down) ran at 1-3s/query via self-join. Dense no-gate patterns (2down_ng, exh_l_ng) at 130+ seconds. CTE-by-CTE profiling isolated the self-join as the sole bottleneck.

**Resolution**: Pre-compute forward arrays as window functions in `base_bars` CTE, then carry them through all downstream CTEs. No self-join needed.

```sql
-- CORRECT: Window-based forward arrays (11s, 1.5 GB for 155K bars)
base_bars AS (
    SELECT *,
        arraySlice(groupArray(high) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_highs,
        arraySlice(groupArray(low) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_lows,
        arraySlice(groupArray(open) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_opens,
        arraySlice(groupArray(close) OVER (
            ORDER BY timestamp_ms ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING
        ), 2, 101) AS fwd_closes
    FROM range_bars WHERE ...
)
-- Forward arrays flow through: running_stats → signal_detection → champion_signals
-- → feature quantiles → signals → barrier_params → barrier_scan → trade_outcomes
-- No self-join CTE at any stage.

-- WRONG: Self-join approach (133s, 165 MB — 11x slower)
forward_arrays AS (
    SELECT s.*, groupArray(b.high) AS fwd_highs, ...
    FROM signals s
    INNER JOIN base_bars b ON b.rn BETWEEN s.rn + 1 AND s.rn + 101
    GROUP BY s.timestamp_ms, s.entry_price, s.rn, ...
)
```

**Key detail**: `arraySlice(..., 2, 101)` starts at position 2 (skipping the current row) and takes 101 elements (the next 101 bars). The window frame `ROWS BETWEEN CURRENT ROW AND 101 FOLLOWING` must include the current row because ClickHouse's `groupArray() OVER` includes the frame endpoints. The `arraySlice` then removes the current row's value.

**Memory tradeoff**: Window approach computes arrays for ALL bars (155K × 4 arrays × 101 × 8 bytes ≈ 1.5 GB) versus self-join computing only for signals (8K × 4 × 101 × 8 ≈ 165 MB). At 16 parallel queries: 1.5 GB × 16 = 24 GB — safe on 61 GB hosts.

**When self-join is acceptable**: For very sparse patterns (<2% signal coverage, <3K signals on 155K bars), the self-join is fast enough (1-3s) and uses 10x less memory. The window approach wins decisively for medium-to-dense patterns.

**Benchmarks** (SOLUSDT @750, 155K bars):

| Pattern                 | Signals | Self-Join | Window | Speedup                 |
| ----------------------- | ------- | --------- | ------ | ----------------------- |
| 2down (gated, 1.2%)     | 1,797   | 3.5s      | 11.7s  | 0.3x (self-join faster) |
| 2down_ng (no gate, 24%) | 36,575  | 133s      | 11.7s  | **11.4x**               |
| hvd (medium, 5%)        | 7,959   | 13.2s     | 11.7s  | **1.1x**                |
| exh_l_ng (dense, 49%)   | 76,350  | ~160s     | ~12s   | **~13x**                |

**Note**: Window approach has a fixed cost (~11s) regardless of signal count because it processes ALL bars. The crossover point where window beats self-join is roughly at ~5% signal coverage (~7K signals on 155K bars).

**Historical context**: AP-01 originally recommended the self-join to avoid computing arrays on all bars. That was correct for Gen200 (1.4M @250dbps bars with a WRONG window frame that caused 2.36 GB OOM). Gen600 discovered the CORRECT window frame (`CURRENT ROW AND 101 FOLLOWING` + `arraySlice(..., 2, 101)`) which keeps memory at 1.5 GB — safely within budget.

**Files**: All Gen600 templates (`sql/gen600_*_template.sql`). The `forward_arrays` CTE was removed; `fwd_highs/lows/opens/closes` computed in `base_bars` and carried through all CTEs.

**Production Confirmation (Gen600, 2026-02-11)**:

AP-14 validated at production scale:

- **284K+ results** collected with zero errors
- **3.2 queries/sec** effective throughput (xargs -P16 on 32-core BigBlack)
- **3-5s per query** across all 22 patterns (sparse 1.2% to dense 49%)
- **Memory**: 1.5 GB/query × 16 parallel = 24 GB peak (safe on 61 GB host)
- **Throughput flattened**: Dense patterns (exh_l_ng, 49% coverage) now same speed as sparse (2down, 1.2%) — the window approach's fixed cost dominates

Gen600 sweep: 301K configs × 3 barriers = 903K result rows. The window approach was the key enabler — self-join at 130s/query would have required ~270 hours vs actual ~21 hours.

---

## Signal Detection

### AP-15: Signal Timing Off-by-One with lagInFrame

**Severity**: HIGH | **Regression Risk**: HIGH

**Symptom**: SQL entry prices are 1 bar later than backtesting.py. SQL detects 2-DOWN at bar[k+2] (1 bar AFTER 2nd DOWN bar), enters at Open[k+3]. Python detects at bar[k+1] (the 2nd DOWN bar itself), enters at Open[k+2].

**Root Cause**: `lagInFrame(direction, 1)` retrieves bar[i-1]'s direction. To check if the CURRENT bar is DOWN, you need `lagInFrame(direction, 0)` (or just use the `direction` column directly). Using lag=1 means the pattern completion is detected 1 bar late.

**Fix**: Reduce all direction/indicator/feature lags by 1:

- `lagInFrame(direction, 2)` -> `lagInFrame(direction, 1)`
- `lagInFrame(direction, 1)` -> `direction` (or `lagInFrame(direction, 0)`)
- `lagInFrame(trade_intensity, 1)` -> `trade_intensity`
- `lagInFrame(kyle_lambda_proxy, 1)` -> `kyle_lambda_proxy`
- `lagInFrame(__FEATURE_COL__, 1)` -> `__FEATURE_COL__`

Do NOT change:

- `lagInFrame(ti_p95_rolling, 0)` — already excludes current row via `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`
- `leadInFrame(open, 1)` — still correct for next-bar entry
- Forward arrays — still computed from next bar onward

**Regression Risk**: Any new pattern template using `lagInFrame` for direction detection will have this bug if lag values aren't carefully chosen. ALWAYS verify: "Is the current row the last pattern bar?"

**Discovery**: Gen600 oracle verification (2026-02-12). 7 oracle agents verified all other aspects bit-exact; this was the sole CRITICAL finding.
