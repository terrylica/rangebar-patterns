# eval/ — Evaluation Metrics Subpackage

**Navigation**: [Root CLAUDE.md](/CLAUDE.md) | [Config](/src/rangebar_patterns/config.py) | [Issue #12](https://github.com/terrylica/rangebar-patterns/issues/12)

---

## 5-Metric Evaluation Stack

| Metric | Role               | Threshold      | Module        |
| ------ | ------------------ | -------------- | ------------- |
| Kelly  | Primary ranker     | > 0            | extraction.py |
| Omega  | Distribution shape | > 1.0          | omega.py      |
| DSR    | Multiple testing   | > 0.95 (N-adj) | dsr.py        |
| MinBTL | Data sufficiency   | n >= MinBTL    | minbtl.py     |
| PBO    | Overfitting detect | < 0.50         | cscv.py       |

**Dropped** (r > 0.95 redundant with Omega): Sharpe, PSR, GROW, CF-ES

---

## Module Index

| Module              | Purpose                                       | Key Function(s)                                        |
| ------------------- | --------------------------------------------- | ------------------------------------------------------ |
| `_io.py`            | Shared I/O: load_jsonl, results_dir           | `results_dir()`, `load_jsonl()`                        |
| `extraction.py`     | ClickHouse SQL extraction (moments + returns) | `generate_configs()`, `build_sql()`                    |
| `dsr.py`            | DSR + PSR                                     | `compute_psr()`, `expected_max_sr()`                   |
| `minbtl.py`         | Minimum Backtest Length gate                  | `compute_minbtl()`                                     |
| `cornish_fisher.py` | Cornish-Fisher Expected Shortfall             | `cornish_fisher_quantile()`, `cf_expected_shortfall()` |
| `omega.py`          | Omega Ratio from trade returns                | `compute_omega()`                                      |
| `cscv.py`           | CSCV/PBO overfitting detection                | `compute_sharpe()`                                     |
| `evalues.py`        | E-values + GROW sequential test               | `compute_evalues()`                                    |
| `synthesis.py`      | e-BH FDR + Romano-Wolf + verdict              | `ebh_procedure()`, `romano_wolf_stepdown()`            |
| `screening.py`      | Multi-tier screening pipeline                 | `passes_tier()`, `compute_composite_scores()`          |

---

## Configuration

All research parameters come from `rangebar_patterns.config` (SSoT = `.mise.toml` `[env]`):

| Config Var       | Used By                  |
| ---------------- | ------------------------ |
| `SYMBOL`         | extraction.py            |
| `THRESHOLD_DBPS` | extraction.py            |
| `TP_MULT`        | extraction.py            |
| `SL_MULT`        | extraction.py            |
| `MAX_BARS`       | extraction.py            |
| `N_TRIALS`       | dsr.py, minbtl.py        |
| `ALPHA`          | evalues.py, synthesis.py |
| `DSR_THRESHOLD`  | dsr.py                   |

Override via environment: `RBP_SYMBOL=ETHUSDT python -m rangebar_patterns.eval.extraction`

---

## How to Run

```bash
# Individual modules
python -m rangebar_patterns.eval.extraction    # Requires ClickHouse SSH
python -m rangebar_patterns.eval.dsr           # Local, reads moments.jsonl
python -m rangebar_patterns.eval.minbtl
python -m rangebar_patterns.eval.cornish_fisher
python -m rangebar_patterns.eval.omega         # Reads trade_returns.jsonl
python -m rangebar_patterns.eval.cscv
python -m rangebar_patterns.eval.evalues
python -m rangebar_patterns.eval.synthesis
python -m rangebar_patterns.eval.screening

# Full pipeline (planned)
mise run eval:full
```

---

## Results

Output goes to `results/eval/` (repo root, git-tracked):

| File                    | Source Module     |
| ----------------------- | ----------------- |
| moments.jsonl           | extraction.py     |
| trade_returns.jsonl     | extraction.py     |
| dsr_rankings.jsonl      | dsr.py            |
| minbtl_gate.jsonl       | minbtl.py         |
| cornish_fisher.jsonl    | cornish_fisher.py |
| omega_rankings.jsonl    | omega.py          |
| cscv_pbo.jsonl          | cscv.py           |
| evalues.jsonl           | evalues.py        |
| ebh_fdr.jsonl           | synthesis.py      |
| romano_wolf.jsonl       | synthesis.py      |
| rank_correlations.jsonl | synthesis.py      |
| verdict.md              | synthesis.py      |
| lenient_screen.jsonl    | screening.py      |
| lenient_verdict.md      | screening.py      |

---

## Key Results (SOLUSDT @500dbps, 1,008 configs)

| Check                           | Value                 |
| ------------------------------- | --------------------- |
| e-BH discoveries                | **0** / 961           |
| Romano-Wolf rejections          | **0** / 939           |
| DSR > 0.95                      | **0** / 961           |
| PBO                             | **0.3286** (marginal) |
| Kelly > 0 configs               | 220 / 1,008           |
| Pathological (Kelly>0, DSR<0.5) | 218                   |
| Expected max SR (null)          | 3.2574                |
