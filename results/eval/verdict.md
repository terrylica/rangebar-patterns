# Beyond-Kelly POC Verdict

## 1. Multiple Testing Corrections

### e-BH FDR (alpha=0.05)
- **Discoveries**: 0 out of 961 configs
- Top 5 E-values: [{"config_id": "ofi_gt_p75__aggression_ratio_lt_p25", "evalue": 1.0395}, {"config_id": "aggression_ratio_lt_p25__turnover_imbalance_gt_p75", "evalue": 1.0395}, {"config_id": "turnover_imbalance_gt_p50__duration_us_lt_p50", "evalue": 1.0371}, {"config_id": "ofi_gt_p50__duration_us_lt_p50", "evalue": 1.0351}, {"config_id": "ofi_gt_p90__vwap_close_deviation_gt_p75", "evalue": 1.0326}]

### Romano-Wolf FWER (B=1000)
- **Rejections**: 0 out of 939
- Critical value: 3.9555

## 2. Overfitting Detection (CSCV/PBO)

- **PBO**: 0.3143 (MARGINAL)
- Mean OOS rank of IS winner: 0.6241
- Most common IS winner: volume_per_trade_gt_p75__aggregation_density_lt_p25

## 3. Cross-Metric Rank Correlations

| Pair | Spearman r | Interpretation |
|------|-----------|----------------|
| cf_es_adj_vs_tamrs | 0.2670 | COMPLEMENTARY |
| dsr_vs_cf_es_adj | 0.0792 | COMPLEMENTARY |
| dsr_vs_grow | 0.0792 | COMPLEMENTARY |
| dsr_vs_omega | 0.0792 | COMPLEMENTARY |
| dsr_vs_tamrs | -0.0759 | COMPLEMENTARY |
| grow_vs_cf_es_adj | 0.9871 | REDUNDANT |
| grow_vs_tamrs | 0.2505 | COMPLEMENTARY |
| kelly_vs_cf_es_adj | 0.6076 | COMPLEMENTARY |
| kelly_vs_dsr | 0.0792 | COMPLEMENTARY |
| kelly_vs_grow | 0.6683 | COMPLEMENTARY |
| kelly_vs_omega | 0.6055 | COMPLEMENTARY |
| kelly_vs_psr | 0.5974 | COMPLEMENTARY |
| kelly_vs_sharpe | 0.6074 | COMPLEMENTARY |
| kelly_vs_tamrs | -0.0005 | COMPLEMENTARY |
| omega_vs_cf_es_adj | 1.0000 | REDUNDANT |
| omega_vs_grow | 0.9866 | REDUNDANT |
| omega_vs_tamrs | 0.2670 | COMPLEMENTARY |
| psr_vs_cf_es_adj | 0.9680 | REDUNDANT |
| psr_vs_dsr | 0.0767 | COMPLEMENTARY |
| psr_vs_grow | 0.9579 | REDUNDANT |
| psr_vs_omega | 0.9678 | REDUNDANT |
| psr_vs_tamrs | 0.2664 | COMPLEMENTARY |
| sharpe_vs_cf_es_adj | 1.0000 | REDUNDANT |
| sharpe_vs_dsr | 0.0792 | COMPLEMENTARY |
| sharpe_vs_grow | 0.9870 | REDUNDANT |
| sharpe_vs_omega | 1.0000 | REDUNDANT |
| sharpe_vs_psr | 0.9685 | REDUNDANT |
| sharpe_vs_tamrs | 0.2674 | COMPLEMENTARY |

### Redundant pairs (r > 0.95): 10
- sharpe_vs_psr: 0.9685
- sharpe_vs_omega: 1.0
- sharpe_vs_grow: 0.987
- sharpe_vs_cf_es_adj: 1.0
- psr_vs_omega: 0.9678
- psr_vs_grow: 0.9579
- psr_vs_cf_es_adj: 0.968
- omega_vs_grow: 0.9866
- omega_vs_cf_es_adj: 1.0
- grow_vs_cf_es_adj: 0.9871

### Complementary pairs (r < 0.80): 18
- kelly_vs_sharpe: 0.6074
- kelly_vs_psr: 0.5974
- kelly_vs_dsr: 0.0792
- kelly_vs_omega: 0.6055
- kelly_vs_grow: 0.6683
- kelly_vs_cf_es_adj: 0.6076
- kelly_vs_tamrs: -0.0005
- sharpe_vs_dsr: 0.0792
- sharpe_vs_tamrs: 0.2674
- psr_vs_dsr: 0.0767
- psr_vs_tamrs: 0.2664
- dsr_vs_omega: 0.0792
- dsr_vs_grow: 0.0792
- dsr_vs_cf_es_adj: 0.0792
- dsr_vs_tamrs: -0.0759
- omega_vs_tamrs: 0.267
- grow_vs_tamrs: 0.2505
- cf_es_adj_vs_tamrs: 0.267

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

## 4b. TAMRS vs Kelly Divergence (Kelly > 0 but TAMRS < 0.05)

**Total**: 194 configs

| config_id | Kelly | TAMRS | N trades |
|-----------|-------|-------|----------|
| aggregation_density_gt_p50__duration_us_ | 0.0052 | 0.0011 | 1018 |
| aggregation_density_gt_p50__duration_us_ | 0.0195 | 0.0013 | 205 |
| aggregation_density_gt_p50__duration_us_ | 0.0093 | 0.0018 | 860 |
| aggregation_density_gt_p75__duration_us_ | 0.0043 | 0.0015 | 376 |
| aggregation_density_gt_p75__duration_us_ | 0.0473 | 0.0030 | 74 |
| aggregation_density_lt_p10__duration_us_ | 0.0143 | 0.0048 | 35 |
| aggregation_density_lt_p25__duration_us_ | 0.0017 | 0.0024 | 216 |
| aggregation_density_lt_p25__duration_us_ | 0.0625 | 0.0046 | 64 |
| aggression_ratio_gt_p50__aggregation_den | 0.0168 | 0.0017 | 788 |
| aggression_ratio_gt_p50__aggregation_den | 0.0448 | 0.0043 | 212 |

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
