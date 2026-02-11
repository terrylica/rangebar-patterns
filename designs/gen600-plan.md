# Gen600: Hybrid Feature Sweep — 22 Patterns (11 LONG + 11 SHORT) x 39 Features

## Context

All prior sweep generations (Gen300-Gen520) tested only 8 bar-level features. The ClickHouse `range_bars` table has 47 features total — 16 lookback and 22 intra-bar features are completely untested. The champion pattern (2 consecutive DOWN bars) is DEAD as standalone strategy, but 56 dual-validated configs suggest real microstructure structure exists. Gen600 pairs each bar-level feature with each lookback/intra feature in hybrid pairs, tests 11 distinct base patterns (including wick patterns, high-coverage variants, and a SHORT signal), and adds a new computed `opposite_wick_pct` feature.

**User decisions**:
- Feature space: Hybrid (bar-level x lookback+intra) — 342 pairs (9 bar-level incl. opposite_wick_pct x 38 lookback/intra)
- Base patterns: 22 total (11 LONG + 11 SHORT mirrors — every LONG has a SHORT counterpart)
- Barriers: 3 profiles per config via inline CROSS JOIN (inverted, symmetric, momentum)
- Assets: BTC, ETH, SOL, BNB, XRP (5 assets — SHIB dropped: dead features; DOGE dropped: @500 truncated 2021, poor lookback coverage)
- Thresholds: @750, @1000 only (2 thresholds, 10 combos — @500 dropped due to rangebar-py pipeline gaps: SOL/XRP 2021 = 100% zero lookback, BTC 2024-25 = 12-15% zero)
- Date cutoff: `timestamp_ms <= 1738713600000` (2026-02-05 00:00:00 UTC epoch ms) — ClickHouse can't multiply DateTime * Int
- Warmup: `rn > 1000` rolling quantile warmup (100% lookback coverage at @750/@1000, no gaps)
- Quantile grid: Phase 1 = p50 median split only (gt/lt per feature = 4 combos per pair)
- Compute: Go big overnight (~301K SQL files, ~21 hours at 8 parallel pueue slots — may need 2 nights)

---

## Config Space

| Dimension | Count |
|---|---|
| Feature pairs | 342 (9 bar-level incl. opposite_wick_pct x 38 lookback/intra) |
| Filter combos per pair | 4 (p50 gt/lt for each feature) |
| Base patterns | 22 (11 LONG + 11 SHORT) |
| Barriers per query | 3 (inline CROSS JOIN, 3 output rows) |
| SQL files per asset/threshold | 30,096 (342 x 4 x 22) |
| Asset/threshold combos | 10 (5 x 2) |
| **Total SQL files** | **300,960** |
| **Total result rows** | **902,880** (300,960 x 3 barriers) |
| **Estimated runtime** | **~21 hours** (8 parallel pueue slots, P50=2s/query) |

---

## 22 Base Patterns (11 LONG + 11 SHORT mirrors)

Every LONG pattern has a SHORT mirror testing the opposite directional thesis. This ensures complete LONG/SHORT symmetry — if a microstructure effect exists, it should be detectable in both directions.

### 11 LONG Patterns (Mean-Reversion After Selling)

| # | Name | Short ID | Signal → Direction | Gate | Coverage (SOL @750) |
|---|---|---|---|---|---|
| L1 | 2-DOWN (champion) | `2down` | dir_2=0, dir_1=0 → LONG | ti>p95, kyle>0 | 1.16% (1,797) |
| L2 | 3-DOWN | `3down` | dir_3=0, dir_2=0, dir_1=0 → LONG | ti>p95, kyle>0 | 0.82% (1,260) |
| L3 | DOWN-UP-DOWN | `dud` | dir_3=0, dir_2=1, dir_1=0 → LONG | ti>p95, kyle>0 | 0.29% (442) |
| L4 | UP-DOWN-DOWN | `udd` | dir_3=1, dir_2=0, dir_1=0 → LONG | ti>p95, kyle>0 | 0.35% (537) |
| L5 | 2-DOWN no gate | `2down_ng` | dir_2=0, dir_1=0 → LONG | None | 23.68% (36,575) |
| L6 | HIGH-VOL DOWN | `hvd` | dir_1=0 → LONG | vpt>p90 | 5.15% (7,959) |
| L7 | VWAP dislocation | `vwap_l` | dir_1=0 → LONG | vcd<p10 | ~10.7% (~16,473) |
| L8 | Wickless 2-DOWN | `wl2d` | dir_2=0, dir_1=0 + both wickless → LONG | wick<0.001 | 0.46% (710) |
| L9 | Single wickless DOWN | `wl1d` | dir_1=0 + wickless → LONG | wick<0.001 | 4.91% (7,580) |
| L10 | DOWN + intra exhaustion | `exh_l` | dir_1=0 → LONG | mdd>p75 | ~12% (gated) |
| L11 | DOWN + intra exhaustion (no gate) | `exh_l_ng` | dir_1=0 → LONG | None (mdd eligible) | ~49% (76,350 eligible) |

### 11 SHORT Mirrors (Mean-Reversion After Buying)

| # | Name | Short ID | Signal → Direction | Gate | Coverage (SOL @750) | Barrier Math |
|---|---|---|---|---|---|---|
| S1 | 2-UP SHORT | `2up_s` | dir_2=1, dir_1=1 → SHORT | ti>p95, kyle<0 | 0.19% (288) | Flipped |
| S2 | 3-UP SHORT | `3up_s` | dir_3=1, dir_2=1, dir_1=1 → SHORT | ti>p95, kyle<0 | 0.10% (157) | Flipped |
| S3 | UP-DOWN-UP SHORT | `udu_s` | dir_3=1, dir_2=0, dir_1=1 → SHORT | ti>p95, kyle<0 | 0.40% (622) | Flipped |
| S4 | DOWN-UP-UP SHORT | `duu_s` | dir_3=0, dir_2=1, dir_1=1 → SHORT | ti>p95, kyle<0 | 0.08% (131) | Flipped |
| S5 | 2-UP no gate SHORT | `2up_ng_s` | dir_2=1, dir_1=1 → SHORT | None | 24.82% (38,341) | Flipped |
| S6 | HIGH-VOL UP SHORT | `hvu_s` | dir_1=1 → SHORT | vpt>p90 | 5.29% (8,173) | Flipped |
| S7 | VWAP dislocation SHORT | `vwap_s` | dir_1=1 → SHORT | vcd>p90 | 9.85% (15,213) | Flipped |
| S8 | Wickless 2-UP SHORT | `wl2u_s` | dir_2=1, dir_1=1 + both wickless → SHORT | wick<0.001 | 0.57% (875) | Flipped |
| S9 | Single wickless UP SHORT | `wl1u_s` | dir_1=1 + wickless → SHORT | wick<0.001 | 5.43% (8,394) | Flipped |
| S10 | UP + intra runup SHORT | `exh_s` | dir_1=1 → SHORT | mru>p75 | ~12% (gated) | Flipped |
| S11 | UP + intra runup (no gate) SHORT | `exh_s_ng` | dir_1=1 → SHORT | None (mru eligible) | ~50% (78,117 eligible) | Flipped |

### SHORT Barrier Math (all S1-S11)

All SHORT templates flip the barrier formulas:
- `tp_price = entry_price * (1.0 - tp_mult * threshold_pct)` (TP below entry)
- `sl_price = entry_price * (1.0 + sl_mult * threshold_pct)` (SL above entry)
- Barrier scan: TP when `fwd_lows <= tp_price`, SL when `fwd_highs >= sl_price`
- SL execution: `greatest(fwd_opens[raw_sl_bar], sl_price)` (gap-up)
- Return: `(entry_price - exit_price) / entry_price`

### Signal Coverage Summary

| Tier | Patterns | Coverage Range | Signals (SOL @750) |
|---|---|---|---|
| **Sparse** | L1-L4, S1-S4, L8, S8 | 0.08-1.16% | 131-1,797 |
| **Medium** | L6, L7, L9, S6, S7, S9 | 4.9-10.7% | 7,580-16,473 |
| **Dense** | L5, L10-L11, S5, S10-S11 | 12-25% | 19K-78K |

### Wick Structural Discovery (verified cross-asset)

- Range bars have a **structural wick asymmetry**: the close-side wick is zero **99.5%** of the time (construction artifact)
- Only the **opposite wick** (open-side) carries information: zero ~10% of the time, median ~23% of bar range
- **Direction-aware formula** (CRITICAL — a non-direction-aware formula produces zero signals for one side):
  - DOWN bars: `opposite_wick_pct = (high - open) / nullIf(high - low, 0)` — upper wick
  - UP bars: `opposite_wick_pct = (open - low) / nullIf(high - low, 0)` — lower wick
- This is **universal across all 15 symbols** (range bar construction artifact, not asset-specific)
- Wickless bars (~10%): bar opened at its extreme and moved straight to the other extreme = strong momentum

### Wick Formula Bug Discovery (2026-02-11)

**Initial diagnostic query bug**: Used `(high - open) / (high - low)` for ALL bars regardless of direction. This computes the UPPER wick for all bars. For UP bars, the opposite wick is the LOWER wick `(open - low) / (high - low)`. Using the wrong formula produced **zero** wickless UP signals, falsely suggesting wickless UP bars don't exist. With the correct direction-aware formula: wickless 1-UP = 8,394 (5.43%), wickless 2-UP = 875 (0.57%) — fully symmetric with DOWN.

---

## 3 Barrier Profiles (CROSS JOIN)

| Profile | TP mult | SL mult | Max Bars | Thesis |
|---|---|---|---|---|
| `inverted` | 0.25x | 0.50x | 100 | Mean-reversion (Gen510 optimum) |
| `symmetric` | 0.50x | 0.50x | 50 | Neutral baseline |
| `momentum` | 0.75x | 0.25x | 50 | Trend continuation |

Embedded via UNION ALL subquery in `barrier_params` CTE (3 rows per signal):

```sql
CROSS JOIN (
    SELECT 'inverted' AS barrier_profile, 0.25 AS tp_mult, 0.50 AS sl_mult, toUInt32(100) AS max_bars
    UNION ALL
    SELECT 'symmetric', 0.50, 0.50, toUInt32(50)
    UNION ALL
    SELECT 'momentum', 0.75, 0.25, toUInt32(50)
) bp
```

---

## File Inventory

### SQL Templates (22 files — NEW, 11 LONG + 11 SHORT)

All forked from `sql/gen500_2feature_template.sql`. SHORT templates fork from their LONG counterpart with barrier math flipped.

**Template naming**: `sql/gen600_{short_id}_template.sql`

**11 LONG templates**:

| File | Key Changes |
|---|---|
| `gen600_2down_template.sql` | Canonical LONG template: barrier CROSS JOIN, 101 fwd bars, base_pattern output |
| `gen600_3down_template.sql` | + `dir_3` lag via `lagInFrame(direction, 3)` |
| `gen600_dud_template.sql` | dir_3=0, dir_2=1, dir_1=0 (failed bounce) |
| `gen600_udd_template.sql` | dir_3=1, dir_2=0, dir_1=0 (momentum reversal) |
| `gen600_2down_ng_template.sql` | Remove ti_1/kyle_1 from WHERE |
| `gen600_hvd_template.sql` | + `volume_per_trade`, + `vpt_p90_rolling` |
| `gen600_vwap_l_template.sql` | + `vwap_close_deviation` **p10** rolling (extreme negative) |
| `gen600_wl2d_template.sql` | + `opposite_wick_pct` (direction-aware), wick_1/wick_2 lags, WHERE both < 0.001 |
| `gen600_wl1d_template.sql` | + `opposite_wick_pct`, WHERE wick_1 < 0.001 |
| `gen600_exh_l_template.sql` | + `intra_max_drawdown` rolling p75 gate |
| `gen600_exh_l_ng_template.sql` | dir_1=0, intra_mdd eligible (no gate — features replace it) |

**11 SHORT templates** (each mirrors a LONG template):

| File | Mirrors | Additional Changes |
|---|---|---|
| `gen600_2up_s_template.sql` | L1 (2down) | dir flipped to 1, kyle<0, barrier math flipped |
| `gen600_3up_s_template.sql` | L2 (3down) | dir_3=1, dir_2=1, dir_1=1, kyle<0 |
| `gen600_udu_s_template.sql` | L3 (dud) | dir_3=1, dir_2=0, dir_1=1 (failed pullback) |
| `gen600_duu_s_template.sql` | L4 (udd) | dir_3=0, dir_2=1, dir_1=1 |
| `gen600_2up_ng_s_template.sql` | L5 (2down_ng) | dir flipped, no gate, barrier flipped |
| `gen600_hvu_s_template.sql` | L6 (hvd) | dir_1=1, vpt>p90, barrier flipped |
| `gen600_vwap_s_template.sql` | L7 (vwap_l) | dir_1=1, vcd>p90 (extreme POSITIVE dislocation), barrier flipped |
| `gen600_wl2u_s_template.sql` | L8 (wl2d) | dir flipped, opposite_wick for UP bars, barrier flipped |
| `gen600_wl1u_s_template.sql` | L9 (wl1d) | dir_1=1, wick for UP bar, barrier flipped |
| `gen600_exh_s_template.sql` | L10 (exh_l) | dir_1=1, intra_max_runup>p75, barrier flipped |
| `gen600_exh_s_ng_template.sql` | L11 (exh_l_ng) | dir_1=1, mru eligible, barrier flipped |

**New computed feature**: `opposite_wick_pct` is computed inline in `base_bars` CTE (not a table column):
```sql
-- In base_bars CTE:
CASE
    WHEN direction = 0 THEN (high - open) / nullIf(high - low, 0)   -- DOWN: upper wick as fraction of range
    ELSE (open - low) / nullIf(high - low, 0)                        -- UP: lower wick as fraction of range
END AS opposite_wick_pct
```
This becomes the 9th bar-level feature available for hybrid pairing (total: 9 bar-level x 38 lookback/intra = 342 pairs).

### Scripts (7 files — NEW)

| File | Purpose | Reference |
|---|---|---|
| `scripts/gen600/generate.sh` | Generate 301K SQL files from 22 templates | `scripts/gen500/generate.sh` |
| `scripts/gen600/poc.sh` | Fail-fast 10-config validation | `scripts/gen400/poc.sh` |
| `scripts/gen600/submit.sh` | Submit one asset/threshold/pattern | `scripts/gen510/submit.sh` (3-row parsing) |
| `scripts/gen600/submit_all.sh` | Orchestrate all 220 units (22 patterns x 10 combos) | `scripts/gen500/submit_all.sh` |
| `scripts/gen600/status.sh` | Progress across 220 units | `scripts/gen500/status.sh` |
| `scripts/gen600/collect.sh` | scp + sanitize + validate | `scripts/gen500/collect.sh` |
| `scripts/gen600/report.sh` | Cross-asset/threshold/barrier/pattern analysis | New (most complex) |

### Alignment Tests (1 file — NEW)

| File | Purpose | Reference |
|---|---|---|
| `tests/test_gen600_barrier_alignment.py` | SQL vs backtesting.py exit price match across 3 barrier profiles | `tests/test_gen300_barrier_alignment.py` |

### Mise + Config (2 files — EDIT)

| File | Action |
|---|---|
| `.mise/tasks/gen600.toml` | NEW — tasks: generate, poc, submit, submit-all, status, collect, report |
| `.mise.toml` | EDIT — add `".mise/tasks/gen600.toml"` to `[task_config] includes` |

---

## SQL Template Design (CTE Chain)

Using 2-DOWN as canonical reference. Other patterns modify `signal_detection` → `champion_signals` only.

```
base_bars                          SELECT from range_bars + bar-level + lookback/intra feature cols
                                   + opposite_wick_pct (computed: CASE WHEN dir=0 THEN (high-open)/(high-low) ELSE (open-low)/(high-low) END)
                                   WHERE timestamp_ms <= 1738713600000  (Feb 5 2026 cutoff)
  → running_stats                  ti_p95_rolling (1000-bar window, ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING)
    → signal_detection             lagInFrame for directions, ti, kyle, features, entry_price
      → champion_signals           Base pattern WHERE clause (varies per template)
        → feature1_with_quantile   Rolling 1000-SIGNAL quantile on bar-level feature (within signal set)
          → feature2_with_quantile Rolling 1000-SIGNAL quantile on lookback/intra feature
            → signals              Feature filter applied (direction comparisons)
              → forward_arrays     groupArray of fwd highs/lows/opens/closes (101 bars for MB=100)
                → barrier_params   CROSS JOIN with 3 barrier sets (UNION ALL)
                  → barrier_scan   arrayFirstIndex for TP/SL detection per barrier profile
                    → trade_outcomes  exit_type, exit_bar, exit_price per barrier
                      → SELECT     GROUP BY barrier_profile → 3 output rows per query
```

**Nullable intra features**: Handled by existing `IS NOT NULL` guards in `champion_signals`. `quantileExactExclusive` skips NULLs natively. No special handling needed.

**Lookback zero guard**: No longer needed — @500 threshold dropped. All @750/@1000 combos have 100% lookback coverage. Template retains `AND lookback_trade_count > 0` as a defensive guard (zero cost if no zeros exist) but it should never filter any bars.

**SHORT template (2up_short)**: Barrier formulas flip:
- `tp_price = entry_price * (1.0 - tp_mult * threshold_pct)` (below)
- `sl_price = entry_price * (1.0 + sl_mult * threshold_pct)` (above)
- Barrier scan: TP when `fwd_lows <= tp_price`, SL when `fwd_highs >= sl_price`
- SL execution: `greatest(fwd_opens[raw_sl_bar], sl_price)` (gap-up)
- Return: `(entry_price - exit_price) / entry_price`

---

## NDJSON Telemetry Schema (Extended — Full Forensic)

Every NDJSON line must support post-hoc forensic analysis without re-running any query. Three barrier rows per query are written atomically in a single `flock` call.

```json
{
    "generation": 600,
    "config_id": "2down__ofi_gt_p50__lookback_hurst_lt_p50__inverted",
    "feature_config": "2down__ofi_gt_p50__lookback_hurst_lt_p50",
    "base_pattern": "2down",
    "barrier_profile": "inverted",
    "feature_group": "hybrid_bar_x_lookback",

    "features": {
        "feature1_col": "ofi",
        "feature1_direction": "gt",
        "feature1_quantile": 0.50,
        "feature1_group": "bar_level",
        "feature2_col": "lookback_hurst",
        "feature2_direction": "lt",
        "feature2_quantile": 0.50,
        "feature2_group": "lookback"
    },

    "environment": {
        "symbol": "BTCUSDT",
        "threshold_dbps": 750,
        "template_sha256": "a1b2c3...",
        "git_commit": "deadbeef",
        "quantile_method": "rolling_1000_signal",
        "date_cutoff_ms": 1738713600000,
        "warmup_bars": 1000
    },

    "barrier": {
        "tp_mult": 0.25,
        "sl_mult": 0.50,
        "max_bars": 100
    },

    "signal_funnel": {
        "total_bars": 154467,
        "base_pattern_signals": 1797,
        "after_feature_filter": 847,
        "signal_coverage": 0.00548,
        "feature2_null_rate": 0.0
    },

    "results": {
        "filtered_signals": 847,
        "kelly_fraction": 0.024,
        "profit_factor": 1.17,
        "hit_rate": 0.70,
        "avg_win": 0.0018,
        "avg_loss": -0.0031,
        "total_return": 0.312,
        "tp_count": 593,
        "sl_count": 212,
        "time_count": 42,
        "incomplete_count": 0,
        "median_exit_bar": 12,
        "signal_min_ts_ms": 1516057200000,
        "signal_max_ts_ms": 1738627200000
    },

    "timing": {
        "query_duration_ms": 2340,
        "submitted_at": "2026-02-12T03:14:00Z"
    },

    "skipped": false,
    "error": false,
    "error_message": null
}
```

### Telemetry Field Groups

| Group | Fields | Forensic Purpose |
|---|---|---|
| **Identity** | config_id, feature_config, base_pattern, barrier_profile, feature_group | Unique identification + cross-dimensional joins |
| **Features** | feature1_col/direction/quantile/group, feature2_* | Full feature specification — reconstruct the exact SQL without re-parsing config_id |
| **Environment** | symbol, threshold, template_sha256, git_commit, quantile_method, date_cutoff, warmup | Exact reproducibility — any result can be replicated from these fields |
| **Barrier** | tp_mult, sl_mult, max_bars | Barrier configuration per profile |
| **Signal Funnel** | total_bars → base_pattern_signals → after_feature_filter, coverage, null_rate | **NEW**: How many signals survived each filter stage. Diagnose: is the pattern too rare? Is the feature filter too aggressive? Is the feature mostly NULL? |
| **Results** | kelly, PF, HR, avg_win/loss, total_return, exit type counts, median_exit_bar, signal timestamps | Full outcome distribution — TP/SL/TIME breakdown, temporal span of signals |
| **Timing** | query_duration_ms, submitted_at | Performance forensics — identify slow queries, estimate completion |
| **Status** | skipped, error, error_message | Error tracking — skipped (< 100 signals), error (query failure with truncated message) |

### Key Improvements vs Gen500

| Field | Gen500 | Gen600 | Why |
|---|---|---|---|
| `features.*` | Encoded in config_id only | Explicit structured fields | Parse-free filtering/grouping in analysis |
| `signal_funnel.*` | Only `filtered_signals` | Full funnel: total → base → filtered | Diagnose filter aggressiveness per stage |
| `feature2_null_rate` | Not tracked | Tracked | Intra features (hurst, permutation_entropy) have 10-35% NULLs |
| `results.tp/sl/time_count` | Not tracked | Tracked | Outcome distribution — a config with 95% TP exits is very different from one with 50% |
| `results.median_exit_bar` | Not tracked | Tracked | How quickly trades resolve — barrier tuning diagnostic |
| `results.signal_min/max_ts_ms` | Not tracked | Tracked | Temporal span — detect if all signals cluster in one regime |
| `timing.*` | Not tracked | Tracked | Query performance forensics |
| `environment.date_cutoff_ms` | Implicit | Explicit | Reproducibility — exact data window |

### Wrapper Implementation

The submit wrapper script:
1. Runs the SQL query, captures TSV output (3 rows — one per barrier profile)
2. Parses each row into the JSON schema above
3. Adds provenance fields (template_sha256, git_commit, timing)
4. If query returns 0 rows: writes `{"skipped": true, ...}` with signal_funnel showing where the funnel emptied
5. If query errors: writes `{"error": true, "error_message": "<first 500 chars>", ...}`
6. Writes all 3 (or 1 if skipped/error) lines atomically: `flock "${LOG_FILE}.lock" bash -c "echo '${LINE1}\n${LINE2}\n${LINE3}' >> ${LOG_FILE}"`

---

## Task Graph (Authoritative Execution Order)

26 tasks with dependency chains. Execute strictly one at a time, in topological order. GATE tasks are validation checkpoints — must pass before downstream tasks proceed.

### Legend
- `→` = blocked by (must complete first)
- `GATE` = validation checkpoint with pass/fail criteria
- `cp` = copy from existing file before modifying

### Phase 0: Setup (Tasks #54-55)

```
#54 Archive plan to designs/gen600-plan.md
     cp from: ~/.claude/plans/prancy-tumbling-candy.md → designs/gen600-plan.md

#55 Create GitHub Issue #14: Gen600 parent issue  → #54
     gh issue create with full config space summary
```

### Phase 1: SQL Templates (Tasks #56-61) — SR&ED Commit 1

```
#56 Create canonical LONG template: gen600_2down_template.sql
     cp from: sql/gen500_2feature_template.sql → sql/gen600_2down_template.sql
     Modify: barrier CROSS JOIN, 101 fwd bars, signal_funnel output, date cutoff

#57 GATE: Validate 2-DOWN template with atomic POC query  → #56
     Run on BigBlack SOLUSDT @750 with ofi_lt_p50 + lookback_hurst_lt_p50
     Expected: 3 rows, inverted PF≈1.17, symmetric PF≈1.25, momentum PF≈1.04

#58 Create 10 remaining LONG templates (L2-L11)  → #57
     cp from: sql/gen600_2down_template.sql → each LONG template
     Per-pattern WHERE clause modifications only

#59 Create 11 SHORT mirror templates (S1-S11)  → #58
     cp from: each LONG template → its SHORT mirror
     5 systematic changes: dir flip, kyle flip, barrier flip, scan flip, execution flip

#60 GATE: POC validation — 24 configs across 22 patterns  → #59
     Run 24 configs on BigBlack (1 per pattern, LONG+SHORT pairs)
     Verify: 3-row output, barrier math, NULL handling, wick computation

#61 GATE: SHORT barrier reversal via introspect.py  → #60
     Manual bar-by-bar verification of 1 SHORT trade
     tp < entry, sl > entry, gap-up SL, positive return = SHORT profit

#72 SR&ED Commit 1: 22 SQL templates  → #61, #54
     "feat: Gen600 hybrid feature sweep — 22 SQL templates (11 LONG + 11 SHORT)"
```

### Phase 2: Infrastructure Scripts (Tasks #62-71) — SR&ED Commit 2

Two parallel tracks after Phase 1:

**Track A: Generate + POC pipeline**
```
#62 Write scripts/gen600/generate.sh  → #61
     cp from: scripts/gen500/generate.sh
     22 patterns x 342 pairs x 4 combos x 10 combos = 300,960 SQL files

#63 GATE: Verify generate.sh → 300,960 SQL files  → #62
     find /tmp/gen600_sql -name '*.sql' | wc -l = 300,960

#64 Write scripts/gen600/poc.sh  → #63
     cp from: scripts/gen400/poc.sh
     24 generated SQL files → BigBlack → validate 3-row output
```

**Track B: Submit + collect pipeline**
```
#65 Write scripts/gen600/submit.sh + wrapper  → #60
     cp from: scripts/gen510/submit.sh
     Full forensic NDJSON schema, 3-row parsing, flock, dedup

#66 Write scripts/gen600/submit_all.sh  → #65
     cp from: scripts/gen500/submit_all.sh
     220 units (22 patterns x 10 combos), rsync once

#67 Write scripts/gen600/status.sh  → #66
     cp from: scripts/gen500/status.sh
     Progress per 220 units

#68 Write scripts/gen600/collect.sh  → #67
     cp from: scripts/gen500/collect.sh
     scp + sed sanitize + python3 validate + brotli
```

**Merge + config**
```
#70 Create test_gen600_barrier_alignment.py  → #57, #60
     cp from: tests/test_gen300_barrier_alignment.py
     LONG + SHORT barrier alignment, 3 profiles, >95% match

#71 Create .mise/tasks/gen600.toml + update .mise.toml  → #62
     cp from: .mise/tasks/gen500.toml
     7 tasks: generate, poc, submit, submit-all, status, collect, report

#73 SR&ED Commit 2: Infrastructure scripts  → #71, #70, #68, #65
     "feat: Gen600 infrastructure — generate/submit/collect pipeline for 301K configs"
```

### Phase 3: Production Sweep (Tasks #74-76)

```
#74 Launch overnight sweep via pueue on BigBlack  → #73, #63
     mise run gen600:generate → gen600:submit-all
     ~21 hours, 8 parallel pueue slots, 300,960 queries

#75 Collect and validate sweep results  → #74
     mise run gen600:collect
     Expected: ~902,880 result rows, <5% error rate

#69 Write scripts/gen600/report.sh  → #68
     Cross-asset/threshold/barrier/pattern/feature analysis
     No direct copy — novel analysis dimensions

#76 Run cross-dimensional analysis report  → #75
     mise run gen600:report
     Top 20 cross-asset, LONG vs SHORT, feature ranking, Bonferroni
```

### Phase 4: Wrap-up (Tasks #77-79)

```
#77 SR&ED Commit 3: report.sh + results  → #76
     "feat: Gen600 cross-dimensional analysis"

#78 Post Gen600 findings to GitHub Issue #14  → #76
     Comprehensive findings comment, title update

#79 Run code-clone-assistant for DRY compliance  → #73
     Skill(quality-tools:code-clone-assistant) across 22 templates + 7 scripts
```

### Dependency Graph (Visual)

```
#54 ──┬─→ #55
      │
      └─→ #56 → #57(GATE) → #58 → #59 → #60(GATE) → #61(GATE) ──┬─→ #72(COMMIT-1)
                   │                        │                       │
                   │                        ├─→ #65 → #66 → #67 → #68 ──┐
                   │                        │                             │
                   │                        ├─→ #70 ──────────────────────┤
                   │                        │                             │
                   └─→ #62 → #63(GATE) → #64                            │
                        │                                                 │
                        ├─→ #71 ──────────────────────────────────────────┤
                        │                                                 │
                        │                                    #73(COMMIT-2)┤
                        │                                          │      │
                        └──────────────────────────────→ #74 → #75 │    #79
                                                              │    │
                                                    #69 ──→ #76 ──┤
                                                              │    │
                                                           #77(C3) #78
```

### Copy-From Reference (cp Before Create)

| New File | Copy From | Key Modifications |
|---|---|---|
| `designs/gen600-plan.md` | `~/.claude/plans/prancy-tumbling-candy.md` | None (archive copy) |
| `sql/gen600_2down_template.sql` | `sql/gen500_2feature_template.sql` | Barrier CROSS JOIN, 101 fwd bars, signal_funnel, date cutoff |
| `sql/gen600_{L2-L11}_template.sql` | `sql/gen600_2down_template.sql` | Per-pattern WHERE clause |
| `sql/gen600_{S1-S11}_template.sql` | Matching LONG template | 5 systematic SHORT changes |
| `scripts/gen600/generate.sh` | `scripts/gen500/generate.sh` | 22 templates, 342 pairs, 10 combos |
| `scripts/gen600/poc.sh` | `scripts/gen400/poc.sh` | 24 configs, 3-row validation |
| `scripts/gen600/submit.sh` | `scripts/gen510/submit.sh` | Full forensic NDJSON, 3-row parsing |
| `scripts/gen600/submit_all.sh` | `scripts/gen500/submit_all.sh` | 220 units |
| `scripts/gen600/status.sh` | `scripts/gen500/status.sh` | 220 units progress |
| `scripts/gen600/collect.sh` | `scripts/gen500/collect.sh` | 220 files, brotli |
| `scripts/gen600/report.sh` | None (novel) | Cross-dimensional analysis |
| `tests/test_gen600_barrier_alignment.py` | `tests/test_gen300_barrier_alignment.py` | 3 barrier profiles, SHORT test |
| `.mise/tasks/gen600.toml` | `.mise/tasks/gen500.toml` | 7 tasks |

---

## Anti-Pattern Compliance (clickhouse-antipatterns skill)

Audit of ALL 13 anti-patterns against ALL 11 Gen600 templates:

| AP | Rule | Severity | Gen600 Status (all 22 templates) |
|---|---|---|---|
| AP-01 | Signals BEFORE arrays | CRITICAL | **Compliant** — CTE chain: champion_signals → feature filter → `signals` → forward_arrays. Arrays only collected on filtered signals, not all bars. Same for wick templates (wl2d/wl1d) and exhaustion (exh). |
| AP-02 | Pre-compute barrier prices as columns | HIGH | **Compliant** — `barrier_params` CTE pre-computes `tp_price` and `sl_price` as columns before `barrier_scan`. SHORT template uses flipped formula but same pre-computation pattern. |
| AP-03 | arrayFirstIndex > 0 guards | HIGH | **Compliant** — 6-way CASE with explicit `> 0` guards on `raw_tp_bar` and `raw_sl_bar`. Identical logic across all 22 templates. |
| AP-04 | arrayMap + arrayReduce O(n^2) | MEDIUM | **N/A** — Gen600 does not use arrayMap/arrayReduce. Uses arrayFirstIndex for barrier detection. |
| AP-05 | arrayScan does not exist | LOW | **N/A** — Gen600 does not use arrayScan. |
| AP-06 | arrayFold returns only final value | LOW | **N/A** — Gen600 does not use arrayFold. |
| AP-07 | leadInFrame UNBOUNDED FOLLOWING | HIGH | **Compliant** — `entry_price = leadInFrame(open, 1)` uses explicit `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`. Same frame for all lagInFrame/leadInFrame calls across all templates. Wick templates add `lagInFrame(opposite_wick_pct, 1)` and `lagInFrame(opposite_wick_pct, 2)` with same frame. |
| AP-08 | arraySlice before arrayFirstIndex | MEDIUM | **Compliant** — Forward arrays collect 101 bars (for max_bars=100). `barrier_scan` uses `arraySlice(fwd_highs, 1, bp.max_bars)` per barrier profile (50 for symmetric/momentum, 100 for inverted). The slice happens BEFORE arrayFirstIndex in the same CTE. |
| AP-09 | Threshold-relative parameters | HIGH | **Compliant** — All barrier prices use `tp_mult * (__THRESHOLD_DBPS__ / 10000.0)`. Same for SHORT template (flipped direction, same multiplication). |
| AP-10 | NEVER expanding window | CRITICAL | **Compliant** — Every rolling quantile in all 22 templates uses `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`. Specifically: (1) `ti_p95_rolling` in running_stats, (2) `vpt_p90_rolling` in hvd template, (3) `vcd_p10_rolling` in vwap template, (4) `mdd_p75_rolling` in exh template, (5) `feature1_q` in feature1_with_quantile, (6) `feature2_q` in feature2_with_quantile. ZERO expanding windows. |
| AP-11 | TP/SL from entry price | MEDIUM | **Compliant** — `entry_price = leadInFrame(open, 1)` = next bar's open (the actual fill price). All barrier prices derived from entry_price. |
| AP-12 | SL wins same-bar ties | MEDIUM | **Compliant** — `WHEN raw_sl_bar > 0 AND raw_tp_bar > 0 AND raw_sl_bar <= raw_tp_bar THEN 'SL'`. Note: `<=` ensures SL wins when TP and SL fire on the same bar. |
| AP-13 | Gap execution price | MEDIUM | **Compliant** — LONG templates (1-7, 9-11): `least(fwd_opens[raw_sl_bar], sl_price)` for gap-down SL. SHORT template (8): `greatest(fwd_opens[raw_sl_bar], sl_price)` for gap-up SL. TP always fills at tp_price (limit order). |

**New pattern-specific compliance notes**:

| Template | Pattern-Specific Concerns | Status |
|---|---|---|
| **wl2d** (wickless 2-DOWN) | `opposite_wick_pct` computed in base_bars using `nullIf(high - low, 0)` to avoid division by zero. Lagged via `lagInFrame(..., 1)` and `lagInFrame(..., 2)` with UNBOUNDED frame. Wick = 0 check uses `< 0.001` tolerance (not exact 0.0) for floating point safety. | **Compliant** |
| **wl1d** (single wickless DOWN) | Same as wl2d but only 1 lag. No ti/kyle gate — the wick condition IS the gate. | **Compliant** |
| **exh** (exhaustion) | `intra_max_drawdown` is Nullable. `running_stats` computes `mdd_p75_rolling` using `quantileExact(0.75)(intra_max_drawdown)` which skips NULLs natively. `champion_signals` WHERE includes `AND intra_mdd_1 IS NOT NULL` guard. | **Compliant** |
| **2up_short** | Barrier formulas flipped: `tp_price = entry * (1 - tp_mult * threshold)`, `sl_price = entry * (1 + sl_mult * threshold)`. arrayFirstIndex: TP checks `fwd_lows <= tp_price`, SL checks `fwd_highs >= sl_price`. Gap-up SL: `greatest(open, sl_price)`. Return: `(entry - exit) / entry`. | **Compliant** |

## Sweep Methodology Compliance

Audit against sweep-methodology skill checklist (all 22 templates):

| Checklist Item | Gen600 Status |
|---|---|
| Quantile window: Rolling 1000-bar/signal | **All quantile stages across all 22 templates**: (1) `ti_p95` in running_stats, (2) `vpt_p90` in hvd, (3) `vcd_p10` in vwap, (4) `mdd_p75` in exh, (5-6) feature1_q/feature2_q in feature CTEs — ALL use `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`. **Zero expanding windows in any template.** |
| Feature quantiles within signal set | Compliant — feature quantiles computed in CTEs AFTER champion_signals. This applies identically to all 22 templates including wick patterns (wl2d/wl1d) and exhaustion (exh). The champion_signals WHERE clause varies per pattern, but the quantile-within-signal-set principle is invariant. |
| Feature Quantile Distribution Trap | **Compliant + lesson applied** — Pattern 7 (VWAP) was caught by this exact trap: `vwap_close_deviation > p90` on DOWN bars = 0 signals because DOWN bars have structurally negative vcd. Fixed to `< p10`. All other patterns verified: their gate features are not structurally correlated with bar direction. |
| Warmup guard `rn > 1000` | Compliant — in champion_signals WHERE clause for all 22 templates |
| Barriers: Gen510 optimum as baseline | Compliant — `inverted` profile (0.25x/0.50x/100) is one of 3 profiles tested per query |
| Min signal count n >= 100 | Wrapper marks `skipped: true` for configs with < 100 signals. Pattern 9 (wl2d, ~1%) and Pattern 8 (SHORT, 0.19%) are sparse but not pre-filtered — they get feature-filtered first and the wrapper checks the resulting count. |
| Cross-asset from the start | Compliant — 5 assets (BTC/ETH/SOL/BNB/XRP) in initial sweep. SHIB dropped: dead features. DOGE dropped: truncated data. Wick structural analysis confirmed universal across all 15 symbols (range bar construction artifact, not asset-specific). |
| Cross-threshold from the start | Compliant — 2 thresholds (@750/@1000) tested for every config. @500 dropped (pipeline gaps). |
| 5-metric evaluation stack | report.sh computes Kelly; full eval pipeline (`src/rangebar_patterns/eval/`) applicable post-collect |
| Telemetry: NDJSON + brotli | Compliant — NDJSON with provenance, `signal_coverage` field, `barrier` nested object; brotli for >1MB after collect |
| Infrastructure: Parallel SSH + dedup | Compliant — submit_all.sh orchestrates 220 units (22 patterns x 10 combos). Config-ID dedup handles SSH drops. 8 parallel pueue slots. |

## Lookahead Bias Audit (CRITICAL)

### Three quantile stages — all rolling, none expanding

1. **`running_stats` CTE** — `ti_p95_rolling`: Rolling 1000-BAR window over ALL bars, computed BEFORE signal detection. Uses `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`. The `1 PRECEDING` excludes the current bar = no lookahead.

2. **`feature1_with_quantile` CTE** — feature1 quantile: Rolling 1000-SIGNAL window WITHIN champion_signals. Uses `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`. The `1 PRECEDING` means the current signal's feature value is compared against a threshold computed from the 999 PRIOR signals only = no lookahead.

3. **`feature2_with_quantile` CTE** — feature2 quantile: Same rolling 1000-SIGNAL window. Same `1 PRECEDING` exclusion. No lookahead.

### Lookback column lookahead risk — VERIFIED SAFE (2026-02-11)

**`lookback_*` columns are pre-computed in the ClickHouse table.** Diagnostic queries confirmed:

1. **Lookback EXCLUDES the current bar** — When bar N has extreme OFI (e.g., +1.0), the shift appears in `lookback_ofi` at bar N+1 (not bar N). The shift magnitude matches `bar_ofi / lookback_trade_count`, confirming the current bar's data enters the NEXT bar's lookback only.

2. **Lookback is NOT an expanding window** — `lookback_trade_count` does not grow monotonically with bar position (e.g., rn=5000→19K, rn=10000→3.8K, rn=300000→22K). It uses a variable-size rolling/time-based window.

3. **Lookback window is time-based, not bar-count-based** — `lookback_trade_count` ranges from 0 to 12M depending on asset/threshold/activity. The window likely covers a fixed calendar period, with trade counts varying by market conditions.

4. **Caveat (historical) — @500 had lookback_trade_count = 0 gaps**: SOLUSDT @500 had 34% zeros, BTCUSDT @500 had 1.5% zeros (rangebar-py pipeline gaps, not data quality). **Resolved by dropping @500** — @750/@1000 have 100% coverage.

**Verdict**: Lookback columns are safe for Gen600. No lookahead contamination. The `lagInFrame(__FEATURE_COL_2__, 1)` adds a second layer of safety — we use the lookback value from bar N-1, which is computed from data strictly before bar N-1.

### Intra column lookahead risk (NEW for Gen600)

**`intra_*` columns are WITHIN-BAR statistics.** Since the signal fires at bar N's close and entry is at bar N+1's open, using `intra_*` values from bar N is NOT lookahead — the bar has already closed when the signal fires. However, we use `lagInFrame(__FEATURE_COL_2__, 1)` which takes the value from bar N-1 (one bar prior to the signal bar). This is doubly safe — the intra-bar features are from a fully completed prior bar.

### Entry price computation

`entry_price = leadInFrame(open, 1)` = next bar's open price. This is the actual fill price. The signal fires at bar N's close; the trade enters at bar N+1's open. No lookahead.

### Feature filter timing

Both feature columns are accessed via `lagInFrame(__FEATURE_COL__, 1)` = value from bar N-1 (one bar BEFORE the signal bar). The quantile threshold is computed over the 999 signals before the current one. Both the value being compared AND the threshold it's compared against are strictly from the past. No lookahead.

### Summary

| Data Point | Source Bar | Signal Bar | Temporal Relation | Verdict |
|---|---|---|---|---|
| Direction (dir_1, dir_2) | N-1, N-2 | N | Past | Safe |
| trade_intensity (ti_1) | N-1 | N | Past | Safe |
| kyle_lambda_proxy (kyle_1) | N-1 | N | Past | Safe |
| ti_p95_rolling | N-1000..N-1 | N | Past (rolling) | Safe |
| feature1_lag1 (bar-level) | N-1 | N | Past | Safe |
| feature2_lag1 (lookback/intra) | N-1 | N | Past | **VERIFIED safe** (lookback excludes current bar, time-based rolling window) |
| feature1_q (quantile threshold) | Prior 999 signals | Current signal | Past (rolling) | Safe |
| feature2_q (quantile threshold) | Prior 999 signals | Current signal | Past (rolling) | Safe |
| entry_price | N+1 | N | Future (correct — this IS the entry) | Safe |
| opposite_wick_pct (computed) | N-1 | N | Past (lagInFrame, uses open/high/low from completed bar) | Safe |
| intra_max_drawdown (for exh) | N-1 | N | Past (within-bar stat from completed bar, lagged) | Safe |

**All data points verified** — no outstanding lookback/lookahead risks. The new wick feature (`opposite_wick_pct`) is computed from `open`, `high`, `low` of a completed bar and accessed via `lagInFrame(..., 1)` — strictly past data.

## Data Verification (BigBlack, 2026-02-11)

### Asset/Threshold Availability (5 assets x 2 thresholds = 10 combos)

| Asset | @750 Bars | @1000 Bars | Date Range | Span | Lookback Coverage |
|---|---|---|---|---|---|
| BTCUSDT | 86K | 47K | 2018-01-15 → 2026-02-05 | 8.1y | 100% (no gaps at @750/@1000) |
| ETHUSDT | 129K | 72K | 2018-01-15 → 2026-02-05 | 8.1y | 100% |
| SOLUSDT | 168K | 94K | 2020-08-10 → 2026-02-05 | 5.5y | 100% (@750/@1000 fully populated, 2021 gap only at @500) |
| BNBUSDT | 143K | 79K | 2018-01-15 → 2026-02-05 | 8.1y | 100% |
| XRPUSDT | 185K | 103K | 2018-05-04 → 2026-02-05 | 7.8y | 100% (@750/@1000 fully populated, 2021 gap only at @500) |

**Dropped assets**: SHIBUSDT (dead features), DOGEUSDT (@500 truncated, poor lookback)
**Dropped threshold**: @500 — rangebar-py pipeline gaps (SOL/XRP 2021 = 100% zero lookback, BTC 2024-25 = 12-15% zero). @750/@1000 have 100% lookback coverage for all 5 assets.

### Date Cutoff and Warmup Strategy

**Date cutoff**: `WHERE timestamp_ms <= 1738713600000` in `base_bars` CTE (2026-02-05 00:00:00 UTC as epoch milliseconds). ClickHouse cannot multiply `toDateTime() * 1000` — must use pre-computed constant. Excludes ~2 days of recent data (negligible: <0.2% of bars).

**Warmup guards** (two layers):
1. **`rn > 1000`** — Existing warmup for rolling 1000-bar quantile computation. First 1000 bars per asset/threshold excluded from signal detection. Ensures rolling p95 threshold is stable.
2. **Rolling 1000-SIGNAL quantile warmup** — The first 1000 signals within `champion_signals` have no reliable feature quantile threshold. The signal-level quantile is computed via `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING` which naturally returns NULL for the first signal, and the feature filter `WHERE feature1_lag1 > feature1_q` will exclude NULLs.

**Why these are sufficient**: By dropping @500, all remaining combos (@750/@1000 x 5 assets) have 100% lookback feature coverage with 5.5-8.1 years of multi-year data. No pipeline gaps, no year-long outages. The `rn > 1000` bar warmup provides a clean start for the rolling quantile computation.

### Signal Counts by Base Pattern (Verified)

Verified counts (SOLUSDT @750, 154,467 bars after warmup):

| Pattern | Gated Signals | Coverage | Gate |
|---|---|---|---|
| 2-DOWN | 1,797 | 1.16% | ti>p95, kyle>0 |
| 3-DOWN | 1,260 | 0.82% | ti>p95, kyle>0 |
| DUD | 442 | 0.29% | ti>p95, kyle>0 |
| UDD | 537 | 0.35% | ti>p95, kyle>0 |
| 2-DOWN no gate | 36,575 | 23.68% | None |
| HVD | 7,959 | 5.15% | vpt>p90 |
| VWAP | ~16,473 | ~10.7% | vcd<p10 |
| 2-UP SHORT | 288 | 0.19% | ti>p95, kyle<0 |

**Gate pass rate is stable at 5.0-6.8%** across all 10 asset/threshold combos. Smallest gated pool: BTC @1000 = 670 signals (thin but usable).

### Signal Coverage by Base Pattern (Verified, SOLUSDT @750)

Coverage = gated signals / total bars after warmup. Measures what fraction of bars trigger each pattern.

| # | Pattern | Gated Signals | Coverage | Notes |
|---|---|---|---|---|
| 1 | 2-DOWN (ti>p95, kyle>0) | 1,797 | 1.16% | Baseline champion |
| 2 | 3-DOWN (ti>p95, kyle>0) | 1,260 | 0.82% | Rarer — 3 consecutive bars |
| 3 | DUD (ti>p95, kyle>0) | 442 | 0.29% | Failed bounce — sparse |
| 4 | UDD (ti>p95, kyle>0) | 537 | 0.35% | Momentum reversal — sparse |
| 5 | 2-DOWN no gate | 36,575 | 23.68% | No ti/kyle filter = many signals |
| 6 | HVD (vpt>p90) | 7,959 | 5.15% | Single-bar, own gate |
| 7 | VWAP (vcd<p10) | ~16,473 | ~10.7% | **FIXED**: Originally `> p90` = 0 signals (structural impossibility — DOWN bars always have negative vcd). Changed to `< p10` (extreme negative dislocation). |
| 8 | 2-UP SHORT (ti>p95, kyle<0) | 288 | 0.19% | Thinnest pool — kyle<0 gate very restrictive |
| 9 | Wickless 2-DOWN (wick=0 both) | 710 (**verified**) | 0.46% | Two consecutive wickless DOWN bars — sparse but pure momentum exhaustion |
| 10 | Single wickless DOWN (wick=0) | 7,580 (**verified**) | 4.91% | Single bar opened at high, no wick rejection |
| 11 | DOWN + intra exhaustion (mdd>p75) | 76,350 eligible (**verified**) | ~49% of bars | Highest coverage — to be gated by rolling p75 threshold (~25% pass = ~12%) |

**Total bars after warmup**: 154,467 (SOLUSDT @750)

**Coverage tiers**:
- **Sparse** (0.2-1.2%): Patterns 1-4, 8, 9 — tight directional + gate combos (~200-1800 signals)
- **Medium** (5-11%): Patterns 6, 7, 10 — single-bar with own gate (~8K-16K signals)
- **Dense** (22-24%): Patterns 5, 11 — ungated or broad gate (~34K-37K signals, best for statistical power)

**Cross-asset wick pattern verification (all 10 combos)**:

| Pattern | @750 coverage range | @1000 coverage range | Min signals | Max signals |
|---|---|---|---|---|
| P10 (wl1d) | 4.2-6.7% | 3.3-5.5% | 1,822 (BTC @1000) | 10,078 (XRP @750) |
| P9 (wl2d) | 0.46-1.02% | 0.33-0.89% | 223 (ETH @1000) | 1,686 (XRP @750) |
| P11 (exh eligible) | 49% (0% MDD null) | 49% (0-7.2% MDD null) | 19,589 (BTC @1000) | 81,911 (XRP @750) |

**`opposite_wick_pct` feature distribution (verified)**:
- p50 = 0.216-0.232 across all 5 assets (excellent cross-asset consistency, spread only 0.016)
- ~10% zero mass (wickless bars) — all land in lower half of p50 split, no degeneracy
- Zero nulls (range bars always have `high - low > 0`)
- UP/DOWN symmetric (DOWN p50=0.237, UP p50=0.227) — no direction bias
- **Verdict**: Healthy for p50 median splits

**Key insights**:
- Pattern 7 (VWAP) was redesigned: `vwap_close_deviation > p90` is structurally impossible for DOWN bars (close < VWAP by construction). Changed to `< p10` (extreme negative dislocation).
- Pattern 8 (SHORT) is thinnest at 288 signals. After feature filters (~50% pass at p50), expect ~140. Marginal but acceptable.
- Pattern 9 (wl2d) is also sparse: ETH @1000 has only 223 signals. After feature filters, ~110. At the edge of MinBTL.
- New wick patterns (9-10) explore a previously untested microstructure dimension — bar open location relative to range.
- Pattern 11 (exhaustion) has ~49% eligible bars; after rolling p75 gate expect ~12% final coverage.
- BNB and XRP consistently produce the most wickless signals (higher momentum-driven bar formation).
- **MDD null rate is zero everywhere except BTCUSDT @1000 (7.2%)** — `IS NOT NULL` guard handles this.

**The `signal_coverage` fraction and full signal funnel are included in every NDJSON telemetry line** (see Telemetry Schema).

### Lookback Column Semantics (Verified)

- **Window type**: Time-based rolling (NOT bar-count-based, NOT expanding)
- **Excludes current bar**: Confirmed — extreme values shift lookback at bar N+1, not bar N
- **lookback_trade_count range**: Varies by market activity. At @750/@1000: fully populated (100% coverage for all 5 assets)
- **@500 pipeline gap**: Entire year-blocks with `lookback_trade_count = 0` (SOL/XRP 2021, BTC 2024-25) — caused by rangebar-py not populating those batches. **Resolved by dropping @500.**
- **intra_hurst/intra_permutation_entropy**: 65-90% populated (quantileExactExclusive skips NULLs natively)

## Backtesting Alignment Verification (CRITICAL)

Gen600 must produce results that are **reproducible by backtesting.py** — the same signals, entry prices, and exit prices. This is verified via existing infrastructure plus Gen600-specific additions.

### Existing Validation Infrastructure (Reuse)

| Artifact | Path | What It Validates |
|---|---|---|
| `verify_atomic_nolookahead.sql` | `sql/` | Manual p95 = window p95 (current bar excluded) |
| `test_barrier_alignment.py` | `tests/` | SQL vs backtesting.py exit price match (>95% on shared signals) |
| `test_gen300_barrier_alignment.py` | `tests/` | Feature-filtered SQL vs BT alignment |
| `extraction.py` `_CTE_TEMPLATE` | `src/rangebar_patterns/eval/` | Shared 10-CTE chain (base_bars through trade_outcomes) |
| `introspect.py` | `src/rangebar_patterns/` | Bar-by-bar trade reconstruction |

### Gen600-Specific Alignment Steps

**Step A: Adapt `verify_atomic_nolookahead.sql` for @750/@1000**
- Change symbol/threshold to match Gen600 data (@750 or @1000)
- Add lookback_hurst to the test bar's feature list
- Verify: `lookback_hurst` at test bar = value from bar N-1 (lagInFrame verified)
- Run on BigBlack via `poc.sh`

**Step B: Create `test_gen600_barrier_alignment.py`**
- Fork from `test_gen300_barrier_alignment.py` (186 lines)
- Test the **2-DOWN + ofi_lt_p50 + lookback_hurst_lt_p50** config (the atomic POC config)
- Match by entry bar index (same as Gen200/Gen300 pattern)
- Verify all 3 barrier profiles (inverted/symmetric/momentum)
- Gate: >95% exit price match on shared signals per barrier profile
- Known divergence: None expected (Gen600 uses rolling 1000 in both SQL and BT)

**Step C: Verify SHORT signal barrier reversal**
- Run `introspect.py` on one 2-UP SHORT trade
- Manual check: tp_price < entry_price, sl_price > entry_price
- Verify gap-up SL execution: `greatest(fwd_opens[rsl], sl_price)`
- Verify return sign: negative return = profit for SHORT

**Step D: Reuse `extraction.py` `_CTE_TEMPLATE` structure**
Gen600 templates share the same CTE chain as `extraction.py`:
```
extraction.py _CTE_TEMPLATE          Gen600 template
─────────────────────────             ────────────────
base_bars                      ←──→  base_bars (+ date cutoff, + lookback cols)
running_stats                  ←──→  running_stats
signal_detection               ←──→  signal_detection (+ dir_3 for 3-bar patterns)
champion_signals               ←──→  champion_signals (different WHERE per pattern)
feature1_with_quantile         ←──→  feature1_with_quantile
feature2_with_quantile         ←──→  feature2_with_quantile
signals                        ←──→  signals
forward_arrays                 ←──→  forward_arrays (101 bars for MB=100)
param_with_prices              ←──→  barrier_params (CROSS JOIN → 3 profiles)
barrier_scan                   ←──→  barrier_scan (arraySlice per barrier)
trade_outcomes                 ←──→  trade_outcomes
```
Every CTE pair uses identical logic. The structural alignment is guaranteed by construction.

### Rolling Window Alignment (SQL ↔ backtesting.py)

**Critical**: Both SQL and backtesting.py MUST use the same rolling 1000-bar window:

| Quantile Stage | SQL | backtesting.py |
|---|---|---|
| ti_p95 | `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING` | `_rolling_p95()` (1000-bar, in champion_strategy.py) |
| feature1_q | `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING` (within signal set) | Same rolling window |
| feature2_q | `ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING` (within signal set) | Same rolling window |

**Gen200/Gen300 had a known divergence**: SQL used expanding p95, BT used rolling 1000. This produced different signal sets (~50 common out of ~1800 each). **Gen600 has NO divergence** — both use rolling 1000 from the start. Signal sets should be nearly identical (not just shared-signal comparison).

## Risk Mitigations

| Risk | Mitigation |
|---|---|
| **Lookback column lookahead** | **RESOLVED** — verified safe (excludes current bar, time-based rolling window) |
| **lookback_trade_count = 0** | **RESOLVED** — @500 dropped; @750/@1000 have 100% coverage. Defensive guard retained at zero cost. |
| **SHIBUSDT dead features** | Dropped from sweep — all lookback/intra zero/NULL |
| **DOGEUSDT poor coverage** | Dropped — @500 truncated May 2021, lookback 48-62% across thresholds |
| SHORT barrier math bug (AP-13 mirror) | POC validates: tp_price < entry_price, sl_price > entry_price, gap-up SL = `greatest(open, sl_price)` |
| AP-08 per-barrier arraySlice | Each barrier profile slices to its own max_bars: `arraySlice(fwd_highs, 1, max_bars)` where max_bars comes from the CROSS JOIN |
| Sparse intra features (65% populated) | POC tests intra_hurst with NULL handling; telemetry includes `null_rate` for feature2 when applicable |
| 301K SQL files = ~1.2GB on /tmp | rsync --compress; delete after collect |
| ~21-hour runtime | 8 parallel pueue slots; status.sh at 6-hour and 12-hour marks; crash recovery via config-ID dedup |
| Bonferroni penalty (30,096 tests) | Expected: 0 survivors. Cross-asset/threshold validation is the real filter |
| Config ID collision | Pattern prefix in config_id ensures uniqueness across all 11 patterns |
| **VWAP dislocation structural impossibility** | **RESOLVED** — `vwap_close_deviation > p90` is geometrically impossible for DOWN bars (close < VWAP by construction → vcd always negative; max observed = +0.40 vs p90 threshold = +0.63). Redesigned to `vwap_close_deviation < p10` (extreme negative dislocation = close hammered far below VWAP). Verified: 16,473 signals on SOLUSDT @750 (10.7% coverage). |

---

## Verification

1. ~~**POC step 0**: Lookback column lookahead audit~~ — **DONE** (verified safe, excludes current bar)
1b. **Atomic POC** — **DONE** (2026-02-11): Full CTE chain tested on SOLUSDT @750 with `ofi_lt_p50 + lookback_hurst_lt_p50`. All 3 barrier profiles produced sensible results: inverted=337 signals/PF=1.17/HR=70%, symmetric=PF=1.25/HR=55%, momentum=PF=1.04/HR=31%. Date cutoff, lookback features, rolling quantiles, barrier CROSS JOIN all working correctly.
1c. **Signal Coverage POC** — **DONE** (2026-02-11): All 8 original base patterns measured on SOLUSDT @750. Coverage ranges from 0.19% (2-UP SHORT) to 23.68% (2-DOWN no gate). **Pattern 7 redesigned**: `vwap_close_deviation > p90` = 0 signals (structural impossibility for DOWN bars). Fixed to `< p10` (extreme negative dislocation) = ~16K signals.
1d. **Wick Pattern Validation** — **DONE** (2026-02-11): All 10 asset/threshold combos verified for patterns 9-11. P10 (wl1d): 3.3-6.7% coverage, min 1,822 signals. P9 (wl2d): 0.33-1.02% coverage, min 223 signals (marginal). P11 (exh): 0% MDD null rate on 9/10 combos (BTCUSDT @1000 = 7.2% null, handled by IS NOT NULL guard).
1e. **`opposite_wick_pct` Distribution** — **DONE** (2026-02-11): Cross-asset p50 = 0.216-0.232 (spread 0.016 = excellent consistency). ~10% zero mass. Zero nulls. UP/DOWN symmetric. Healthy for p50 median splits.
1f. **Wick Structural Analysis** — **DONE** (2026-02-11): Verified universal across all 15 symbols — range bars close at their extreme 99.5% of the time (construction artifact). Only opposite wick carries information.
2. **POC step 1**: 14 configs across pattern types — correct 3-row output, barrier math, NULL handling, wick computation
2b. **Alignment step A**: Run adapted `verify_atomic_nolookahead.sql` on @750 with lookback feature verification
2c. **Alignment step B**: Run `test_gen600_barrier_alignment.py` — SQL vs backtesting.py exit price match (>95% gate)
2d. **Alignment step C**: Verify SHORT signal barrier reversal via `introspect.py` manual inspection
3. **POC step 2**: SHORT config — verify reversed barrier prices, gap-up SL execution, negative return = profit
4. `generate.sh` produces exactly 300,960 SQL files with correct directory structure
5. `submit_all.sh` queues jobs; `status.sh` shows progress
6. `collect.sh` downloads, sanitizes, validates all JSONL (every line passes `json.loads()`)
7. `report.sh` produces cross-asset/threshold/barrier/pattern analysis
8. `mise run gen600:generate` through `mise run gen600:report` all work end-to-end

---

## Plan Archive

**Copy this plan to `designs/gen600-plan.md`** in the repository for version control. This is the first implementation step before writing any code.

---

## SR&ED Commit Structure

| Commit | Phase | SRED-Type | Content |
|---|---|---|---|
| 1 | Templates | experimental-development | 22 SQL templates (11 LONG + 11 SHORT mirrors — directional, wick, exhaustion, barrier CROSS JOIN) |
| 2 | Infrastructure | support-work | generate.sh, poc.sh, submit scripts, status/collect |
| 3 | Analysis | applied-research | report.sh with cross-dimensional validation |
