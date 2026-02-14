# Per-Metric Percentile Ranking Report

## 1. Cutoffs Applied

| Metric | Cutoff (top X%) | Configs Passing |
|--------|-----------------|-----------------|
| TAMRS | 20% | 183 |
| Rachev | 100% | 1008 |
| OU Ratio | 100% | 1008 |
| SL/CDaR | 100% | 1008 |
| Omega | 30% | 289 |
| DSR | 100% | 1008 |
| MinBTL Headroom | 100% | 1008 |
| E-value | 100% | 1008 |
| Regularity CV | 100% | 1008 |
| Coverage | 100% | 1008 |
| Trade Count | 100% | 1008 |
| Kelly | 100% | 1008 |

**Intersection (pass ALL cutoffs)**: 110 / 1008 configs

## 2. Intersection Configs

| Rank | Config ID | Avg Pct | TAMRS | Rachev | OU Ratio | SL/CDaR | Omega | DSR | MinBTL Headroom | E-value | Regularity CV | Coverage | Trade Count | Kelly |
|------|-----------|---------|-------|--------|----------|---------|-------|-----|-----------------|---------|---------------|----------|-------------|-------|
| 1 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p50 | 74.7 | 87.5 | 49.9 | 68.4 | 84.1 | 94.3 | 49.9 | 91.2 | 95.9 | 58.0 | 86.7 | 36.3 | 94.3 |
| 2 | price_impact_lt_p50__aggregation_density_lt_p25 | 74.4 | 93.5 | 85.3 | 11.0 | 92.3 | 95.4 | 49.9 | 97.9 | 98.8 | 39.5 | 86.7 | 46.0 | 96.6 |
| 3 | volume_per_trade_gt_p75__aggregation_density_lt_p25 | 74.2 | 94.1 | 66.7 | 41.2 | 91.7 | 95.8 | 49.9 | 96.3 | 97.6 | 91.3 | 37.1 | 32.0 | 96.2 |
| 4 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 73.2 | 99.8 | 19.3 | 76.3 | 98.9 | 98.9 | 49.9 | 99.0 | 99.5 | 78.6 | 45.6 | 13.1 | 99.0 |
| 5 | turnover_imbalance_gt_p90__vwap_close_deviation_gt_p75 | 73.0 | 99.1 | 19.3 | 76.3 | 97.9 | 98.9 | 49.9 | 99.0 | 99.5 | 78.6 | 45.6 | 13.1 | 99.0 |
| 6 | aggression_ratio_gt_p90__duration_us_gt_p90 | 72.9 | 94.6 | 85.3 | 83.9 | 91.2 | 94.7 | 49.9 | 93.4 | 97.4 | 6.1 | 45.6 | 36.7 | 96.4 |
| 7 | turnover_imbalance_lt_p25__price_impact_lt_p25 | 72.7 | 86.4 | 85.3 | 55.0 | 83.6 | 92.0 | 49.9 | 86.8 | 93.0 | 91.3 | 18.3 | 38.2 | 92.4 |
| 8 | ofi_gt_p90__price_impact_lt_p10 | 72.6 | 92.7 | 85.3 | 60.3 | 89.2 | 91.8 | 49.9 | 75.8 | 91.6 | 91.3 | 24.8 | 24.0 | 94.5 |
| 9 | ofi_gt_p90__aggregation_density_gt_p50 | 72.4 | 82.9 | 85.3 | 82.1 | 78.0 | 89.9 | 49.9 | 79.3 | 91.2 | 38.2 | 65.1 | 35.2 | 92.1 |
| 10 | ofi_gt_p90__price_impact_lt_p25 | 71.5 | 90.0 | 85.3 | 52.8 | 87.5 | 84.6 | 49.9 | 69.2 | 90.5 | 53.9 | 65.1 | 38.5 | 91.0 |
| 11 | turnover_imbalance_gt_p90__price_impact_lt_p10 | 71.3 | 89.5 | 85.3 | 55.7 | 86.8 | 91.3 | 49.9 | 71.8 | 90.8 | 91.3 | 24.8 | 24.3 | 93.9 |
| 12 | aggregation_density_lt_p25__duration_us_gt_p90 | 71.2 | 89.7 | 85.3 | 80.3 | 85.6 | 90.2 | 49.9 | 67.3 | 89.8 | 91.3 | 9.9 | 20.6 | 93.8 |
| 13 | ofi_gt_p50__price_impact_gt_p75 | 70.9 | 85.8 | 35.8 | 15.0 | 85.9 | 91.9 | 49.9 | 96.5 | 96.7 | 48.8 | 86.7 | 67.3 | 90.4 |
| 14 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 70.8 | 97.4 | 49.9 | 22.6 | 96.3 | 96.9 | 49.9 | 99.6 | 99.2 | 49.2 | 53.8 | 37.8 | 96.7 |
| 15 | ofi_gt_p75__price_impact_gt_p75 | 70.7 | 96.9 | 49.9 | 22.6 | 95.4 | 96.9 | 49.9 | 99.6 | 99.2 | 49.2 | 53.8 | 37.8 | 96.8 |
| 16 | vwap_close_deviation_gt_p90__duration_us_gt_p75 | 70.2 | 98.2 | 85.3 | 56.6 | 97.1 | 97.3 | 49.9 | 80.6 | 94.4 | 61.9 | 13.2 | 10.3 | 97.9 |
| 17 | turnover_imbalance_gt_p90__aggregation_density_gt_p75 | 69.9 | 98.1 | 85.3 | 91.3 | 96.5 | 90.2 | 49.9 | 56.5 | 86.9 | 63.1 | 13.2 | 14.8 | 93.4 |
| 18 | price_impact_lt_p10__vwap_close_deviation_lt_p10 | 69.8 | 98.7 | 85.3 | 89.2 | 97.7 | 85.7 | 49.9 | 50.0 | 85.5 | 72.8 | 13.2 | 18.0 | 91.7 |
| 19 | ofi_gt_p90__aggregation_density_gt_p75 | 69.8 | 97.7 | 85.3 | 91.3 | 94.8 | 90.2 | 49.9 | 56.5 | 86.9 | 63.1 | 13.2 | 14.8 | 93.5 |
| 20 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 68.9 | 96.7 | 38.7 | 76.3 | 94.2 | 96.3 | 49.9 | 93.5 | 97.5 | 27.8 | 37.1 | 21.9 | 97.4 |
| 21 | aggression_ratio_lt_p25__price_impact_lt_p25 | 68.8 | 81.3 | 49.3 | 76.9 | 76.8 | 90.5 | 49.9 | 81.2 | 90.9 | 91.3 | 7.2 | 39.6 | 90.2 |
| 22 | aggression_ratio_gt_p50__aggregation_density_gt_p75 | 68.5 | 87.1 | 85.3 | 63.8 | 83.6 | 84.5 | 49.9 | 77.7 | 92.5 | 6.7 | 45.6 | 54.2 | 90.8 |
| 23 | aggression_ratio_gt_p75__price_impact_gt_p75 | 68.4 | 92.3 | 85.3 | 13.7 | 91.6 | 90.9 | 49.9 | 83.9 | 75.0 | 55.7 | 65.1 | 42.9 | 74.3 |
| 24 | aggression_ratio_lt_p10__vwap_close_deviation_lt_p50 | 68.3 | 87.7 | 44.4 | 96.8 | 76.9 | 89.1 | 49.9 | 70.3 | 88.3 | 46.0 | 53.8 | 27.1 | 89.8 |
| 25 | ofi_gt_p90__duration_us_lt_p50 | 68.3 | 92.0 | 38.7 | 54.1 | 89.2 | 96.4 | 49.9 | 94.3 | 96.8 | 34.4 | 53.8 | 23.5 | 96.3 |
| 26 | turnover_imbalance_lt_p25__vwap_close_deviation_lt_p25 | 68.2 | 90.5 | 48.4 | 73.2 | 86.5 | 78.7 | 49.9 | 57.2 | 85.2 | 36.6 | 86.7 | 39.4 | 86.5 |
| 27 | ofi_gt_p75__aggression_ratio_lt_p50 | 68.2 | 91.0 | 38.7 | 83.1 | 86.8 | 95.7 | 49.9 | 91.5 | 97.1 | 27.8 | 37.1 | 22.2 | 97.1 |
| 28 | ofi_gt_p75__aggregation_density_gt_p75 | 68.1 | 81.7 | 85.3 | 47.6 | 79.6 | 93.0 | 49.9 | 83.1 | 95.1 | 31.2 | 45.6 | 29.7 | 95.0 |
| 29 | ofi_gt_p50__aggression_ratio_lt_p25 | 68.0 | 99.9 | 0.5 | 62.1 | 99.6 | 99.2 | 49.9 | 96.0 | 98.6 | 91.3 | 9.9 | 9.9 | 99.3 |
| 30 | aggression_ratio_lt_p25__turnover_imbalance_gt_p50 | 67.9 | 99.6 | 0.5 | 62.1 | 98.7 | 99.2 | 49.9 | 96.0 | 98.6 | 91.3 | 9.9 | 9.9 | 99.3 |
| 31 | volume_per_trade_gt_p90__aggregation_density_lt_p25 | 67.8 | 98.6 | 85.3 | 68.6 | 97.6 | 98.1 | 49.9 | 98.6 | 99.1 | 0.0 | 4.9 | 14.8 | 98.2 |
| 32 | turnover_imbalance_lt_p10__aggregation_density_gt_p90 | 67.5 | 89.1 | 16.5 | 83.5 | 85.0 | 80.7 | 49.9 | 63.6 | 81.8 | 82.0 | 53.8 | 41.8 | 81.9 |
| 33 | ofi_lt_p25__duration_us_lt_p10 | 67.4 | 94.0 | 26.1 | 77.2 | 89.8 | 86.0 | 49.9 | 79.8 | 75.2 | 74.6 | 65.1 | 53.9 | 37.4 |
| 34 | ofi_lt_p25__vwap_close_deviation_lt_p25 | 67.4 | 85.2 | 48.4 | 73.2 | 81.4 | 78.7 | 49.9 | 57.2 | 85.2 | 36.6 | 86.7 | 39.4 | 86.6 |
| 35 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 67.1 | 88.0 | 38.7 | 51.2 | 85.6 | 95.9 | 49.9 | 92.8 | 96.0 | 34.4 | 53.8 | 23.8 | 95.4 |
| 36 | price_impact_lt_p50__duration_us_lt_p50 | 67.1 | 82.2 | 48.8 | 42.6 | 80.0 | 88.8 | 49.9 | 97.6 | 98.2 | 2.3 | 37.1 | 86.8 | 90.9 |
| 37 | turnover_imbalance_gt_p90__price_impact_gt_p75 | 67.1 | 99.3 | 30.9 | 78.0 | 98.6 | 97.9 | 49.9 | 95.1 | 95.7 | 22.7 | 24.8 | 16.0 | 95.8 |
| 38 | turnover_imbalance_lt_p10__vwap_close_deviation_lt_p50 | 67.1 | 94.9 | 44.4 | 69.2 | 92.0 | 91.1 | 49.9 | 73.6 | 90.0 | 44.6 | 37.1 | 26.7 | 91.3 |
| 39 | ofi_gt_p90__price_impact_gt_p75 | 67.0 | 99.2 | 30.9 | 78.0 | 98.5 | 97.9 | 49.9 | 95.1 | 95.7 | 22.7 | 24.8 | 16.0 | 95.7 |
| 40 | price_impact_lt_p25__aggregation_density_lt_p25 | 67.0 | 84.1 | 85.3 | 7.6 | 85.6 | 96.1 | 49.9 | 91.9 | 97.2 | 42.1 | 45.6 | 21.3 | 97.3 |
| 41 | turnover_imbalance_lt_p25__duration_us_lt_p10 | 66.5 | 88.7 | 26.1 | 77.2 | 84.7 | 86.0 | 49.9 | 79.8 | 75.2 | 74.6 | 65.1 | 53.9 | 37.4 |
| 42 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p90 | 66.0 | 100.0 | 85.3 | 35.2 | 99.8 | 99.1 | 49.9 | 98.4 | 99.4 | 0.0 | 13.2 | 12.1 | 99.2 |
| 43 | vwap_close_deviation_lt_p10__duration_us_gt_p90 | 65.2 | 99.5 | 85.3 | 10.1 | 99.3 | 90.2 | 49.9 | 51.3 | 86.1 | 91.3 | 13.2 | 12.5 | 93.7 |
| 44 | aggression_ratio_lt_p50__turnover_imbalance_gt_p90 | 64.9 | 99.7 | 19.3 | 37.1 | 99.3 | 96.5 | 49.9 | 75.6 | 92.5 | 91.3 | 9.9 | 9.9 | 97.5 |
| 45 | turnover_imbalance_gt_p50__vwap_close_deviation_gt_p90 | 64.8 | 97.2 | 18.1 | 36.3 | 95.8 | 95.2 | 49.9 | 82.1 | 92.3 | 60.4 | 37.1 | 17.7 | 95.1 |
| 46 | ofi_gt_p90__aggression_ratio_lt_p50 | 64.7 | 98.8 | 19.3 | 37.1 | 98.2 | 96.5 | 49.9 | 75.6 | 92.5 | 91.3 | 9.9 | 9.9 | 97.5 |
| 47 | price_impact_lt_p10__aggregation_density_lt_p25 | 64.6 | 97.5 | 85.3 | 2.7 | 97.1 | 95.6 | 49.9 | 75.9 | 92.2 | 56.8 | 13.2 | 11.4 | 97.0 |
| 48 | price_impact_gt_p50__duration_us_lt_p10 | 64.6 | 92.9 | 18.9 | 82.8 | 89.0 | 88.9 | 49.9 | 86.3 | 77.5 | 32.7 | 53.8 | 54.5 | 47.3 |
| 49 | aggression_ratio_gt_p75__vwap_close_deviation_lt_p10 | 64.4 | 82.1 | 56.8 | 20.9 | 82.3 | 82.3 | 49.9 | 60.3 | 87.9 | 40.2 | 86.7 | 32.9 | 90.3 |
| 50 | aggression_ratio_gt_p75__volume_per_trade_gt_p90 | 64.4 | 87.4 | 85.3 | 76.6 | 83.6 | 81.1 | 49.9 | 38.9 | 83.2 | 79.1 | 3.2 | 14.3 | 89.7 |

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
RBP_RANK_CUT_OMEGA=30 RBP_RANK_CUT_TAMRS=20 mise run eval:rank
```

