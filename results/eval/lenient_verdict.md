# Lenient 5-Metric Screening -- Forensic Report

## 1. Metric Distribution Summary (All Configs)

| Metric | Min | P10 | P25 | P50 | P75 | P90 | Max |
|--------|-----|-----|-----|-----|-----|-----|-----|
| Kelly | -0.311348 | -0.128044 | -0.068838 | -0.030307 | -0.003448 | 0.040995 | 0.623787 |
| Omega | 0.0 | 0.84058 | 0.940096 | 1.016461 | 1.083001 | 1.2 | 5.942338 |
| DSR | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| MinBTL Headroom | 0.0 | 0.0002 | 0.0023 | 0.0165 | 0.052325 | 0.125 | 0.4706 |
| N Trades | 0.0 | 21.0 | 79.75 | 189.0 | 363.0 | 656.3 | 1696.0 |
| TAMRS | 0.008538 | 0.019623 | 0.026354 | 0.039804 | 0.062571 | 0.088418 | 0.379308 |
| Rachev | 1.799281 | 1.946922 | 1.970233 | 1.993552 | 2.0 | 2.0 | 2.0 |

## 2. Tier1 Exploratory

**Thresholds**: Kelly > 0.0, Omega > 1.0, DSR > -1.0, MinBTL headroom > 0.01, n_trades >= 30

### Funnel (individual gate pass rates)

| Gate | Pass | Fail | % Pass |
|------|------|------|--------|
| kelly | 220 | 788 | 21.8% |
| omega | 533 | 475 | 52.9% |
| dsr | 961 | 47 | 95.3% |
| headroom | 584 | 424 | 57.9% |
| n_trades | 893 | 115 | 88.6% |
| tamrs | 914 | 94 | 90.7% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 976 | 32 | 96.8% |
| **ALL gates** | **151** | **857** | **15.0%** |

### Binding Constraint: **kelly** (kills 158 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | TAMRS | Kelly | Omega | DSR | Headroom | N Trades | Score |
|------|-----------|-------|-------|-------|-----|----------|----------|-------|
| 1 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p | 0.3793 | 0.2742 | 2.1333 | 0.000000 | 0.2886 | 31 | 0.7604 |
| 2 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.2635 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | 0.6364 |
| 3 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.1979 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | 0.5651 |
| 4 | volume_per_trade_gt_p90__aggregation_density_lt_p2 | 0.1686 | 0.2091 | 1.9743 | 0.000000 | 0.3023 | 40 | 0.4913 |
| 5 | turnover_imbalance_gt_p90__price_impact_gt_p75 | 0.2304 | 0.0892 | 1.6615 | 0.000000 | 0.1891 | 46 | 0.4488 |
| 6 | ofi_gt_p90__price_impact_gt_p75 | 0.2298 | 0.0892 | 1.6615 | 0.000000 | 0.1891 | 46 | 0.4481 |
| 7 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1299 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.3333 |
| 8 | ofi_gt_p75__price_impact_gt_p75 | 0.1215 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.3241 |
| 9 | vwap_close_deviation_lt_p10__duration_us_gt_p90 | 0.2351 | 0.0625 | 1.2000 | 0.000000 | 0.0168 | 32 | 0.2910 |
| 10 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.1209 | 0.1303 | 1.4493 | 0.000000 | 0.1550 | 69 | 0.2647 |
| 11 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.1006 | 0.0939 | 1.4140 | 0.000000 | 0.2060 | 105 | 0.2441 |
| 12 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.0983 | 0.1013 | 1.3707 | 0.000000 | 0.2672 | 164 | 0.2432 |
| 13 | ofi_gt_p90__duration_us_lt_p50 | 0.0934 | 0.0942 | 1.4557 | 0.000000 | 0.1688 | 74 | 0.2395 |
| 14 | price_impact_lt_p25__vwap_close_deviation_gt_p90 | 0.0822 | 0.1427 | 1.4991 | 0.000000 | 0.1685 | 63 | 0.2391 |
| 15 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0648 | 0.0755 | 1.2913 | 0.000000 | 0.4706 | 440 | 0.2295 |
| 16 | turnover_imbalance_gt_p50__vwap_close_deviation_gt | 0.1240 | 0.0787 | 1.3572 | 0.000000 | 0.0766 | 51 | 0.2261 |
| 17 | price_impact_lt_p10__vwap_close_deviation_lt_p10 | 0.1863 | 0.0481 | 1.1515 | 0.000000 | 0.0165 | 52 | 0.2247 |
| 18 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.0910 | 0.1213 | 1.4140 | 0.000000 | 0.1368 | 70 | 0.2187 |
| 19 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 0.0828 | 0.0860 | 1.4219 | 0.000000 | 0.1501 | 75 | 0.2148 |
| 20 | aggression_ratio_gt_p90__duration_us_gt_p90 | 0.1055 | 0.0952 | 1.3158 | 0.000000 | 0.1549 | 126 | 0.2117 |

## 2. Tier2 Balanced

**Thresholds**: Kelly > 0.01, Omega > 1.02, DSR > -1.0, MinBTL headroom > 0.05, n_trades >= 50

### Funnel (individual gate pass rates)

| Gate | Pass | Fail | % Pass |
|------|------|------|--------|
| kelly | 165 | 843 | 16.4% |
| omega | 465 | 543 | 46.1% |
| dsr | 961 | 47 | 95.3% |
| headroom | 260 | 748 | 25.8% |
| n_trades | 834 | 174 | 82.7% |
| tamrs | 332 | 676 | 32.9% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 971 | 37 | 96.3% |
| **ALL gates** | **42** | **966** | **4.2%** |

### Binding Constraint: **kelly** (kills 31 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | TAMRS | Kelly | Omega | DSR | Headroom | N Trades | Score |
|------|-----------|-------|-------|-------|-----|----------|----------|-------|
| 1 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1299 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.7724 |
| 2 | ofi_gt_p75__price_impact_gt_p75 | 0.1215 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.7290 |
| 3 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.1209 | 0.1303 | 1.4493 | 0.000000 | 0.1550 | 69 | 0.6362 |
| 4 | turnover_imbalance_gt_p50__vwap_close_deviation_gt | 0.1240 | 0.0787 | 1.3572 | 0.000000 | 0.0766 | 51 | 0.5656 |
| 5 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.1006 | 0.0939 | 1.4140 | 0.000000 | 0.2060 | 105 | 0.5172 |
| 6 | ofi_gt_p90__duration_us_lt_p50 | 0.0934 | 0.0942 | 1.4557 | 0.000000 | 0.1688 | 74 | 0.5022 |
| 7 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.0983 | 0.1013 | 1.3707 | 0.000000 | 0.2672 | 164 | 0.4881 |
| 8 | price_impact_lt_p25__vwap_close_deviation_gt_p90 | 0.0822 | 0.1427 | 1.4991 | 0.000000 | 0.1685 | 63 | 0.4767 |
| 9 | aggression_ratio_gt_p90__duration_us_gt_p90 | 0.1055 | 0.0952 | 1.3158 | 0.000000 | 0.1549 | 126 | 0.4577 |
| 10 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.0910 | 0.1213 | 1.4140 | 0.000000 | 0.1368 | 70 | 0.4513 |
| 11 | ofi_gt_p50__vwap_close_deviation_gt_p90 | 0.1125 | 0.0598 | 1.2907 | 0.000000 | 0.0522 | 50 | 0.4507 |
| 12 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 0.0828 | 0.0860 | 1.4219 | 0.000000 | 0.1501 | 75 | 0.4180 |
| 13 | price_impact_lt_p25__aggregation_density_lt_p25 | 0.0742 | 0.1269 | 1.4359 | 0.000000 | 0.1429 | 67 | 0.3822 |
| 14 | ofi_gt_p90__price_impact_lt_p10 | 0.0950 | 0.0724 | 1.2340 | 0.000000 | 0.0543 | 76 | 0.3188 |
| 15 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.0813 | 0.0669 | 1.2953 | 0.000000 | 0.1357 | 125 | 0.3128 |
| 16 | price_impact_gt_p50__volume_per_trade_gt_p90 | 0.0770 | 0.0741 | 1.3439 | 0.000000 | 0.0770 | 56 | 0.3126 |
| 17 | turnover_imbalance_gt_p75__duration_us_lt_p50 | 0.0642 | 0.0917 | 1.3541 | 0.000000 | 0.3020 | 201 | 0.3080 |
| 18 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0648 | 0.0755 | 1.2913 | 0.000000 | 0.4706 | 440 | 0.3046 |
| 19 | price_impact_lt_p25__vwap_close_deviation_gt_p75 | 0.0745 | 0.0844 | 1.3068 | 0.000000 | 0.1897 | 163 | 0.2989 |
| 20 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p | 0.0769 | 0.0792 | 1.3117 | 0.000000 | 0.1136 | 95 | 0.2970 |

## 2. Tier3 Strict

**Thresholds**: Kelly > 0.05, Omega > 1.05, DSR > -1.0, MinBTL headroom > 0.1, n_trades >= 100

### Funnel (individual gate pass rates)

| Gate | Pass | Fail | % Pass |
|------|------|------|--------|
| kelly | 78 | 930 | 7.7% |
| omega | 336 | 672 | 33.3% |
| dsr | 961 | 47 | 95.3% |
| headroom | 128 | 880 | 12.7% |
| n_trades | 700 | 308 | 69.4% |
| tamrs | 18 | 990 | 1.8% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 17 | 991 | 1.7% |
| **ALL gates** | **0** | **1008** | **0.0%** |

### Binding Constraint: **kelly** (kills 0 configs that pass other 4 gates)

**No configs pass all gates at this tier.**

## 3. Near-Miss Analysis (Tier 2 -- fail exactly 1 gate)

**99 configs** fail exactly 1 gate at Tier 2:

| Failed Gate | Count |
|-------------|-------|
| kelly | 31 |
| tamrs | 31 |
| headroom | 24 |
| n_trades | 13 |

### Top 10 Near-Misses (by Kelly)

| Config ID | Kelly | Omega | DSR | Headroom | N | Failed Gate |
|-----------|-------|-------|-----|----------|---|-------------|
| aggression_ratio_lt_p25__turnover_imbalance_g | 0.2827 | 2.1721 | 0.000000 | 0.2024 | 21 | n_trades |
| ofi_gt_p50__aggression_ratio_lt_p25 | 0.2827 | 2.1721 | 0.000000 | 0.2024 | 21 | n_trades |
| vwap_close_deviation_lt_p10__volume_per_trade | 0.2742 | 2.1333 | 0.000000 | 0.2886 | 31 | n_trades |
| ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | n_trades |
| turnover_imbalance_gt_p90__vwap_close_deviati | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | n_trades |
| volume_per_trade_gt_p90__aggregation_density_ | 0.2091 | 1.9743 | 0.000000 | 0.3023 | 40 | n_trades |
| vwap_close_deviation_gt_p90__duration_us_gt_p | 0.1522 | 1.5385 | 0.000000 | 0.0677 | 23 | n_trades |
| aggression_ratio_lt_p50__turnover_imbalance_g | 0.1424 | 1.4976 | 0.000000 | 0.0541 | 21 | n_trades |
| ofi_gt_p90__aggression_ratio_lt_p50 | 0.1424 | 1.4976 | 0.000000 | 0.0541 | 21 | n_trades |
| price_impact_lt_p10__aggregation_density_lt_p | 0.1207 | 1.4118 | 0.000000 | 0.0550 | 29 | n_trades |

## 4. Summary

| Tier | Pass | % | Binding Constraint |
|------|------|---|-------------------|
| Tier1 Exploratory | 151 | 15.0% | kelly |
| Tier2 Balanced | 42 | 4.2% | kelly |
| Tier3 Strict | 0 | 0.0% | kelly |
