# Lenient 5-Metric Screening -- Forensic Report

## 1. Metric Distribution Summary (All Configs)

| Metric | Min | P10 | P25 | P50 | P75 | P90 | Max |
|--------|-----|-----|-----|-----|-----|-----|-----|
| Omega | 0.0 | 0.84058 | 0.940096 | 1.016461 | 1.083001 | 1.2 | 5.942338 |
| DSR | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| MinBTL Headroom | 0.0 | 0.0002 | 0.0023 | 0.0165 | 0.052325 | 0.125 | 0.4706 |
| N Trades | 0.0 | 21.0 | 79.75 | 189.0 | 363.0 | 656.3 | 1696.0 |
| TAMRS | 0.008538 | 0.019623 | 0.026354 | 0.039804 | 0.062571 | 0.088418 | 0.379308 |
| Rachev | 1.799281 | 1.946922 | 1.970233 | 1.993552 | 2.0 | 2.0 | 2.0 |
| Regularity CV | 0.0 | 0.0 | 0.064103 | 0.244019 | 0.406689 | 0.581773 | 1.007334 |
| Coverage | 0.2 | 0.55 | 0.7 | 0.85 | 1.0 | 1.0 | 1.0 |

## 2. Tier1 Exploratory

**Thresholds**: Omega > 1.0, DSR > -1.0, MinBTL headroom > 0.01, n_trades >= 30, regularity_cv < 999.0, coverage >= 0.0

### Funnel (individual gate pass rates)

| Gate | Pass | Fail | % Pass |
|------|------|------|--------|
| omega | 533 | 475 | 52.9% |
| dsr | 961 | 47 | 95.3% |
| headroom | 584 | 424 | 57.9% |
| n_trades | 893 | 115 | 88.6% |
| tamrs | 914 | 94 | 90.7% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 976 | 32 | 96.8% |
| regularity_cv | 896 | 112 | 88.9% |
| temporal_coverage | 1008 | 0 | 100.0% |
| **ALL gates** | **298** | **710** | **29.6%** |

### Binding Constraint: **omega** (kills 221 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | TAMRS | Omega | DSR | Headroom | Reg CV | Coverage | N | Score |
|------|-----------|-------|-------|-----|----------|--------|----------|---|-------|
| 1 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.2635 | 2.1152 | 0.000000 | 0.3198 | 0.0376 | 0.85 | 35 | 0.7673 |
| 2 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.1979 | 2.1152 | 0.000000 | 0.3198 | 0.0376 | 0.85 | 35 | 0.6633 |
| 3 | turnover_imbalance_gt_p90__price_impact_gt_p75 | 0.2304 | 1.6615 | 0.000000 | 0.1891 | 0.4416 | 0.70 | 46 | 0.5616 |
| 4 | ofi_gt_p90__price_impact_gt_p75 | 0.2298 | 1.6615 | 0.000000 | 0.1891 | 0.4416 | 0.70 | 46 | 0.5606 |
| 5 | vwap_close_deviation_lt_p10__duration_us_gt_p90 | 0.2351 | 1.2000 | 0.000000 | 0.0168 | 0.0000 | 0.60 | 32 | 0.4046 |
| 6 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1299 | 1.5052 | 0.000000 | 0.3551 | 0.2510 | 0.90 | 130 | 0.3953 |
| 7 | ofi_gt_p75__price_impact_gt_p75 | 0.1215 | 1.5052 | 0.000000 | 0.3551 | 0.2510 | 0.90 | 130 | 0.3819 |
| 8 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.1209 | 1.4493 | 0.000000 | 0.1550 | 0.3813 | 0.80 | 69 | 0.3220 |
| 9 | price_impact_lt_p10__vwap_close_deviation_lt_p10 | 0.1863 | 1.1515 | 0.000000 | 0.0165 | 0.0714 | 0.60 | 52 | 0.3137 |
| 10 | volume_per_trade_lt_p10__aggregation_density_lt_p1 | 0.1137 | 1.4075 | 0.000000 | 0.1205 | 0.0000 | 0.50 | 66 | 0.2917 |
| 11 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.1006 | 1.4140 | 0.000000 | 0.2060 | 0.0000 | 0.80 | 105 | 0.2912 |
| 12 | aggression_ratio_gt_p75__vwap_close_deviation_gt_p | 0.1611 | 1.2010 | 0.000000 | 0.0318 | 0.0926 | 0.80 | 60 | 0.2908 |
| 13 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.0983 | 1.3707 | 0.000000 | 0.2672 | 0.3036 | 1.00 | 164 | 0.2890 |
| 14 | vwap_close_deviation_gt_p90__aggregation_density_l | 0.1153 | 1.3665 | 0.000000 | 0.1469 | 0.1053 | 0.75 | 95 | 0.2886 |
| 15 | turnover_imbalance_gt_p50__vwap_close_deviation_gt | 0.1240 | 1.3572 | 0.000000 | 0.0766 | 0.1800 | 0.80 | 51 | 0.2847 |
| 16 | ofi_gt_p90__duration_us_lt_p50 | 0.0934 | 1.4557 | 0.000000 | 0.1688 | 0.3386 | 0.90 | 74 | 0.2832 |
| 17 | turnover_imbalance_gt_p90__aggregation_density_gt_ | 0.1557 | 1.2000 | 0.000000 | 0.0212 | 0.1483 | 0.60 | 40 | 0.2796 |
| 18 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.0910 | 1.4140 | 0.000000 | 0.1368 | 0.3813 | 0.80 | 70 | 0.2610 |
| 19 | aggression_ratio_gt_p90__duration_us_gt_p90 | 0.1055 | 1.3158 | 0.000000 | 0.1549 | 0.6585 | 0.85 | 126 | 0.2609 |
| 20 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0648 | 1.2913 | 0.000000 | 0.4706 | 0.3301 | 1.00 | 440 | 0.2581 |

## 2. Tier2 Balanced

**Thresholds**: Omega > 1.02, DSR > -1.0, MinBTL headroom > 0.05, n_trades >= 50, regularity_cv < 0.8, coverage >= 0.5

### Funnel (individual gate pass rates)

| Gate | Pass | Fail | % Pass |
|------|------|------|--------|
| omega | 465 | 543 | 46.1% |
| dsr | 961 | 47 | 95.3% |
| headroom | 260 | 748 | 25.8% |
| n_trades | 834 | 174 | 82.7% |
| tamrs | 332 | 676 | 32.9% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 971 | 37 | 96.3% |
| regularity_cv | 887 | 121 | 88.0% |
| temporal_coverage | 884 | 124 | 87.7% |
| **ALL gates** | **69** | **939** | **6.8%** |

### Binding Constraint: **headroom** (kills 94 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | TAMRS | Omega | DSR | Headroom | Reg CV | Coverage | N | Score |
|------|-----------|-------|-------|-----|----------|--------|----------|---|-------|
| 1 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1299 | 1.5052 | 0.000000 | 0.3551 | 0.2510 | 0.90 | 130 | 0.7725 |
| 2 | ofi_gt_p75__price_impact_gt_p75 | 0.1215 | 1.5052 | 0.000000 | 0.3551 | 0.2510 | 0.90 | 130 | 0.7293 |
| 3 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.1209 | 1.4493 | 0.000000 | 0.1550 | 0.3813 | 0.80 | 69 | 0.6373 |
| 4 | turnover_imbalance_gt_p50__vwap_close_deviation_gt | 0.1240 | 1.3572 | 0.000000 | 0.0766 | 0.1800 | 0.80 | 51 | 0.5678 |
| 5 | volume_per_trade_lt_p10__aggregation_density_lt_p1 | 0.1137 | 1.4075 | 0.000000 | 0.1205 | 0.0000 | 0.50 | 66 | 0.5619 |
| 6 | vwap_close_deviation_gt_p90__aggregation_density_l | 0.1153 | 1.3665 | 0.000000 | 0.1469 | 0.1053 | 0.75 | 95 | 0.5462 |
| 7 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.1006 | 1.4140 | 0.000000 | 0.2060 | 0.0000 | 0.80 | 105 | 0.5192 |
| 8 | ofi_gt_p90__duration_us_lt_p50 | 0.0934 | 1.4557 | 0.000000 | 0.1688 | 0.3386 | 0.90 | 74 | 0.5039 |
| 9 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.0983 | 1.3707 | 0.000000 | 0.2672 | 0.3036 | 1.00 | 164 | 0.4905 |
| 10 | volume_per_trade_lt_p10__aggregation_density_lt_p2 | 0.1131 | 1.2804 | 0.000000 | 0.1036 | 0.0000 | 0.55 | 107 | 0.4616 |
| 11 | aggression_ratio_gt_p90__duration_us_gt_p90 | 0.1055 | 1.3158 | 0.000000 | 0.1549 | 0.6585 | 0.85 | 126 | 0.4607 |
| 12 | ofi_gt_p50__vwap_close_deviation_gt_p90 | 0.1125 | 1.2907 | 0.000000 | 0.0522 | 0.1800 | 0.80 | 50 | 0.4539 |
| 13 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.0910 | 1.4140 | 0.000000 | 0.1368 | 0.3813 | 0.80 | 70 | 0.4535 |
| 14 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 0.0828 | 1.4219 | 0.000000 | 0.1501 | 0.3386 | 0.90 | 75 | 0.4203 |
| 15 | turnover_imbalance_lt_p25__aggregation_density_lt_ | 0.1130 | 1.2045 | 0.000000 | 0.0734 | 0.0818 | 0.85 | 137 | 0.3988 |
| 16 | price_impact_lt_p25__aggregation_density_lt_p25 | 0.0742 | 1.4359 | 0.000000 | 0.1429 | 0.2908 | 0.85 | 67 | 0.3845 |
| 17 | vwap_close_deviation_gt_p90__aggregation_density_l | 0.0987 | 1.2495 | 0.000000 | 0.0895 | 0.0992 | 0.75 | 114 | 0.3619 |
| 18 | price_impact_gt_p90__aggregation_density_lt_p25 | 0.0932 | 1.2395 | 0.000000 | 0.1297 | 0.2876 | 0.85 | 180 | 0.3357 |
| 19 | ofi_gt_p90__price_impact_lt_p10 | 0.0950 | 1.2340 | 0.000000 | 0.0543 | 0.0000 | 0.70 | 76 | 0.3231 |
| 20 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.0813 | 1.2953 | 0.000000 | 0.1357 | 0.2000 | 1.00 | 125 | 0.3165 |

## 2. Tier3 Strict

**Thresholds**: Omega > 1.05, DSR > -1.0, MinBTL headroom > 0.1, n_trades >= 100, regularity_cv < 0.5, coverage >= 0.7

### Funnel (individual gate pass rates)

| Gate | Pass | Fail | % Pass |
|------|------|------|--------|
| omega | 336 | 672 | 33.3% |
| dsr | 961 | 47 | 95.3% |
| headroom | 128 | 880 | 12.7% |
| n_trades | 700 | 308 | 69.4% |
| tamrs | 18 | 990 | 1.8% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 17 | 991 | 1.7% |
| regularity_cv | 751 | 257 | 74.5% |
| temporal_coverage | 738 | 270 | 73.2% |
| **ALL gates** | **0** | **1008** | **0.0%** |

### Binding Constraint: **omega** (kills 0 configs that pass other 4 gates)

**No configs pass all gates at this tier.**

## 3. Near-Miss Analysis (Tier 2 -- fail exactly 1 gate)

**172 configs** fail exactly 1 gate at Tier 2:

| Failed Gate | Count |
|-------------|-------|
| headroom | 94 |
| tamrs | 59 |
| n_trades | 10 |
| omega | 5 |
| regularity_cv | 3 |
| temporal_coverage | 1 |

### Top 10 Near-Misses (by TAMRS)

| Config ID | TAMRS | Omega | DSR | Headroom | Reg CV | Cov | N | Failed Gate |
|-----------|-------|-------|-----|----------|--------|-----|---|-------------|
| ofi_gt_p50__aggression_ratio_lt_p25 | 0.3502 | 2.1721 | 0.000000 | 0.2024 | 0.0000 | 0.55 | 21 | n_trades |
| ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.2635 | 2.1152 | 0.000000 | 0.3198 | 0.0376 | 0.85 | 35 | n_trades |
| aggression_ratio_lt_p50__turnover_imbalance_g | 0.2489 | 1.4976 | 0.000000 | 0.0541 | 0.0000 | 0.55 | 21 | n_trades |
| aggression_ratio_lt_p25__turnover_imbalance_g | 0.2420 | 2.1721 | 0.000000 | 0.2024 | 0.0000 | 0.55 | 21 | n_trades |
| turnover_imbalance_gt_p90__price_impact_gt_p7 | 0.2304 | 1.6615 | 0.000000 | 0.1891 | 0.4416 | 0.70 | 46 | n_trades |
| ofi_gt_p90__price_impact_gt_p75 | 0.2298 | 1.6615 | 0.000000 | 0.1891 | 0.4416 | 0.70 | 46 | n_trades |
| turnover_imbalance_gt_p90__vwap_close_deviati | 0.1979 | 2.1152 | 0.000000 | 0.3198 | 0.0376 | 0.85 | 35 | n_trades |
| ofi_gt_p90__aggression_ratio_lt_p50 | 0.1867 | 1.4976 | 0.000000 | 0.0541 | 0.0000 | 0.55 | 21 | n_trades |
| price_impact_lt_p10__vwap_close_deviation_lt_ | 0.1863 | 1.1515 | 0.000000 | 0.0165 | 0.0714 | 0.60 | 52 | headroom |
| aggression_ratio_gt_p75__vwap_close_deviation | 0.1611 | 1.2010 | 0.000000 | 0.0318 | 0.0926 | 0.80 | 60 | headroom |

## 4. Summary

| Tier | Pass | % | Binding Constraint |
|------|------|---|-------------------|
| Tier1 Exploratory | 298 | 29.6% | omega |
| Tier2 Balanced | 69 | 6.8% | headroom |
| Tier3 Strict | 0 | 0.0% | omega |
