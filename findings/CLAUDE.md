# Research Findings - AI Context

**Scope**: Chronological research analysis documents from brute-force pattern discovery.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Findings Index

| Date       | File                                       | Key Insight                                                                                                                             |
| ---------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-02-01 | parameter-free-methods.md                  | E-values, ADWIN, TDA for parameter-free evaluation                                                                                      |
| 2026-02-02 | brute-force-synthesis.md                   | Pattern analysis across Gen1-Gen110                                                                                                     |
| 2026-02-02 | artifact-synthesis.md                      | NN feature engineering from brute-force results                                                                                         |
| 2026-02-02 | ood-deep-research.md                       | OOD robustness methods                                                                                                                  |
| 2026-02-05 | production-readiness-audit.md              | **CONDITIONAL GO**: lagInFrame fix, DSR=1.000                                                                                           |
| 2026-02-05 | microstructure-analysis.md                 | VPIN, Kyle lambda, OFI implementation                                                                                                   |
| 2026-02-05 | microstructure-deep-research.md            | Regime detection, exhaustion patterns                                                                                                   |
| 2026-02-07 | overnight-sweep-forensic-analysis.md       | **Gen500-520**: 15,300 configs, 0 survive Bonferroni, 56 dual-validated                                                                 |
| 2026-02-07 | beyond-kelly-metrics.md                    | SOTA metrics: DSR, CSCV/PBO, MinBTL, e-values, Omega, Cornish-Fisher ES                                                                 |
| 2026-02-07 | `tmp/beyond-kelly-poc/results/verdict.md`  | **Beyond-Kelly POC**: 0 survive e-BH/Romano-Wolf, 5-metric stack decided                                                                |
| 2026-02-11 | feature-column-provenance-audit.md         | Feature column schema change audit (kyle_lambda → kyle_lambda_proxy)                                                                    |
| 2026-02-12 | gen600-sweep-results.md                    | **Gen600**: 300K configs, 13K survive Bonferroni, LONG>>SHORT, exh_l dominates                                                          |
| 2026-02-12 | 2026-02-12-gen600-oracle-validation.md     | **Oracle**: SQL vs backtesting.py 5-gate PASS on 3 assets, hedging=True req'd                                                           |
| 2026-02-13 | kelly-alternatives-tail-risk-evaluation.md | **Gemini 3 Pro**: CDaR, Rachev Ratio, UPI, e-values, OU barriers, TCP gates                                                             |
| 2026-02-13 | 2026-02-13-kelly-deep-dive-3-methods.md    | **Gemini 3 Pro**: Rachev Ratio, CDaR, OU barriers, TAMRS composite score                                                                |
| 2026-02-15 | mcdm-pareto-ranking-methods.md             | **Gemini 3 Pro**: MCDM/TOPSIS/pymoo for threshold-free Pareto ranking ([#28](https://github.com/terrylica/rangebar-patterns/issues/28)) |
