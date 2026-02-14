# Per-Metric Percentile Ranking Report

## 1. Cutoffs Applied

| Metric | Cutoff (top X%) | Configs Passing |
|--------|-----------------|-----------------|
| TAMRS | 30% | 275 |
| Rachev | 90% | 824 |
| OU Ratio | 60% | 585 |
| SL/CDaR | 50% | 470 |
| Omega | 70% | 673 |
| DSR | 95% | 961 |
| MinBTL Headroom | 25% | 253 |
| E-value | 95% | 913 |
| Regularity CV | 65% | 583 |
| Coverage | 85% | 797 |
| Trade Count | 100% | 1008 |
| Kelly | 35% | 335 |

**Intersection (pass ALL cutoffs)**: 11 / 1008 configs

## 2. Intersection Configs

| Rank | Config ID | Avg Pct | TAMRS | Rachev | OU Ratio | SL/CDaR | Omega | DSR | MinBTL Headroom | E-value | Regularity CV | Coverage | Trade Count | Kelly |
|------|-----------|---------|-------|--------|----------|---------|-------|-----|-----------------|---------|---------------|----------|-------------|-------|
| 1 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p50 | 74.7 | 87.5 | 49.9 | 68.4 | 84.1 | 94.3 | 49.9 | 91.2 | 95.9 | 58.0 | 86.7 | 36.3 | 94.3 |
| 2 | volume_per_trade_gt_p75__aggregation_density_lt_p25 | 74.2 | 94.1 | 66.7 | 41.2 | 91.7 | 95.8 | 49.9 | 96.3 | 97.6 | 91.3 | 37.1 | 32.0 | 96.2 |
| 3 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 73.2 | 99.8 | 19.3 | 76.3 | 98.9 | 98.9 | 49.9 | 99.0 | 99.5 | 78.6 | 45.6 | 13.1 | 99.0 |
| 4 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p75 | 73.0 | 99.1 | 19.3 | 76.3 | 97.9 | 98.9 | 49.9 | 99.0 | 99.5 | 78.6 | 45.6 | 13.1 | 99.0 |
| 5 | turnover_imbalance_lt_p25__price_impact_lt_p25 | 72.7 | 86.4 | 85.3 | 55.0 | 83.6 | 92.0 | 49.9 | 86.8 | 93.0 | 91.3 | 18.3 | 38.2 | 92.4 |
| 6 | ofi_gt_p90__price_impact_lt_p10 | 72.6 | 92.7 | 85.3 | 60.3 | 89.2 | 91.8 | 49.9 | 75.8 | 91.6 | 91.3 | 24.8 | 24.0 | 94.5 |
| 7 | ofi_gt_p90__aggregation_density_gt_p50 | 72.4 | 82.9 | 85.3 | 82.1 | 78.0 | 89.9 | 49.9 | 79.3 | 91.2 | 38.2 | 65.1 | 35.2 | 92.1 |
| 8 | ofi_gt_p90__vwap_close_deviation_gt_p50 | 72.3 | 70.9 | 49.9 | 70.9 | 66.9 | 94.6 | 49.9 | 92.5 | 96.4 | 58.5 | 86.7 | 36.0 | 94.4 |
| 9 | turnover_imbalance_gt_p90__aggregation_density_gt_p50 | 71.8 | 79.4 | 85.3 | 82.1 | 73.9 | 89.9 | 49.9 | 79.3 | 91.2 | 38.2 | 65.1 | 35.2 | 92.0 |
| 10 | ofi_lt_p25__price_impact_lt_p25 | 70.1 | 71.0 | 85.3 | 55.0 | 68.3 | 92.0 | 49.9 | 86.8 | 93.0 | 91.3 | 18.3 | 38.2 | 92.5 |
| 11 | price_impact_lt_p25__duration_us_lt_p50 | 68.8 | 71.7 | 60.1 | 59.7 | 68.7 | 89.4 | 49.9 | 93.9 | 97.0 | 52.9 | 18.3 | 71.7 | 92.3 |

## 3. Per-Metric Top 10

### TAMRS

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p90 | 100.0 | 0.379308 |
| 2 | ofi_gt_p50__aggression_ratio_lt_p25 | 99.9 | 0.350157 |
| 3 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 99.8 | 0.263459 |
| 4 | aggression_ratio_lt_p50__turnover_imbalance_gt_p90 | 99.7 | 0.248886 |
| 5 | aggression_ratio_lt_p25__turnover_imbalance_gt_p50 | 99.6 | 0.241969 |
| 6 | vwap_close_deviation_lt_p10__duration_us_gt_p90 | 99.5 | 0.235120 |
| 7 | turnover_imbalance_gt_p90__price_impact_gt_p75 | 99.3 | 0.230432 |
| 8 | ofi_gt_p90__price_impact_gt_p75 | 99.2 | 0.229795 |
| 9 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p75 | 99.1 | 0.197912 |
| 10 | price_impact_gt_p90__volume_per_trade_gt_p75 | 99.0 | 0.190147 |

### Rachev

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_lt_p50__aggression_ratio_gt_p50 | 85.3 | 2.000000 |
| 2 | ofi_lt_p50__aggression_ratio_gt_p75 | 85.3 | 2.000000 |
| 3 | ofi_lt_p50__aggression_ratio_gt_p90 | 85.3 | 2.000000 |
| 4 | ofi_gt_p75__aggression_ratio_gt_p50 | 85.3 | 2.000000 |
| 5 | ofi_gt_p75__aggression_ratio_gt_p75 | 85.3 | 2.000000 |
| 6 | ofi_gt_p75__aggression_ratio_gt_p90 | 85.3 | 2.000000 |
| 7 | ofi_lt_p25__aggression_ratio_gt_p50 | 85.3 | 2.000000 |
| 8 | ofi_gt_p90__aggression_ratio_gt_p50 | 85.3 | 2.000000 |
| 9 | ofi_gt_p90__aggression_ratio_gt_p75 | 85.3 | 2.000000 |
| 10 | ofi_gt_p90__aggression_ratio_gt_p90 | 85.3 | 2.000000 |

### OU Ratio

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | aggression_ratio_lt_p25__duration_us_gt_p90 | 100.0 | 0.664003 |
| 2 | ofi_gt_p50__aggression_ratio_lt_p10 | 99.8 | 0.634427 |
| 3 | aggression_ratio_lt_p10__turnover_imbalance_gt_p50 | 99.8 | 0.634427 |
| 4 | ofi_lt_p25__aggression_ratio_gt_p90 | 99.6 | 0.627846 |
| 5 | aggression_ratio_gt_p90__turnover_imbalance_lt_p25 | 99.6 | 0.627846 |
| 6 | ofi_lt_p25__duration_us_gt_p90 | 99.4 | 0.607144 |
| 7 | turnover_imbalance_lt_p25__duration_us_gt_p90 | 99.4 | 0.607144 |
| 8 | ofi_lt_p25__duration_us_gt_p75 | 99.2 | 0.545516 |
| 9 | turnover_imbalance_lt_p25__duration_us_gt_p75 | 99.2 | 0.545516 |
| 10 | ofi_lt_p10__duration_us_gt_p50 | 99.0 | 0.509342 |

### SL/CDaR

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_lt_p25__aggression_ratio_gt_p75 | 99.8 | 0.500000 |
| 2 | aggression_ratio_gt_p75__turnover_imbalance_lt_p25 | 99.8 | 0.500000 |
| 3 | price_impact_gt_p90__volume_per_trade_gt_p90 | 99.8 | 0.500000 |
| 4 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p90 | 99.8 | 0.500000 |
| 5 | ofi_gt_p50__aggression_ratio_lt_p25 | 99.6 | 0.478997 |
| 6 | aggression_ratio_lt_p50__turnover_imbalance_gt_p90 | 99.3 | 0.333333 |
| 7 | price_impact_gt_p75__duration_us_gt_p90 | 99.3 | 0.333333 |
| 8 | price_impact_gt_p90__duration_us_gt_p50 | 99.3 | 0.333333 |
| 9 | vwap_close_deviation_lt_p10__duration_us_gt_p90 | 99.3 | 0.333333 |
| 10 | ofi_gt_p75__vwap_close_deviation_gt_p90 | 98.9 | 0.331191 |

### Omega

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_gt_p75__aggression_ratio_lt_p25 | 99.9 | 5.942338 |
| 2 | aggression_ratio_lt_p25__turnover_imbalance_gt_p75 | 99.9 | 5.942338 |
| 3 | ofi_gt_p90__vwap_close_deviation_gt_p90 | 99.7 | 3.311908 |
| 4 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p90 | 99.7 | 3.311908 |
| 5 | ofi_gt_p75__vwap_close_deviation_gt_p90 | 99.5 | 2.325810 |
| 6 | turnover_imbalance_gt_p75__vwap_close_deviation_gt_p90 | 99.5 | 2.325810 |
| 7 | price_impact_gt_p90__volume_per_trade_gt_p90 | 99.4 | 2.297398 |
| 8 | ofi_gt_p50__aggression_ratio_lt_p25 | 99.2 | 2.172147 |
| 9 | aggression_ratio_lt_p25__turnover_imbalance_gt_p50 | 99.2 | 2.172147 |
| 10 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p90 | 99.1 | 2.133333 |

### DSR

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | aggression_ratio_gt_p50__aggregation_density_gt_p90 | 100.0 | 0.500000 |
| 2 | ofi_gt_p75__aggression_ratio_lt_p25 | 99.8 | 0.000001 |
| 3 | aggression_ratio_lt_p25__turnover_imbalance_gt_p75 | 99.8 | 0.000001 |
| 4 | ofi_gt_p50__aggression_ratio_gt_p50 | 49.9 | 0.000000 |
| 5 | ofi_gt_p50__aggression_ratio_lt_p50 | 49.9 | 0.000000 |
| 6 | ofi_gt_p50__aggression_ratio_gt_p75 | 49.9 | 0.000000 |
| 7 | ofi_gt_p50__aggression_ratio_lt_p25 | 49.9 | 0.000000 |
| 8 | ofi_gt_p50__aggression_ratio_gt_p90 | 49.9 | 0.000000 |
| 9 | ofi_lt_p50__aggression_ratio_gt_p50 | 49.9 | 0.000000 |
| 10 | ofi_lt_p50__aggression_ratio_lt_p50 | 49.9 | 0.000000 |

### MinBTL Headroom

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 100.0 | 0.470600 |
| 2 | ofi_gt_p50__duration_us_lt_p50 | 99.9 | 0.448200 |
| 3 | price_impact_gt_p90__aggregation_density_gt_p75 | 99.8 | 0.412000 |
| 4 | aggregation_density_gt_p90__duration_us_gt_p50 | 99.7 | 0.389700 |
| 5 | ofi_gt_p75__price_impact_gt_p75 | 99.6 | 0.355100 |
| 6 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 99.6 | 0.355100 |
| 7 | price_impact_gt_p50__duration_us_gt_p90 | 99.4 | 0.340000 |
| 8 | aggression_ratio_gt_p50__duration_us_lt_p50 | 99.3 | 0.326800 |
| 9 | ofi_gt_p75__aggression_ratio_lt_p25 | 99.2 | 0.322100 |
| 10 | aggression_ratio_lt_p25__turnover_imbalance_gt_p75 | 99.2 | 0.322100 |

### E-value

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_gt_p75__aggression_ratio_lt_p25 | 99.9 | 1.039473 |
| 2 | aggression_ratio_lt_p25__turnover_imbalance_gt_p75 | 99.9 | 1.039473 |
| 3 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 99.8 | 1.037137 |
| 4 | ofi_gt_p50__duration_us_lt_p50 | 99.7 | 1.035125 |
| 5 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 99.5 | 1.032557 |
| 6 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p75 | 99.5 | 1.032557 |
| 7 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p90 | 99.4 | 1.029442 |
| 8 | ofi_gt_p75__price_impact_gt_p75 | 99.2 | 1.026111 |
| 9 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 99.2 | 1.026111 |
| 10 | volume_per_trade_gt_p90__aggregation_density_lt_p25 | 99.1 | 1.025707 |

### Regularity CV

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_gt_p50__aggression_ratio_lt_p25 | 91.3 | 0.000000 |
| 2 | ofi_gt_p75__aggression_ratio_gt_p90 | 91.3 | 0.000000 |
| 3 | ofi_gt_p90__aggression_ratio_lt_p50 | 91.3 | 0.000000 |
| 4 | ofi_gt_p50__price_impact_lt_p10 | 91.3 | 0.000000 |
| 5 | ofi_lt_p50__price_impact_lt_p10 | 91.3 | 0.000000 |
| 6 | ofi_gt_p75__price_impact_lt_p25 | 91.3 | 0.000000 |
| 7 | ofi_gt_p75__price_impact_lt_p10 | 91.3 | 0.000000 |
| 8 | ofi_lt_p25__price_impact_lt_p50 | 91.3 | 0.000000 |
| 9 | ofi_lt_p25__price_impact_lt_p25 | 91.3 | 0.000000 |
| 10 | ofi_lt_p25__price_impact_lt_p10 | 91.3 | 0.000000 |

### Coverage

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_gt_p50__aggression_ratio_gt_p50 | 86.7 | 1.000000 |
| 2 | ofi_gt_p50__aggression_ratio_gt_p75 | 86.7 | 1.000000 |
| 3 | ofi_gt_p50__aggression_ratio_gt_p90 | 86.7 | 1.000000 |
| 4 | ofi_lt_p50__aggression_ratio_gt_p50 | 86.7 | 1.000000 |
| 5 | ofi_lt_p50__aggression_ratio_lt_p50 | 86.7 | 1.000000 |
| 6 | ofi_lt_p50__aggression_ratio_lt_p25 | 86.7 | 1.000000 |
| 7 | ofi_gt_p75__aggression_ratio_gt_p50 | 86.7 | 1.000000 |
| 8 | ofi_gt_p75__aggression_ratio_gt_p75 | 86.7 | 1.000000 |
| 9 | ofi_gt_p75__aggression_ratio_gt_p90 | 86.7 | 1.000000 |
| 10 | ofi_lt_p25__aggression_ratio_lt_p50 | 86.7 | 1.000000 |

### Trade Count

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_gt_p50__turnover_imbalance_gt_p50 | 100.0 | 1696.000000 |
| 2 | aggression_ratio_gt_p50__turnover_imbalance_gt_p50 | 99.9 | 1450.000000 |
| 3 | ofi_gt_p50__aggression_ratio_gt_p50 | 99.8 | 1449.000000 |
| 4 | ofi_lt_p50__turnover_imbalance_lt_p50 | 99.7 | 1342.000000 |
| 5 | aggression_ratio_gt_p50__duration_us_gt_p50 | 99.6 | 1301.000000 |
| 6 | ofi_gt_p50__duration_us_gt_p50 | 99.5 | 1257.000000 |
| 7 | turnover_imbalance_gt_p50__duration_us_gt_p50 | 99.5 | 1257.000000 |
| 8 | price_impact_gt_p50__volume_per_trade_lt_p50 | 99.3 | 1239.000000 |
| 9 | volume_per_trade_lt_p50__duration_us_gt_p50 | 99.2 | 1100.000000 |
| 10 | aggression_ratio_lt_p50__aggregation_density_gt_p50 | 99.1 | 1090.000000 |

### Kelly

| Rank | Config ID | Percentile | Raw Value |
|------|-----------|------------|-----------|
| 1 | ofi_gt_p75__aggression_ratio_lt_p25 | 99.9 | 0.623787 |
| 2 | aggression_ratio_lt_p25__turnover_imbalance_gt_p75 | 99.9 | 0.623787 |
| 3 | ofi_gt_p90__vwap_close_deviation_gt_p90 | 99.7 | 0.436287 |
| 4 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p90 | 99.7 | 0.436287 |
| 5 | ofi_gt_p75__vwap_close_deviation_gt_p90 | 99.5 | 0.306946 |
| 6 | turnover_imbalance_gt_p75__vwap_close_deviation_gt_p90 | 99.5 | 0.306946 |
| 7 | ofi_gt_p50__aggression_ratio_lt_p25 | 99.3 | 0.282661 |
| 8 | aggression_ratio_lt_p25__turnover_imbalance_gt_p50 | 99.3 | 0.282661 |
| 9 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p90 | 99.2 | 0.274194 |
| 10 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 99.0 | 0.271151 |

## 4. Tightening Analysis (Uniform Cutoffs)

| Cutoff | Intersection Size | Example Survivor |
|--------|-------------------|------------------|
| 100% | 1008 | aggregation_density_gt_p50__duration_us_gt_p50 |
| 80% | 132 | aggregation_density_gt_p75__duration_us_gt_p50 |
| 60% | 6 | aggression_ratio_gt_p90__price_impact_lt_p50 |
| 40% | 0 | - |
| 20% | 0 | - |
| 10% | 0 | - |
| 5% | 0 | - |

## 5. Evolutionary Search Ready

Current cutoffs as env vars:

```bash
RBP_RANK_CUT_COVERAGE=85 RBP_RANK_CUT_DSR=95 RBP_RANK_CUT_EVALUE=95 RBP_RANK_CUT_HEADROOM=25 RBP_RANK_CUT_KELLY=35 RBP_RANK_CUT_OMEGA=70 RBP_RANK_CUT_OU_RATIO=60 RBP_RANK_CUT_RACHEV=90 RBP_RANK_CUT_REGULARITY_CV=65 RBP_RANK_CUT_SL_CDAR=50 RBP_RANK_CUT_TAMRS=30 mise run eval:rank
```

