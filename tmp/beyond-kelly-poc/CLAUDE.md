# Beyond-Kelly POC - AI Context

**Scope**: 9-agent, 8-layer evaluation metrics POC for 1,008 dual-feature configs on SOLUSDT @500dbps.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Final Decision: 5-Metric Evaluation Stack

| Metric | Role               | Threshold      |
| ------ | ------------------ | -------------- |
| Kelly  | Primary ranker     | > 0            |
| Omega  | Distribution shape | > 1.0          |
| DSR    | Multiple testing   | > 0.95 (N-adj) |
| MinBTL | Data sufficiency   | n >= MinBTL    |
| PBO    | Overfitting detect | < 0.50         |

**Dropped** (r > 0.95 redundant with Omega): Sharpe, PSR, GROW, CF-ES

**Dropped** (insufficient evidence): E-values (max=1.04, need >= 20)

---

## 8-Layer Architecture

| Layer | File                     | Purpose                           | Key Output                |
| ----- | ------------------------ | --------------------------------- | ------------------------- |
| 1a    | layer1_trade_returns.py  | Extract per-trade returns from CH | trade_returns.jsonl       |
| 1b    | layer1_sql_moments.py    | Extract return moments from CH    | moments.jsonl             |
| 2     | layer2_dsr_psr.py        | DSR + PSR computation             | dsr_rankings.jsonl        |
| 3     | layer3_minbtl.py         | MinBTL data sufficiency gate      | minbtl_gate.jsonl         |
| 4     | layer4_cornish_fisher.py | Cornish-Fisher Expected Shortfall | cornish_fisher.jsonl      |
| 5     | layer5_omega_ratio.py    | Omega ratio from trade returns    | omega_rankings.jsonl      |
| 6     | layer6_cscv_pbo.py       | CSCV/PBO overfitting detection    | cscv_pbo.jsonl            |
| 7     | layer7_evalues_grow.py   | E-values + GROW sequential test   | evalues.jsonl             |
| 8     | layer8_synthesis.py      | Combine all metrics, verdict      | verdict.md + correlations |

---

## Key Results

| Check                           | Value                 |
| ------------------------------- | --------------------- |
| e-BH discoveries                | **0** / 961           |
| Romano-Wolf rejections          | **0** / 939           |
| DSR > 0.95                      | **0** / 961           |
| PBO                             | **0.3286** (marginal) |
| Kelly > 0 configs               | 220 / 1,008           |
| Pathological (Kelly>0, DSR<0.5) | 218                   |
| Expected max SR (null)          | 3.2574                |

---

## Bug Fixes Applied

1. **DSR var_sr bug** (layer2): Changed `var_sr = np.var(valid_srs)` (= 6.8 trillion) to `var_sr = 1.0` (unit variance under null, per Bailey & Lopez de Prado 2014). This fixed expected_max_sr from 8.5M to 3.26.

2. **NaN Kelly correlations** (layer8): Added `math.isfinite()` filter. 19 configs had NaN Kelly from SQL division-by-zero, which polluted all Spearman correlations.

---

## Correlation Matrix (n=955 configs)

| Pair            | Spearman r |
| --------------- | ---------- |
| Kelly vs Sharpe | 0.607      |
| Kelly vs PSR    | 0.597      |
| Kelly vs DSR    | 0.079      |
| Kelly vs Omega  | 0.606      |
| Kelly vs GROW   | 0.668      |
| Kelly vs CF-ES  | 0.608      |

Redundancy cluster {Sharpe, PSR, Omega, GROW, CF-ES}: all pairwise r > 0.95.
DSR is near-zero correlation with everything — functions as binary gate.

---

## How to Re-Run

```bash
# Layer 1 requires SSH tunnel to remote ClickHouse (set RANGEBAR_CH_HOST)
.venv/bin/python tmp/beyond-kelly-poc/layer1_trade_returns.py
.venv/bin/python tmp/beyond-kelly-poc/layer1_sql_moments.py

# Layers 2-8 run locally on cached results
.venv/bin/python tmp/beyond-kelly-poc/layer2_dsr_psr.py
.venv/bin/python tmp/beyond-kelly-poc/layer3_minbtl.py
.venv/bin/python tmp/beyond-kelly-poc/layer4_cornish_fisher.py
.venv/bin/python tmp/beyond-kelly-poc/layer5_omega_ratio.py
.venv/bin/python tmp/beyond-kelly-poc/layer6_cscv_pbo.py
.venv/bin/python tmp/beyond-kelly-poc/layer7_evalues_grow.py
.venv/bin/python tmp/beyond-kelly-poc/layer8_synthesis.py
```

Decision documented in [Issue #12](https://github.com/terrylica/rangebar-patterns/issues/12).
