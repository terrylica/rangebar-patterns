# Lenient 5-Metric Screening -- Forensic Report

## 1. Metric Distribution Summary (All Configs)

| Metric | Min | P10 | P25 | P50 | P75 | P90 | Max |
|--------|-----|-----|-----|-----|-----|-----|-----|
| Kelly | -0.311348 | -0.128044 | -0.068838 | -0.030307 | -0.003448 | 0.040995 | 0.623787 |
| Omega | 0.0 | 0.84058 | 0.940096 | 1.016461 | 1.083001 | 1.2 | 5.942338 |
| DSR | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| MinBTL Headroom | 0.0 | 0.0002 | 0.0023 | 0.0165 | 0.052325 | 0.125 | 0.4706 |
| N Trades | 0.0 | 21.0 | 79.75 | 189.0 | 363.0 | 656.3 | 1696.0 |
| TAMRS | 0.000492 | 0.00108 | 0.001469 | 0.00221 | 0.003374 | 0.00484 | 0.021395 |
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
| ou_ratio | 1008 | 0 | 100.0% |
| **ALL gates** | **151** | **857** | **15.0%** |

### Binding Constraint: **kelly** (kills 158 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | TAMRS | Kelly | Omega | DSR | Headroom | N Trades | Score |
|------|-----------|-------|-------|-------|-----|----------|----------|-------|
| 1 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p | 0.0214 | 0.2742 | 2.1333 | 0.000000 | 0.2886 | 31 | 0.7604 |
| 2 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.0139 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | 0.6178 |
| 3 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.0104 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | 0.5511 |
| 4 | volume_per_trade_gt_p90__aggregation_density_lt_p2 | 0.0090 | 0.2091 | 1.9743 | 0.000000 | 0.3023 | 40 | 0.4811 |
| 5 | turnover_imbalance_gt_p90__price_impact_gt_p75 | 0.0121 | 0.0892 | 1.6615 | 0.000000 | 0.1891 | 46 | 0.4315 |
| 6 | ofi_gt_p90__price_impact_gt_p75 | 0.0121 | 0.0892 | 1.6615 | 0.000000 | 0.1891 | 46 | 0.4309 |
| 7 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.0075 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.3368 |
| 8 | ofi_gt_p75__price_impact_gt_p75 | 0.0070 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.3275 |
| 9 | vwap_close_deviation_lt_p10__duration_us_gt_p90 | 0.0143 | 0.0625 | 1.2000 | 0.000000 | 0.0168 | 32 | 0.3102 |
| 10 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.0064 | 0.1303 | 1.4493 | 0.000000 | 0.1550 | 69 | 0.2560 |
| 11 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.0059 | 0.1013 | 1.3707 | 0.000000 | 0.2672 | 164 | 0.2499 |
| 12 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.0056 | 0.0939 | 1.4140 | 0.000000 | 0.2060 | 105 | 0.2430 |
| 13 | price_impact_lt_p25__vwap_close_deviation_gt_p90 | 0.0047 | 0.1427 | 1.4991 | 0.000000 | 0.1685 | 63 | 0.2405 |
| 14 | ofi_gt_p90__duration_us_lt_p50 | 0.0051 | 0.0942 | 1.4557 | 0.000000 | 0.1688 | 74 | 0.2361 |
| 15 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0039 | 0.0755 | 1.2913 | 0.000000 | 0.4706 | 440 | 0.2337 |
| 16 | turnover_imbalance_gt_p50__vwap_close_deviation_gt | 0.0070 | 0.0787 | 1.3572 | 0.000000 | 0.0766 | 51 | 0.2257 |
| 17 | price_impact_lt_p25__aggregation_density_lt_p25 | 0.0046 | 0.1269 | 1.4359 | 0.000000 | 0.1429 | 67 | 0.2151 |
| 18 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 0.0046 | 0.0860 | 1.4219 | 0.000000 | 0.1501 | 75 | 0.2123 |
| 19 | turnover_imbalance_gt_p75__duration_us_lt_p50 | 0.0037 | 0.0917 | 1.3541 | 0.000000 | 0.3020 | 201 | 0.2107 |
| 20 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.0047 | 0.1213 | 1.4140 | 0.000000 | 0.1368 | 70 | 0.2105 |

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
| tamrs | 0 | 1008 | 0.0% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 0 | 1008 | 0.0% |
| **ALL gates** | **0** | **1008** | **0.0%** |

### Binding Constraint: **kelly** (kills 0 configs that pass other 4 gates)

**No configs pass all gates at this tier.**

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
| tamrs | 0 | 1008 | 0.0% |
| rachev | 914 | 94 | 90.7% |
| ou_ratio | 0 | 1008 | 0.0% |
| **ALL gates** | **0** | **1008** | **0.0%** |

### Binding Constraint: **kelly** (kills 0 configs that pass other 4 gates)

**No configs pass all gates at this tier.**

## 3. Near-Miss Analysis (Tier 2 -- fail exactly 1 gate)

No near-misses found.

## 4. Summary

| Tier | Pass | % | Binding Constraint |
|------|------|---|-------------------|
| Tier1 Exploratory | 151 | 15.0% | kelly |
| Tier2 Balanced | 0 | 0.0% | kelly |
| Tier3 Strict | 0 | 0.0% | kelly |
