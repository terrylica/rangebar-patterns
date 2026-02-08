# Beyond-Kelly POC Verdict

## 1. Multiple Testing Corrections

### e-BH FDR (alpha=0.05)
- **Discoveries**: 0 out of 961 configs
- Top 5 E-values: [{"config_id": "ofi_gt_p75__aggression_ratio_lt_p25", "evalue": 1.0395}, {"config_id": "aggression_ratio_lt_p25__turnover_imbalance_gt_p75", "evalue": 1.0395}, {"config_id": "turnover_imbalance_gt_p50__duration_us_lt_p50", "evalue": 1.0371}, {"config_id": "ofi_gt_p50__duration_us_lt_p50", "evalue": 1.0351}, {"config_id": "ofi_gt_p90__vwap_close_deviation_gt_p75", "evalue": 1.0326}]

### Romano-Wolf FWER (B=1000)
- **Rejections**: 0 out of 939
- Critical value: 3.9555

## 2. Overfitting Detection (CSCV/PBO)

- **PBO**: 0.3286 (MARGINAL)
- Mean OOS rank of IS winner: 0.6886
- Most common IS winner: ofi_gt_p75__aggression_ratio_lt_p25

## 3. Cross-Metric Rank Correlations

| Pair | Spearman r | Interpretation |
|------|-----------|----------------|
| dsr_vs_cf_es_adj | -0.0558 | COMPLEMENTARY |
| dsr_vs_grow | -0.0556 | COMPLEMENTARY |
| dsr_vs_omega | -0.0556 | COMPLEMENTARY |
| grow_vs_cf_es_adj | 0.9813 | REDUNDANT |
| kelly_vs_cf_es_adj | nan | COMPLEMENTARY |
| kelly_vs_dsr | nan | COMPLEMENTARY |
| kelly_vs_grow | nan | COMPLEMENTARY |
| kelly_vs_omega | nan | COMPLEMENTARY |
| kelly_vs_psr | nan | COMPLEMENTARY |
| kelly_vs_sharpe | nan | COMPLEMENTARY |
| omega_vs_cf_es_adj | 0.9940 | REDUNDANT |
| omega_vs_grow | 0.9868 | REDUNDANT |
| psr_vs_cf_es_adj | 0.9614 | REDUNDANT |
| psr_vs_dsr | -0.0066 | COMPLEMENTARY |
| psr_vs_grow | 0.9574 | REDUNDANT |
| psr_vs_omega | 0.9672 | REDUNDANT |
| sharpe_vs_cf_es_adj | 1.0000 | REDUNDANT |
| sharpe_vs_dsr | -0.0558 | COMPLEMENTARY |
| sharpe_vs_grow | 0.9813 | REDUNDANT |
| sharpe_vs_omega | 0.9940 | REDUNDANT |
| sharpe_vs_psr | 0.9619 | REDUNDANT |

### Redundant pairs (r > 0.95): 10
- sharpe_vs_psr: 0.9619
- sharpe_vs_omega: 0.994
- sharpe_vs_grow: 0.9813
- sharpe_vs_cf_es_adj: 1.0
- psr_vs_omega: 0.9672
- psr_vs_grow: 0.9574
- psr_vs_cf_es_adj: 0.9614
- omega_vs_grow: 0.9868
- omega_vs_cf_es_adj: 0.994
- grow_vs_cf_es_adj: 0.9813

### Complementary pairs (r < 0.80): 5
- sharpe_vs_dsr: -0.0558
- psr_vs_dsr: -0.0066
- dsr_vs_omega: -0.0556
- dsr_vs_grow: -0.0556
- dsr_vs_cf_es_adj: -0.0558

## 4. Pathological Cases (Kelly > 0 but DSR < 0.5)

**Total**: 218 configs

| config_id | Kelly | DSR | N trades | MinBTL passes |
|-----------|-------|-----|----------|---------------|
| aggregation_density_gt_p50__duration_us_ | 0.0052 | 0.0000 | 1018 | False |
| aggregation_density_gt_p50__duration_us_ | 0.0195 | 0.0000 | 205 | False |
| aggregation_density_gt_p50__duration_us_ | 0.0093 | 0.0000 | 860 | False |
| aggregation_density_gt_p75__duration_us_ | 0.0043 | 0.0000 | 376 | False |
| aggregation_density_gt_p75__duration_us_ | 0.0473 | 0.0000 | 74 | False |
| aggregation_density_lt_p10__duration_us_ | 0.0143 | 0.0000 | 35 | False |
| aggregation_density_lt_p25__duration_us_ | 0.0017 | 0.0000 | 216 | False |
| aggregation_density_lt_p25__duration_us_ | 0.0625 | 0.0000 | 64 | False |
| aggression_ratio_gt_p50__aggregation_den | 0.0168 | 0.0000 | 788 | False |
| aggression_ratio_gt_p50__aggregation_den | 0.0448 | 0.0000 | 212 | False |

## 5. Recommended Metric Stack

Based on the POC analysis, the recommended minimal metric stack is:

1. **DSR** (Deflated Sharpe Ratio) -- primary ranking metric (replaces Kelly)
2. **MinBTL** -- data sufficiency gate (hard reject if n_trades < MinBTL)
3. **PBO** (from CSCV) -- overfitting detection (reject if PBO > 0.5)
4. **Omega Ratio** -- complementary ranking (captures full distribution)
5. **E-values + e-BH** -- anytime-valid FDR control for live monitoring
6. **Cornish-Fisher ES** -- tail risk filter (reject extreme tail_risk_ratio)

### Metrics to DROP (if redundant):

- sharpe_vs_psr are redundant -- keep only one
- sharpe_vs_omega are redundant -- keep only one
- sharpe_vs_grow are redundant -- keep only one
- sharpe_vs_cf_es_adj are redundant -- keep only one
- psr_vs_omega are redundant -- keep only one
- psr_vs_grow are redundant -- keep only one
- psr_vs_cf_es_adj are redundant -- keep only one
- omega_vs_grow are redundant -- keep only one
- omega_vs_cf_es_adj are redundant -- keep only one
- grow_vs_cf_es_adj are redundant -- keep only one

## 6. Summary Verdict

**CONSISTENT WITH BONFERRONI**: Zero discoveries under both e-BH and Romano-Wolf, confirming that no configs survive rigorous multiple testing.
