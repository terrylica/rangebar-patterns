---
name: sweep-methodology
description: Brute-force pattern sweep methodology for range bar microstructure discovery. Guidelines (not constraints) for designing, executing, and evaluating new sweep generations. Use when creating Gen600+, designing feature sweeps, setting barrier parameters, choosing evaluation metrics, or reviewing sweep results. TRIGGERS - new generation, Gen600, sweep design, feature sweep, barrier grid, evaluation metrics, cross-asset validation, multiple testing, Kelly fraction, Bonferroni, signal count, rolling window, quantile method.
---

# Sweep Methodology for Range Bar Pattern Discovery

Principles distilled from 15,300+ configurations across Gen300-Gen520. These are **guidelines**, not constraints — future generations may discover reasons to deviate. When deviating, document why.

**Companion skill**: [clickhouse-antipatterns](../clickhouse-antipatterns/SKILL.md) (SQL correctness)
**GitHub Issues**: [#9 Research Consolidation](https://github.com/terrylica/rangebar-patterns/issues/9), [#12 Beyond-Kelly](https://github.com/terrylica/rangebar-patterns/issues/12)

---

## Quick Reference: Generation Design Checklist

Before launching a new generation sweep:

- [ ] Quantile window: Rolling 1000-bar/signal (see [Signal Detection](#signal-detection))
- [ ] Feature quantiles: Computed within signal set, not all bars (see [Feature Quantile Trap](#the-feature-quantile-distribution-trap))
- [ ] Barriers: Start with Gen510 optimum (TP=0.25x, SL=0.50x, max_bars=100) unless testing barrier variation
- [ ] Minimum signal count: Filter configs with n < 100 from results (see [Sample Size](#minimum-sample-size))
- [ ] Cross-asset validation: Plan for multi-asset sweep from the start (see [Overfitting Filters](#cross-asset-validation))
- [ ] Evaluation: Use 5-metric stack, not Kelly alone (see [Evaluation](#5-metric-evaluation-stack))
- [ ] Infrastructure: Parallel SSH submissions, dedup by config_id (see [Infrastructure](#infrastructure-patterns))
- [ ] Telemetry: NDJSON format, brotli compression for >1MB (see [Telemetry](#telemetry-conventions))

---

## Signal Detection

### Rolling Window Policy

**Always use rolling 1000-bar windows for quantile computation.**

```sql
-- CORRECT: Rolling 1000-bar
ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING

-- WRONG: Expanding window (inflates early-data quality)
ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
```

**Why**: Expanding windows produce unstable quantiles in early data (first few hundred bars). The Gen300 "winner" (duration_us_gt_p75, Kelly=+0.029) was an artifact of expanding window — with rolling window it has Kelly=-0.046. This single bug wasted an entire generation's analysis.

**Warmup guard**: Always include `rn > 1000` to exclude bars where the rolling window hasn't filled.

### The Feature Quantile Distribution Trap

**Compute feature quantiles WITHIN the signal set, not over all bars.**

Champion signals (2 consecutive DOWN bars) have fundamentally different feature distributions than the global bar population. Example: Global OFI p50 ≈ 0, but champion signal OFI p50 ≈ -0.66. Using global quantiles as thresholds means the filter passes almost all signals (or almost none), defeating the purpose.

```sql
-- CORRECT: Quantile within signal set (CTE after champion_signals)
feature_quantiles AS (
    SELECT *,
        quantileExactExclusive(__QUANTILE_PCT__)(__FEATURE_COL__) OVER (
            ORDER BY timestamp_ms
            ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING
        ) AS feature_threshold
    FROM champion_signals
)

-- WRONG: Quantile over all bars (global distribution)
```

---

## Barrier Configuration

### The Barrier Inversion Principle

For mean-reversion patterns, the optimal barriers are the **inverse** of intuitive defaults:

| Parameter   | Intuitive Default | Optimal (Gen510)  | Why                                            |
| ----------- | ----------------- | ----------------- | ---------------------------------------------- |
| Take Profit | Wide (0.50x+)     | **Tight (0.25x)** | Mean reversion bounces are small and fast      |
| Stop Loss   | Tight (0.25x)     | **Wide (0.50x)**  | Price may drift further before reverting       |
| Max Bars    | Short (50)        | **Long (100)**    | Time exits destroy alpha (r=-0.965 with Kelly) |

**Quantified impact**: +283% Kelly improvement from barrier inversion alone (Gen510).

**When to deviate**: If exploring momentum/trend patterns (not mean-reversion), wider TP and tighter SL may be appropriate. Document the hypothesis.

### Threshold-Relative Parameters

Barriers must scale with the range bar threshold. A 1% TP at @250dbps spans ~3 bar moves; at @1000dbps it's ~1 bar move.

```
tp_price = entry_price * (1.0 + tp_mult * threshold_pct)
sl_price = entry_price * (1.0 - sl_mult * threshold_pct)
```

The @750dbps sweet spot (40.7% positive configs vs 21.7% at @500) suggests this threshold captures the best signal-to-noise ratio for 2-feature patterns.

---

## Overfitting Filters

### Cross-Asset Validation

**The strongest overfitting filter discovered.** A config that works on 1 asset may be noise; one that works on 7+ assets is capturing real microstructure.

| Validation Level     | Interpretation                                                                  |
| -------------------- | ------------------------------------------------------------------------------- |
| 1/12 assets positive | Asset-specific noise (the original SOLUSDT champion)                            |
| 3+ assets positive   | Candidate for further investigation                                             |
| 7+ assets positive   | Robust microstructure signal                                                    |
| 10+ assets positive  | Exceptional (only `price_impact_lt_p10__volume_per_trade_gt_p75` achieved this) |

**Best practice**: Design sweeps for multi-asset from the start. Running single-asset first and then validating cross-asset introduces confirmation bias.

### Cross-Threshold Validation

Configs that work across @250/@500/@750/@1000 are more robust than single-threshold winners. Different thresholds expose different microstructure regimes.

| Level           | Interpretation                                       |
| --------------- | ---------------------------------------------------- |
| 1/4 thresholds  | Threshold-specific artifact                          |
| 3+/4 thresholds | Structurally robust                                  |
| 4/4 thresholds  | "Gold tier" (only 6 configs achieved this in Gen520) |

### Dual Validation

The 56 configs that survive BOTH cross-asset (3+) AND cross-threshold (3+) represent the most validated patterns. Two microstructure themes emerged:

- **Theme A (Slow Accumulation)**: Low `aggregation_density` + high `duration_us` — institutional accumulation
- **Theme B (Institutional Flow)**: High `volume_per_trade` + extreme OFI/turnover_imbalance — informed directional flow

---

## Minimum Sample Size

**Filter results with n_trades < 100.**

Near-miss configs with n=8 trades can show Kelly=0.624 and Omega=5.94 — these are meaningless. The 5-metric stack (particularly MinBTL) formalizes this, but as a practical rule: ignore configs with fewer than 100 signals.

**For Bonferroni significance at typical effect sizes**:

| Kelly | Signals needed for z > 3 (Bonferroni, 1000 tests) |
| ----- | ------------------------------------------------- |
| +0.03 | ~6,000                                            |
| +0.05 | ~2,200                                            |
| +0.10 | ~550                                              |

This means most brute-force configs will never achieve statistical significance with current data volumes. The path forward is either: (1) more data (more time / more assets), or (2) NN that learns continuous relationships rather than binary thresholds.

---

## 5-Metric Evaluation Stack

Use all 5 metrics together. Kelly alone produces 218 false positives out of 220 Kelly>0 configs.

| Metric     | Role                  | Threshold      | What It Catches                                   |
| ---------- | --------------------- | -------------- | ------------------------------------------------- |
| **Kelly**  | Primary ranker        | > 0            | Edge sizing                                       |
| **Omega**  | Distribution shape    | > 1.0          | Captures full return distribution (unlike Sharpe) |
| **DSR**    | Multiple testing gate | > 0.95 (N-adj) | False Strategy Theorem — adjusts for N trials     |
| **MinBTL** | Data sufficiency      | n >= MinBTL    | Rejects claims based on too few trades            |
| **PBO**    | Overfitting detection | < 0.50         | CSCV probability of backtest overfitting          |

**Dropped metrics** (Spearman r > 0.95 with Omega — redundant): Sharpe, PSR, GROW, Cornish-Fisher ES.
**Dropped** (insufficient evidence): E-values (max=1.04, need >= 20).

**Implementation**: `src/rangebar_patterns/eval/` (10 modules, fully tested).

### DSR Caveat

DSR is effectively useless for pre-screening when testing 1000+ configs. 958/961 configs have DSR = exactly 0.000. It requires SR > 3.26 (for N=1,008 tests) — far above any observed SR. DSR is valid as a post-hoc significance test, not a filter.

---

## Recurring Feature Patterns

Features that repeatedly appear across top configs, validated cross-asset and cross-threshold:

| Feature                      | Pattern                       | Microstructure Story                                   |
| ---------------------------- | ----------------------------- | ------------------------------------------------------ |
| `price_impact`               | Low (< p50)                   | Thin spread = less friction                            |
| `volume_per_trade`           | High (> p75)                  | Institutional-sized orders                             |
| `aggregation_density`        | Low (< p25)                   | Unclustered = individual large trades                  |
| `duration_us`                | Short (< p50) or Long (> p90) | Either fast-moving (conviction) or slow (accumulation) |
| `ofi` / `turnover_imbalance` | Extreme (> p75)               | Order flow pressure                                    |
| `vwap_close_deviation`       | Extreme                       | Price dislocation from fair value                      |

**Anti-features** (consistently in losing configs): High aggression_ratio on SHORT signals.

---

## Infrastructure Patterns

The patterns below represent the current baseline (Gen500 being the most mature). Future generations should evolve beyond these — the goal is to raise the floor, not cap the ceiling.

**Reference implementations**: `scripts/gen500/` (most complete pipeline), `scripts/gen510/` (barrier grid variant)

### Concurrency Safety

Gen500 solved parallel-write corruption with `flock`. Any approach that guarantees atomic NDJSON appends is valid — flock is the current baseline:

```bash
# Gen500 baseline: flock around every append
flock "${LOG_FILE}.lock" bash -c "echo '${LINE}' >> ${LOG_FILE}"
```

Future generations might outgrow this (e.g., per-job output files merged post-hoc, a results database, streaming to a message queue). The invariant is: parallel writers must not corrupt the telemetry.

### Crash Recovery

SSH drops and pueue restarts are expected over multi-hour sweeps. Gen500 solved this with config-ID dedup — re-running `submit.sh` reads the log and skips completed configs:

```bash
# Gen500 baseline: skip already-completed config IDs
DONE_IDS=$(ssh "$HOST" "jq -r '.config_id' ${LOG_FILE} 2>/dev/null" | sort)
echo "$DONE_IDS" | grep -q "^${CONFIG_ID}$" && continue
```

The invariant: submissions must be idempotent. The mechanism can evolve (e.g., a checkpoint file, a database table, pueue's own state).

### ClickHouse Output Sanitization

ClickHouse TSV produces values that break JSON. Gen500's `collect.sh` post-processes with sed; the wrapper script also handles these inline. Either approach works — the invariant is that JSONL must be valid before consumption:

| ClickHouse Output | JSON Problem            | Gen500 Fix                                 |
| ----------------- | ----------------------- | ------------------------------------------ |
| `\N` (NULL)       | Invalid escape sequence | `sed 's/\\N/NULL/g'`                       |
| `nan`             | Not a JSON value        | `sed 's/:nan,/:null,/g; s/:nan}/:null}/g'` |
| `inf` / `-inf`    | Not a JSON value        | Wrapper: conditional replacement           |

Validate after collection: `python3 -c "import json; [json.loads(l) for l in open('file.jsonl')]"`

### Telemetry Provenance

The Gen300 expanding-window bug proved that results are meaningless without knowing which method produced them. Gen500 established this baseline schema — future generations should include at least these provenance fields, and add more as methodology evolves:

```json
{
  "generation": 500,
  "config_id": "ofi_gt_p75__price_impact_lt_p10",
  "environment": {
    "symbol": "SOLUSDT",
    "threshold_dbps": 500,
    "template_sha256": "a1b2c3...",
    "git_commit": "deadbeef",
    "quantile_method": "rolling_1000_signal"
  },
  "results": { "kelly_fraction": 0.036, "filtered_signals": 247 },
  "skipped": false,
  "error": false
}
```

**Compression**: Brotli `--quality=11` for files >1MB (14-21x ratio). Use `brotli --quality=11 -c file > file.br` — never `brotli -11` (silently corrupt).

---

## Emerging Opportunities (Untested)

These are documented for future generations, not prescriptions:

1. **47-feature sweep**: 38 lookback/intra features never tested in any brute-force generation
2. **Regime conditioning**: Use `lookback_hurst < 0.5` as hard gate (mean-reverting regime only)
3. **Intra-bar structure**: `intra_bull_epoch_density` / `intra_bear_epoch_density` differentiate exhaustion vs panic
4. **Dynamic barriers**: Condition TP/SL on volatility (`lookback_garman_klass_vol`)
5. **Anti-pattern portfolio**: 92 confirmed anti-patterns could be traded in reverse
6. **Feature interactions**: XOR, ratio, nonlinear combinations (not just AND filters)
7. **Walk-forward optimization**: Full WFO on SQL-discovered patterns

---

## References

- [Detailed patterns and themes](./references/patterns-and-themes.md)
- [clickhouse-antipatterns skill](../clickhouse-antipatterns/SKILL.md) (SQL correctness)
- [sql/CLAUDE.md](/sql/CLAUDE.md) (generation evolution table)
- [findings/CLAUDE.md](/findings/CLAUDE.md) (research findings index)
- [src/rangebar_patterns/eval/CLAUDE.md](/src/rangebar_patterns/eval/CLAUDE.md) (5-metric stack)
