# eval/ — Evaluation Metrics Subpackage

**Navigation**: [Root CLAUDE.md](/CLAUDE.md) | [Config](/src/rangebar_patterns/config.py) | [Issue #12](https://github.com/terrylica/rangebar-patterns/issues/12) | [Issue #16](https://github.com/terrylica/rangebar-patterns/issues/16)

---

## TAMRS Evaluation Stack

TAMRS (Tail-Adjusted Mean Reversion Score) replaces Kelly as primary ranker (Issue #16).

| Metric            | Role                | Threshold      | Module               |
| ----------------- | ------------------- | -------------- | -------------------- |
| TAMRS             | Primary ranker      | > 0            | tamrs.py             |
| Rachev            | Tail asymmetry      | > 0.30 (T2)    | rachev.py            |
| CDaR              | Clustered losses    | (via SL/CDaR)  | cdar.py              |
| OU                | Mean-reversion fit  | > 0.30 (T2)    | ou_barriers.py       |
| Omega             | Distribution shape  | > 1.0          | omega.py             |
| DSR               | Multiple testing    | > 0.95 (N-adj) | dsr.py               |
| MinBTL            | Data sufficiency    | n >= MinBTL    | minbtl.py            |
| PBO               | Overfitting detect  | < 0.50         | cscv.py              |
| Signal Regularity | Temporal clustering | CV < 0.80 (T2) | signal_regularity.py |

**TAMRS formula**: `Rachev(0.05) * min(1, |SL_emp| / CDaR(0.95)) * min(1, TP_emp / TP_OU)`

**Dropped** (r > 0.95 redundant with Omega): Sharpe, PSR, GROW, CF-ES

---

## Module Index

| Module                 | Purpose                                       | Key Function(s)                                                      |
| ---------------------- | --------------------------------------------- | -------------------------------------------------------------------- |
| `_io.py`               | Shared I/O: load_jsonl, results_dir           | `results_dir()`, `load_jsonl()`                                      |
| `extraction.py`        | ClickHouse SQL extraction (moments + returns) | `generate_configs()`, `build_sql()`, `run_query_ou_prices()`         |
| `dsr.py`               | DSR + PSR                                     | `compute_psr()`, `expected_max_sr()`                                 |
| `minbtl.py`            | Minimum Backtest Length gate                  | `compute_minbtl()`                                                   |
| `cornish_fisher.py`    | Cornish-Fisher Expected Shortfall             | `cornish_fisher_quantile()`, `cf_expected_shortfall()`               |
| `omega.py`             | Omega Ratio from trade returns                | `compute_omega()`                                                    |
| `cscv.py`              | CSCV/PBO with TAMRS or Sharpe ranker          | `compute_sharpe()`, `compute_tamrs_for_block()`                      |
| `evalues.py`           | E-values + GROW sequential test               | `compute_evalues()`                                                  |
| `rachev.py`            | Rachev ratio (CVaR tail asymmetry)            | `compute_rachev()`                                                   |
| `cdar.py`              | CDaR (Conditional Drawdown at Risk)           | `compute_cdar()`                                                     |
| `ou_barriers.py`       | OU calibration + barrier ratio                | `calibrate_ou()`, `ou_barrier_ratio()`                               |
| `tamrs.py`             | TAMRS composite (Rachev _SL/CDaR_ OU)         | `compute_tamrs()`                                                    |
| `synthesis.py`         | e-BH FDR + Romano-Wolf + TAMRS correlation    | `ebh_procedure()`, `romano_wolf_stepdown()`                          |
| `signal_regularity.py` | KDE temporal regularity (Issue #17)           | `compute_signal_regularity()`                                        |
| `screening.py`         | Multi-tier screening (TAMRS + regularity)     | `passes_tier()`, `compute_composite_scores()`                        |
| `ranking.py`           | Per-metric percentile cutoffs + intersection  | `percentile_ranks()`, `apply_cutoff()`, `run_ranking_with_cutoffs()` |
| `cross_asset.py`       | Gen500 cross-asset robustness metrics         | `compute_cross_asset_metrics()`, `load_gen500_data()`                |

---

## Configuration

All research parameters come from `rangebar_patterns.config` (SSoT = `.mise.toml` `[env]`):

| Config Var                 | Used By                       |
| -------------------------- | ----------------------------- |
| `SYMBOL`                   | extraction.py, ou_barriers.py |
| `THRESHOLD_DBPS`           | extraction.py, ou_barriers.py |
| `TP_MULT`                  | extraction.py                 |
| `SL_MULT`                  | extraction.py                 |
| `MAX_BARS`                 | extraction.py                 |
| `N_TRIALS`                 | dsr.py, minbtl.py             |
| `ALPHA`                    | evalues.py, synthesis.py      |
| `DSR_THRESHOLD`            | dsr.py                        |
| `RACHEV_ALPHA`             | rachev.py                     |
| `CDAR_ALPHA`               | cdar.py                       |
| `MIN_TRADES_RACHEV`        | rachev.py                     |
| `MIN_TRADES_CDAR`          | cdar.py                       |
| `TP_EMP`                   | ou_barriers.py, tamrs.py      |
| `SL_EMP`                   | cdar.py, cscv.py              |
| `CSCV_RANKER`              | cscv.py                       |
| `CSCV_SPLITS`              | cscv.py                       |
| `SCREEN_TAMRS_MIN`         | screening.py                  |
| `SCREEN_RACHEV_MIN`        | screening.py                  |
| `SCREEN_OU_RATIO_MIN`      | screening.py                  |
| `MIN_TRADES_REGULARITY`    | signal_regularity.py          |
| `SCREEN_REGULARITY_CV_MAX` | screening.py                  |
| `SCREEN_COVERAGE_MIN`      | screening.py                  |
| `RANK_CUT_*` (12 metrics)  | ranking.py                    |
| `RANK_TOP_N`               | ranking.py                    |
| `RANK_OBJECTIVE`           | rank_optimize.py              |
| `RANK_N_TRIALS`            | rank_optimize.py              |
| `RANK_TARGET_N`            | rank_optimize.py              |

Override via environment: `RBP_RACHEV_ALPHA=0.10 mise run eval:rachev`

---

## How to Run

```bash
# Individual modules
mise run eval:extract          # Requires ClickHouse SSH
mise run eval:ou               # Requires ClickHouse SSH
mise run eval:dsr              # Local, reads moments.jsonl
mise run eval:minbtl
mise run eval:cornish-fisher
mise run eval:omega            # Reads trade_returns.jsonl
mise run eval:rachev           # Reads trade_returns.jsonl
mise run eval:cdar             # Reads trade_returns.jsonl
mise run eval:tamrs            # Joins rachev + cdar + ou
mise run eval:cscv             # Uses RBP_CSCV_RANKER
mise run eval:regularity       # KDE signal regularity
mise run eval:evalues
mise run eval:synthesize
mise run eval:screen
mise run eval:cross-asset       # Gen500 cross-asset robustness metrics
mise run eval:rank             # Per-metric percentile ranking
mise run eval:rank-optimize    # Optuna cutoff optimization (NSGA-II Pareto)

# Pipeline orchestration
mise run eval:compute          # Phase 1: all parallel local metrics
mise run eval:compute-phase2   # Phase 2: TAMRS + CSCV (after Phase 1)
mise run eval:full             # Everything: extract + ou + compute + synthesize + screen + rank

# POC validation
mise run eval:tamrs-poc        # Synthetic profile validation
```

---

## Results

Output goes to `results/eval/` (repo root, git-tracked):

| File                             | Source Module        |
| -------------------------------- | -------------------- |
| moments.jsonl                    | extraction.py        |
| trade_returns.jsonl              | extraction.py        |
| dsr_rankings.jsonl               | dsr.py               |
| minbtl_gate.jsonl                | minbtl.py            |
| cornish_fisher.jsonl             | cornish_fisher.py    |
| omega_rankings.jsonl             | omega.py             |
| cscv_pbo.jsonl                   | cscv.py              |
| evalues.jsonl                    | evalues.py           |
| rachev_rankings.jsonl            | rachev.py            |
| cdar_rankings.jsonl              | cdar.py              |
| ou_calibration.jsonl             | ou_barriers.py       |
| tamrs_rankings.jsonl             | tamrs.py             |
| tamrs_poc.jsonl                  | tamrs_poc.py         |
| signal_regularity_rankings.jsonl | signal_regularity.py |
| ebh_fdr.jsonl                    | synthesis.py         |
| romano_wolf.jsonl                | synthesis.py         |
| rank_correlations.jsonl          | synthesis.py         |
| verdict.md                       | synthesis.py         |
| lenient_screen.jsonl             | screening.py         |
| lenient_verdict.md               | screening.py         |
| rankings.jsonl                   | ranking.py           |
| ranking_report.md                | ranking.py           |
| cross_asset_rankings.jsonl       | cross_asset.py       |
| rank_optimization.jsonl          | rank_optimize.py     |

---

## Key Results (SOLUSDT @500dbps, 1,008 configs)

| Check                           | Value                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------- |
| e-BH discoveries                | **0** / 961                                                                  |
| Romano-Wolf rejections          | **0** / 939                                                                  |
| DSR > 0.95                      | **0** / 961                                                                  |
| PBO (TAMRS ranker)              | **0.3714** (marginal)                                                        |
| Kelly > 0 configs               | 220 / 1,008                                                                  |
| Pathological (Kelly>0, DSR<0.5) | 218                                                                          |
| Expected max SR (null)          | 3.2574                                                                       |
| TAMRS range (rolling 1000-bar)  | [0.009, 0.379]                                                               |
| OU method                       | Rolling 1000-bar lookback per signal                                         |
| OU ratio range                  | [0.215, 0.664] (median 0.388)                                                |
| Spearman(TAMRS, Kelly)          | -0.010 (uncorrelated)                                                        |
| T1 / T2 / T3 pass               | 298 / **69** / 0 (Kelly removed, binding: Omega)                             |
| Pareto front (NSGA-II)          | 76 solutions (11 metrics + cross-asset, Kelly excluded)                      |
| XA consistency (#1)             | `price_impact_lt_p10__volume_per_trade_gt_p75` (91.7% PF>1 across 12 assets) |
