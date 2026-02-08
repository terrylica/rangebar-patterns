# Lenient 5-Metric Screening — Forensic Report

## 1. Metric Distribution Summary (All 1,008 Configs)

| Metric | Min | P10 | P25 | P50 | P75 | P90 | Max |
|--------|-----|-----|-----|-----|-----|-----|-----|
| Kelly | -0.311348 | -0.128044 | -0.068838 | -0.030307 | -0.003448 | 0.040995 | 0.623787 |
| Omega | 0.0 | 0.84058 | 0.940096 | 1.016461 | 1.083001 | 1.2 | 5.942338 |
| DSR | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| MinBTL Headroom | 0.0 | 0.0002 | 0.0023 | 0.0165 | 0.052325 | 0.125 | 0.4706 |
| N Trades | 0.0 | 21.0 | 79.75 | 189.0 | 363.0 | 656.3 | 1696.0 |

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
| **ALL gates** | **151** | **857** | **15.0%** |

### Binding Constraint: **kelly** (kills 158 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | Kelly | Omega | DSR | Headroom | N Trades | Score |
|------|-----------|-------|-------|-----|----------|----------|-------|
| 1 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p | 0.2742 | 2.1333 | 0.000000 | 0.2886 | 31 | 0.7604 |
| 2 | ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | 0.7578 |
| 3 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | 0.7578 |
| 4 | volume_per_trade_gt_p90__aggregation_density_lt_p2 | 0.2091 | 1.9743 | 0.000000 | 0.3023 | 40 | 0.6251 |
| 5 | price_impact_lt_p25__vwap_close_deviation_gt_p90 | 0.1427 | 1.4991 | 0.000000 | 0.1685 | 63 | 0.3700 |
| 6 | ofi_gt_p75__price_impact_gt_p75 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.3676 |
| 7 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.3676 |
| 8 | ofi_gt_p90__price_impact_gt_p75 | 0.0892 | 1.6615 | 0.000000 | 0.1891 | 46 | 0.3405 |
| 9 | turnover_imbalance_gt_p90__price_impact_gt_p75 | 0.0892 | 1.6615 | 0.000000 | 0.1891 | 46 | 0.3405 |
| 10 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.1303 | 1.4493 | 0.000000 | 0.1550 | 69 | 0.3354 |
| 11 | price_impact_lt_p25__aggregation_density_lt_p25 | 0.1269 | 1.4359 | 0.000000 | 0.1429 | 67 | 0.3241 |
| 12 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.1213 | 1.4140 | 0.000000 | 0.1368 | 70 | 0.3087 |
| 13 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.1013 | 1.3707 | 0.000000 | 0.2672 | 164 | 0.2962 |
| 14 | ofi_gt_p90__duration_us_lt_p50 | 0.0942 | 1.4557 | 0.000000 | 0.1688 | 74 | 0.2875 |
| 15 | turnover_imbalance_gt_p75__duration_us_lt_p50 | 0.0917 | 1.3541 | 0.000000 | 0.3020 | 201 | 0.2852 |
| 16 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.0939 | 1.4140 | 0.000000 | 0.2060 | 105 | 0.2838 |
| 17 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0755 | 1.2913 | 0.000000 | 0.4706 | 440 | 0.2812 |
| 18 | ofi_gt_p75__duration_us_lt_p50 | 0.0887 | 1.3429 | 0.000000 | 0.2868 | 202 | 0.2744 |
| 19 | ofi_gt_p50__duration_us_lt_p50 | 0.0734 | 1.2838 | 0.000000 | 0.4482 | 439 | 0.2711 |
| 20 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 0.0860 | 1.4219 | 0.000000 | 0.1501 | 75 | 0.2622 |

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
| **ALL gates** | **73** | **935** | **7.2%** |

### Binding Constraint: **kelly** (kills 60 configs that pass other 4 gates)

### Top 20 Configs (by composite score)

| Rank | Config ID | Kelly | Omega | DSR | Headroom | N Trades | Score |
|------|-----------|-------|-------|-----|----------|----------|-------|
| 1 | price_impact_lt_p25__vwap_close_deviation_gt_p90 | 0.1427 | 1.4991 | 0.000000 | 0.1685 | 63 | 0.7237 |
| 2 | ofi_gt_p75__price_impact_gt_p75 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.6799 |
| 3 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.6799 |
| 4 | aggression_ratio_lt_p50__turnover_imbalance_gt_p75 | 0.1303 | 1.4493 | 0.000000 | 0.1550 | 69 | 0.6490 |
| 5 | price_impact_lt_p25__aggregation_density_lt_p25 | 0.1269 | 1.4359 | 0.000000 | 0.1429 | 67 | 0.6266 |
| 6 | ofi_gt_p75__aggression_ratio_lt_p50 | 0.1213 | 1.4140 | 0.000000 | 0.1368 | 70 | 0.5934 |
| 7 | ofi_gt_p90__duration_us_lt_p50 | 0.0942 | 1.4557 | 0.000000 | 0.1688 | 74 | 0.5475 |
| 8 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.1013 | 1.3707 | 0.000000 | 0.2672 | 164 | 0.5347 |
| 9 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.0939 | 1.4140 | 0.000000 | 0.2060 | 105 | 0.5271 |
| 10 | turnover_imbalance_gt_p75__duration_us_lt_p50 | 0.0917 | 1.3541 | 0.000000 | 0.3020 | 201 | 0.5025 |
| 11 | turnover_imbalance_gt_p90__duration_us_lt_p50 | 0.0860 | 1.4219 | 0.000000 | 0.1501 | 75 | 0.4951 |
| 12 | ofi_gt_p75__duration_us_lt_p50 | 0.0887 | 1.3429 | 0.000000 | 0.2868 | 202 | 0.4822 |
| 13 | aggression_ratio_gt_p90__duration_us_gt_p90 | 0.0952 | 1.3158 | 0.000000 | 0.1549 | 126 | 0.4520 |
| 14 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0755 | 1.2913 | 0.000000 | 0.4706 | 440 | 0.4511 |
| 15 | ofi_gt_p50__duration_us_lt_p50 | 0.0734 | 1.2838 | 0.000000 | 0.4482 | 439 | 0.4342 |
| 16 | price_impact_lt_p25__vwap_close_deviation_gt_p75 | 0.0844 | 1.3068 | 0.000000 | 0.1897 | 163 | 0.4213 |
| 17 | turnover_imbalance_gt_p50__vwap_close_deviation_gt | 0.0787 | 1.3572 | 0.000000 | 0.0766 | 51 | 0.4114 |
| 18 | vwap_close_deviation_lt_p10__volume_per_trade_gt_p | 0.0792 | 1.3117 | 0.000000 | 0.1136 | 95 | 0.3908 |
| 19 | price_impact_gt_p50__volume_per_trade_gt_p90 | 0.0741 | 1.3439 | 0.000000 | 0.0770 | 56 | 0.3886 |
| 20 | ofi_gt_p90__vwap_close_deviation_gt_p50 | 0.0716 | 1.3128 | 0.000000 | 0.1490 | 124 | 0.3771 |

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
| **ALL gates** | **16** | **992** | **1.6%** |

### Binding Constraint: **kelly** (kills 28 configs that pass other 4 gates)

### Top 16 Configs (by composite score)

| Rank | Config ID | Kelly | Omega | DSR | Headroom | N Trades | Score |
|------|-----------|-------|-------|-----|----------|----------|-------|
| 1 | ofi_gt_p75__price_impact_gt_p75 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.7655 |
| 2 | turnover_imbalance_gt_p75__price_impact_gt_p75 | 0.1121 | 1.5052 | 0.000000 | 0.3551 | 130 | 0.7655 |
| 3 | price_impact_lt_p50__aggregation_density_lt_p25 | 0.1013 | 1.3707 | 0.000000 | 0.2672 | 164 | 0.5411 |
| 4 | volume_per_trade_gt_p75__aggregation_density_lt_p2 | 0.0939 | 1.4140 | 0.000000 | 0.2060 | 105 | 0.5160 |
| 5 | turnover_imbalance_gt_p75__duration_us_lt_p50 | 0.0917 | 1.3541 | 0.000000 | 0.3020 | 201 | 0.4731 |
| 6 | ofi_gt_p75__duration_us_lt_p50 | 0.0887 | 1.3429 | 0.000000 | 0.2868 | 202 | 0.4385 |
| 7 | aggression_ratio_gt_p90__duration_us_gt_p90 | 0.0952 | 1.3158 | 0.000000 | 0.1549 | 126 | 0.4158 |
| 8 | turnover_imbalance_gt_p50__duration_us_lt_p50 | 0.0755 | 1.2913 | 0.000000 | 0.4706 | 440 | 0.3585 |
| 9 | price_impact_lt_p25__vwap_close_deviation_gt_p75 | 0.0844 | 1.3068 | 0.000000 | 0.1897 | 163 | 0.3470 |
| 10 | ofi_gt_p50__duration_us_lt_p50 | 0.0734 | 1.2838 | 0.000000 | 0.4482 | 439 | 0.3309 |
| 11 | ofi_gt_p90__vwap_close_deviation_gt_p50 | 0.0716 | 1.3128 | 0.000000 | 0.1490 | 124 | 0.2578 |
| 12 | turnover_imbalance_gt_p90__vwap_close_deviation_gt | 0.0669 | 1.2953 | 0.000000 | 0.1357 | 125 | 0.2067 |
| 13 | aggression_ratio_lt_p25__volume_per_trade_gt_p75 | 0.0556 | 1.2555 | 0.000000 | 0.2142 | 258 | 0.1183 |
| 14 | price_impact_gt_p75__duration_us_gt_p50 | 0.0541 | 1.2396 | 0.000000 | 0.1642 | 220 | 0.0789 |
| 15 | vwap_close_deviation_lt_p50__aggregation_density_l | 0.0505 | 1.2211 | 0.000000 | 0.1548 | 240 | 0.0352 |
| 16 | price_impact_lt_p25__duration_us_lt_p50 | 0.0509 | 1.1901 | 0.000000 | 0.1622 | 330 | 0.0102 |

## 3. Near-Miss Analysis (Tier 2 — fail exactly 1 gate)

**129 configs** fail exactly 1 gate at Tier 2:

| Failed Gate | Count |
|-------------|-------|
| kelly | 60 |
| headroom | 44 |
| n_trades | 25 |

### Top 10 Near-Misses (by Kelly)

| Config ID | Kelly | Omega | DSR | Headroom | N | Failed Gate |
|-----------|-------|-------|-----|----------|---|-------------|
| aggression_ratio_lt_p25__turnover_imbalance_g | 0.6238 | 5.9423 | 0.000001 | 0.3221 | 8 | n_trades |
| ofi_gt_p75__aggression_ratio_lt_p25 | 0.6238 | 5.9423 | 0.000001 | 0.3221 | 8 | n_trades |
| ofi_gt_p90__vwap_close_deviation_gt_p90 | 0.4363 | 3.3119 | 0.000000 | 0.1689 | 8 | n_trades |
| turnover_imbalance_gt_p90__vwap_close_deviati | 0.4363 | 3.3119 | 0.000000 | 0.1689 | 8 | n_trades |
| ofi_gt_p75__vwap_close_deviation_gt_p90 | 0.3069 | 2.3258 | 0.000000 | 0.1440 | 13 | n_trades |
| turnover_imbalance_gt_p75__vwap_close_deviati | 0.3069 | 2.3258 | 0.000000 | 0.1440 | 13 | n_trades |
| aggression_ratio_lt_p25__turnover_imbalance_g | 0.2827 | 2.1721 | 0.000000 | 0.2024 | 21 | n_trades |
| ofi_gt_p50__aggression_ratio_lt_p25 | 0.2827 | 2.1721 | 0.000000 | 0.2024 | 21 | n_trades |
| vwap_close_deviation_lt_p10__volume_per_trade | 0.2742 | 2.1333 | 0.000000 | 0.2886 | 31 | n_trades |
| ofi_gt_p90__vwap_close_deviation_gt_p75 | 0.2712 | 2.1152 | 0.000000 | 0.3198 | 35 | n_trades |

## 4. Summary

| Tier | Pass | % of 1,008 | Binding Constraint |
|------|------|------------|-------------------|
| Tier1 Exploratory | 151 | 15.0% | kelly |
| Tier2 Balanced | 73 | 7.2% | kelly |
| Tier3 Strict | 16 | 1.6% | kelly |

## 5. Actionable Recommendations

Configs passing Tier 1 (exploratory) are candidates for:
- **Live paper trading** to accumulate more trades (address MinBTL shortfall)
- **Cross-asset validation** via Gen500 data (check if signal generalizes)
- **Barrier optimization** via Gen510 grid (tight TP + wide SL)

PBO = 0.3286 (marginal) applies globally — there IS some overfitting risk.

