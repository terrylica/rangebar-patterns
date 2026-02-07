---
analysis_type: internal
generated_by: claude-opus-4-6
generated_at: 2026-02-07T22:00:00Z
purpose: Forensic-level performance analysis of Gen500/510/520 overnight brute-force sweeps
tags:
  [
    cross-asset,
    barrier-optimization,
    multi-threshold,
    bonferroni,
    overfitting,
    feature-selection,
    kelly-criterion,
  ]

# Provenance
git_commit: d73254b
data_commit_message: "feat: collect Gen500-520 overnight sweep results (15,300 configs)"
total_configs_analyzed: 15300
test_space_size: 16128

# Cross-references
parent_issue_url: https://github.com/terrylica/rangebar-patterns/issues/9
github_issue_url: https://github.com/terrylica/rangebar-patterns/issues/11
related_issues:
  - https://github.com/terrylica/rangebar-patterns/issues/8
  - https://github.com/terrylica/rangebar-patterns/issues/9
---

# Overnight Sweep Forensic Analysis — Gen500/510/520

**Date**: 2026-02-07
**Status**: **COMPLETE — NO POSITIVE-KELLY CONFIG SURVIVES BONFERRONI**
**Scope**: 15,300 configs across 3 sweep dimensions (cross-asset, barrier, multi-threshold)
**Data**: [`logs/gen500/`](/logs/gen500/), [`logs/gen510/`](/logs/gen510/), [`logs/gen520/`](/logs/gen520/)

---

## Executive Summary

**15,300 configs** analyzed across 3 dimensions: cross-asset (12 assets), barrier optimization (36 barrier combos), and multi-threshold (4 range bar sizes). The combined test space is **16,128 tests**.

**Bottom line**: No positive-Kelly config survives Bonferroni correction. The strongest evidence for real alpha comes from **56 configs** that pass both cross-threshold AND cross-asset validation — but even these have modest Kelly (+0.02–0.04 average). The original SOLUSDT champion is **dead** (1/12 assets positive).

### Verdict Summary

| Sweep                    | Key Finding                                                    | Actionable?                 |
| ------------------------ | -------------------------------------------------------------- | --------------------------- |
| Gen500 (cross-asset)     | 443 configs positive on 3+ assets, but none survive Bonferroni | Use as NN features          |
| Gen510 (barrier grid)    | TP=0.25x/SL=0.50x **inverts** Gen400 default → +283% Kelly     | **YES — adopt immediately** |
| Gen520 (multi-threshold) | @500–750dbps sweet spot; 56 configs pass dual validation       | Use as NN features          |

---

## Data Inventory

| Generation | Directory                       | Files    | Lines  | Configs                 | Hypothesis                   |
| ---------- | ------------------------------- | -------- | ------ | ----------------------- | ---------------------------- |
| 500        | [`logs/gen500/`](/logs/gen500/) | 12 JSONL | 12,096 | 1,008 × 12 assets       | Cross-asset 2F consistency   |
| 510        | [`logs/gen510/`](/logs/gen510/) | 1 JSONL  | 180    | 5 winners × 36 barriers | Barrier optimization         |
| 520        | [`logs/gen520/`](/logs/gen520/) | 3 JSONL  | 3,024  | 1,008 × 3 thresholds    | Multi-threshold robustness   |
| 400        | [`logs/gen400/`](/logs/gen400/) | 3 JSONL  | 14,224 | Baseline @500dbps       | Reference (prior generation) |

### Gen500 Assets

| Asset     | Threshold | File                                                      | Signals (avg/config) |
| --------- | --------- | --------------------------------------------------------- | -------------------- |
| SOLUSDT   | @500dbps  | (Gen400 baseline)                                         | 268                  |
| ADAUSDT   | @500dbps  | [`ADAUSDT_500.jsonl`](/logs/gen500/ADAUSDT_500.jsonl)     | 472                  |
| AVAXUSDT  | @500dbps  | [`AVAXUSDT_500.jsonl`](/logs/gen500/AVAXUSDT_500.jsonl)   | 273                  |
| BNBUSDT   | @250dbps  | [`BNBUSDT_250.jsonl`](/logs/gen500/BNBUSDT_250.jsonl)     | 957                  |
| BTCUSDT   | @250dbps  | [`BTCUSDT_250.jsonl`](/logs/gen500/BTCUSDT_250.jsonl)     | 730                  |
| DOGEUSDT  | @500dbps  | [`DOGEUSDT_500.jsonl`](/logs/gen500/DOGEUSDT_500.jsonl)   | 515                  |
| DOTUSDT   | @500dbps  | [`DOTUSDT_500.jsonl`](/logs/gen500/DOTUSDT_500.jsonl)     | 278                  |
| ETHUSDT   | @250dbps  | [`ETHUSDT_250.jsonl`](/logs/gen500/ETHUSDT_250.jsonl)     | 1,110                |
| LINKUSDT  | @500dbps  | [`LINKUSDT_500.jsonl`](/logs/gen500/LINKUSDT_500.jsonl)   | 475                  |
| LTCUSDT   | @500dbps  | [`LTCUSDT_500.jsonl`](/logs/gen500/LTCUSDT_500.jsonl)     | 316                  |
| MATICUSDT | @500dbps  | [`MATICUSDT_500.jsonl`](/logs/gen500/MATICUSDT_500.jsonl) | 315                  |
| NEARUSDT  | @500dbps  | [`NEARUSDT_500.jsonl`](/logs/gen500/NEARUSDT_500.jsonl)   | 349                  |
| XRPUSDT   | @500dbps  | [`XRPUSDT_500.jsonl`](/logs/gen500/XRPUSDT_500.jsonl)     | 447                  |

---

## Part 1: Gen500 Cross-Asset 2-Feature Sweep

### 1.1 Per-Asset Summary

| Asset         | Total | Kelly>0       | Kelly>0.02 | Best Kelly | Best Config                       | Median Kelly | Avg Signals |
| ------------- | ----- | ------------- | ---------- | ---------- | --------------------------------- | ------------ | ----------- |
| DOTUSDT_500   | 1,008 | **672 (67%)** | 502 (50%)  | 0.500      | various                           | **+0.020**   | 278         |
| LTCUSDT_500   | 1,008 | 486 (48%)     | 326 (32%)  | 0.500      | various                           | 0.000        | 316         |
| ADAUSDT_500   | 1,008 | 474 (47%)     | 334 (33%)  | **0.654**  | `ofi_lt_p10__price_impact_lt_p10` | -0.001       | 472         |
| AVAXUSDT_500  | 1,008 | 383 (38%)     | 207 (21%)  | 0.498      | various                           | -0.010       | 273         |
| NEARUSDT_500  | 1,008 | 353 (35%)     | 213 (21%)  | 0.286      | various                           | -0.012       | 349         |
| LINKUSDT_500  | 1,008 | 334 (33%)     | 216 (21%)  | 0.286      | various                           | -0.016       | 475         |
| XRPUSDT_500   | 1,008 | 274 (27%)     | 171 (17%)  | 0.250      | various                           | -0.030       | 447         |
| MATICUSDT_500 | 1,008 | 177 (18%)     | 142 (14%)  | 0.625      | various                           | -0.056       | 315         |
| ETHUSDT_250   | 1,008 | 122 (12%)     | 38 (4%)    | 0.550      | various                           | -0.046       | 1,110       |
| DOGEUSDT_500  | 1,008 | 57 (6%)       | 42 (4%)    | 0.625      | various                           | -0.140       | 515         |
| BTCUSDT_250   | 1,008 | 51 (5%)       | 32 (3%)    | 0.400      | various                           | -0.106       | 730         |
| BNBUSDT_250   | 1,008 | **42 (4%)**   | 24 (2%)    | 0.300      | various                           | **-0.080**   | 957         |

**Key observations**:

- **Asset heterogeneity is extreme**: DOTUSDT has 67% positive configs vs BNBUSDT at 4%
- **Median Kelly is negative** on 9/12 assets — most 2-feature filters lose money
- **@250dbps assets (BTC/ETH/BNB) systematically underperform** — different threshold, different dynamics
- **Best Kellys** (0.625–0.654) correlate with **tiny signal counts** (<20) — overfitting artifacts

### 1.2 Cross-Asset Consistency (Top 20)

630 configs are positive on 3+ assets. Top 20 ranked by #assets positive, then avg Kelly:

| Rank | Config ID                                             | Assets+   | Avg Kelly | Min Kelly | Max Kelly | Total Signals |
| ---- | ----------------------------------------------------- | --------- | --------- | --------- | --------- | ------------- |
| 1    | `aggression_ratio_lt_p10__price_impact_lt_p50`        | **10/12** | +0.038    | -0.091    | +0.170    | 689           |
| 2    | `price_impact_lt_p10__volume_per_trade_gt_p75`        | **10/12** | +0.027    | -0.023    | +0.105    | 4,085         |
| 3    | `price_impact_lt_p10__duration_us_lt_p25`             | 9/12      | +0.053    | -0.100    | +0.250    | 524           |
| 4    | `aggression_ratio_lt_p10__volume_per_trade_gt_p90`    | 9/12      | +0.032    | -0.092    | +0.211    | 917           |
| 5    | `volume_per_trade_gt_p75__aggregation_density_gt_p90` | 9/12      | +0.020    | -0.105    | +0.152    | 2,073         |

**Microstructure interpretation**:

- **Rank 1**: Low aggression + low price impact → **passive liquidity provision during calm periods**
- **Rank 2**: Low price impact + high volume/trade → **large institutional passive orders** (4,085 total signals = most statistically robust)
- **Rank 3–5**: Variations on low impact / high volume theme

### 1.3 Feature Frequency Analysis (configs positive on 5+ assets, N=344)

| Feature                | Count | %     | Dominant Direction |
| ---------------------- | ----- | ----- | ------------------ |
| `volume_per_trade`     | 105   | 15.3% | gt (91 vs 14)      |
| `duration_us`          | 96    | 14.0% | gt (76 vs 20)      |
| `price_impact`         | 95    | 13.8% | **lt (90 vs 5)**   |
| `aggression_ratio`     | 88    | 12.8% | mixed              |
| `turnover_imbalance`   | 82    | 11.9% | mixed              |
| `ofi`                  | 79    | 11.5% | mixed              |
| `vwap_close_deviation` | 74    | 10.8% | mixed              |
| `aggregation_density`  | 69    | 10.0% | mixed              |

**Quantile distribution**:

| Quantile | Count | %         |
| -------- | ----- | --------- |
| p50      | 210   | **30.5%** |
| p90      | 158   | 23.0%     |
| p75      | 131   | 19.0%     |
| p10      | 103   | 15.0%     |
| p25      | 86    | 12.5%     |

**Median-based thresholds (p50) dominate** — they filter ~50% of signals, preserving sample size while capturing directional bias.

### 1.4 Signal Count vs Kelly

| Signal Range | Config Count | Avg Kelly       | Assessment          |
| ------------ | ------------ | --------------- | ------------------- |
| 0–10         | ~200         | highly variable | **Noise**           |
| 11–50        | ~400         | +0.05 avg       | **Suspect**         |
| 51–200       | ~600         | +0.01 avg       | Marginal            |
| 201–1000     | ~500         | -0.02 avg       | Reliable            |
| 1000+        | ~300         | -0.05 avg       | Reliable (negative) |

**Correlation** (signal count vs Kelly): r = **-0.043** (effectively zero).

**421 configs** have Kelly > 0.05 AND signals < 50 — flagged as **overfitting artifacts**.

### 1.5 Bonferroni Multiple Testing

| Parameter                  | Value                         |
| -------------------------- | ----------------------------- |
| Total tests                | 12,096 (1,008 × 12 assets)    |
| Bonferroni alpha           | 0.05 / 12,096 = **4.13×10⁻⁶** |
| Required \|z\|-score       | 4.37                          |
| Survivors (positive Kelly) | **0**                         |
| Survivors (negative Kelly) | 66                            |

**All 66 Bonferroni survivors have NEGATIVE Kelly** — they are anti-patterns (consistently lose money).

Top 3 anti-patterns:

| Config                                          | Avg Kelly | z-score | p-value    |
| ----------------------------------------------- | --------- | ------- | ---------- |
| `aggression_ratio_lt_p50__duration_us_lt_p25`   | -0.064    | -7.87   | 3.55×10⁻¹⁵ |
| `turnover_imbalance_lt_p25__duration_us_lt_p25` | -0.075    | -7.47   | 7.73×10⁻¹⁴ |
| `ofi_lt_p25__duration_us_lt_p25`                | -0.075    | -7.45   | 9.59×10⁻¹⁴ |

**Interpretation**: Short-duration + directional features = **consistent losers**. These are "what NOT to do" patterns.

### 1.6 Original SOLUSDT Champion: `aggression_ratio_gt_p50__duration_us_lt_p50`

| Asset         | Kelly      | Signals | Win Rate | PF   | Verdict       |
| ------------- | ---------- | ------- | -------- | ---- | ------------- |
| LTCUSDT_500   | **+0.018** | 575     | 34.96%   | 1.11 | Only positive |
| DOTUSDT_500   | -0.004     | 492     | 33.74%   | 1.07 | Negative      |
| ADAUSDT_500   | -0.013     | 738     | 32.93%   | 1.05 | Negative      |
| NEARUSDT_500  | -0.025     | 590     | 32.54%   | 1.03 | Negative      |
| LINKUSDT_500  | -0.029     | 807     | 31.85%   | 0.97 | Negative      |
| AVAXUSDT_500  | -0.050     | 377     | 31.30%   | 1.02 | Negative      |
| ETHUSDT_250   | -0.054     | 1,551   | 30.82%   | 1.02 | Negative      |
| XRPUSDT_500   | -0.089     | 571     | 29.25%   | 0.98 | Negative      |
| MATICUSDT_500 | -0.101     | 635     | 29.61%   | 0.92 | Negative      |
| BNBUSDT_250   | -0.119     | 1,619   | 28.04%   | 0.91 | Negative      |
| BTCUSDT_250   | -0.160     | 966     | 25.88%   | 0.94 | Negative      |
| DOGEUSDT_500  | -0.240     | 1,044   | 24.23%   | 1.01 | Negative      |

**Result: 1/12 positive (8.3%). The Gen400 SOLUSDT champion is asset-specific overfitting — NOT a generalizable alpha signal.**

---

## Part 2: Gen510 Barrier Grid Optimization

### 2.1 The Barrier Inversion Discovery

The Gen400 default barriers (TP=0.50x, SL=0.25x, max_bars=50) are **exactly wrong** for this mean-reversion pattern. The optimal is the **exact inverse**:

| Metric        | Default (TP=0.50x, SL=0.25x, MB=50) | Optimal (TP=0.25x, SL=0.50x, MB=100) | Improvement |
| ------------- | ----------------------------------- | ------------------------------------ | ----------- |
| Kelly         | +0.041                              | **+0.157**                           | **+283%**   |
| Win Rate      | ~55%                                | **72%**                              | +17pp       |
| Profit Factor | 1.24                                | **1.28**                             | +3%         |
| Signals       | 427                                 | 427                                  | (same)      |

**Why inverted barriers work**: This is a **mean-reversion** pattern (2 consecutive DOWN bars → LONG). The price has already moved against the position direction. A tight take-profit (0.25x threshold) captures the bounce quickly; a wide stop-loss (0.50x) tolerates continuation before the eventual reversal.

### 2.2 Barrier Dimension Effects

| Dimension         | Range of Mean Kelly | Best Level | Worst Level | Effect Rank        |
| ----------------- | ------------------- | ---------- | ----------- | ------------------ |
| **TP Multiplier** | 0.302               | TP=0.25x   | TP=1.00x    | **#1 (strongest)** |
| Max Bars          | 0.282               | MB=100     | MB=20       | #2                 |
| SL Multiplier     | 0.151               | SL=0.50x   | SL=0.125x   | #3                 |

**Average Kelly by TP Multiplier**:

| TP Mult | Mean Kelly | Interpretation                |
| ------- | ---------- | ----------------------------- |
| 0.25x   | **+0.050** | Quick profit capture          |
| 0.50x   | -0.056     | Moderate target               |
| 0.75x   | -0.130     | Extended target               |
| 1.00x   | -0.252     | Full-threshold target (worst) |

### 2.3 Time Exit Catastrophe

| max_bars | Time Exit Rate | Mean Kelly | Assessment   |
| -------- | -------------- | ---------- | ------------ |
| 20       | **29.2%**      | **-0.277** | Catastrophic |
| 50       | 9.8%           | -0.086     | Bad          |
| 100      | **1.6%**       | **+0.005** | Acceptable   |

**Correlation** (time_exit_rate vs Kelly): r = **-0.965** (nearly perfect negative).

**Interpretation**: Time exits are alpha destruction. When the pattern doesn't resolve within max_bars, exiting at market is almost always a loss. Wider time windows (MB=100) allow the mean-reversion to complete.

### 2.4 Per-Feature Optimal Barriers

All 5 feature configs converge on the **same optimal barrier**: TP=0.25x, SL=0.50x, MB=100.

| Feature Config                                          | Default Kelly | Optimal Kelly | Improvement |
| ------------------------------------------------------- | ------------- | ------------- | ----------- |
| `aggression_ratio_gt_p50__duration_us_lt_p50`           | +0.041        | **+0.157**    | +283%       |
| `aggression_ratio_gt_p50__aggregation_density_gt_p50`   | +0.028        | **+0.091**    | +225%       |
| `price_impact_lt_p50__aggregation_density_gt_p50`       | +0.020        | **+0.078**    | +290%       |
| `ofi_lt_p50__aggregation_density_gt_p50`                | +0.017        | **+0.065**    | +282%       |
| `turnover_imbalance_lt_p50__aggregation_density_gt_p50` | +0.015        | **+0.058**    | +287%       |

### 2.5 Win Rate vs Kelly

- **Correlation**: r = +0.617 (strong positive)
- **Top 10 by Kelly = Top 10 by Win Rate** (perfect alignment)
- **Risk-reward ratio vs Kelly**: r = -0.044 (near zero)

**Conclusion**: For mean-reversion, **win rate matters far more than risk-reward ratio**. The 72% hit rate with conservative 0.25x profit targets beats aggressive 1.00x targets with 35% hit rates.

### 2.6 Bonferroni for Barrier Grid

| Parameter             | Value                          |
| --------------------- | ------------------------------ |
| Total tests           | 180 (5 features × 36 barriers) |
| Bonferroni alpha      | 0.05 / 180 = 2.78×10⁻⁴         |
| Required \|z\|-score  | 7.66                           |
| Best z-score achieved | 3.24                           |
| **Survivors**         | **0/180**                      |

**Insufficient sample size**: With N~400–800 signals per config, detecting Kelly=+0.15 at Bonferroni-corrected significance requires N>6,000. The barrier inversion is **economically meaningful** but not statistically proven at this sample size.

---

## Part 3: Gen520 Multi-Threshold Sweep

### 3.1 Per-Threshold Summary

| Threshold | Total Bars (est.) | Positive Kelly % | Best Kelly | Median Kelly  | Mean Signals/Config |
| --------- | ----------------- | ---------------- | ---------- | ------------- | ------------------- |
| @250dbps  | ~181,560          | **9.5%** (96)    | 0.500      | deep negative | 1,418               |
| @500dbps  | ~33,920           | 21.7% (219)      | 0.624      | negative      | 268                 |
| @750dbps  | ~17,120           | **40.7%** (410)  | 0.500      | near zero     | 122                 |
| @1000dbps | ~11,260           | 35.2% (355)      | 0.625      | near zero     | 74                  |

**The paradox**: Lower thresholds have 5x more data but 4x fewer positive configs. @250dbps adds **noise**, not signal. The sweet spot is **@500–750dbps**.

**Signal count scaling** (relative to @500):

| Threshold | Signal Multiplier | Median Signals |
| --------- | ----------------- | -------------- |
| @250dbps  | **5.29x**         | 936            |
| @500dbps  | 1.00x             | 189            |
| @750dbps  | 0.46x             | 72             |
| @1000dbps | 0.28x             | 40             |

### 3.2 Cross-Threshold Robustness

| Tier                    | Count | Description                  |
| ----------------------- | ----- | ---------------------------- |
| **Gold (4/4 positive)** | **6** | Positive at ALL 4 thresholds |
| Silver (3/4 positive)   | 60    | Positive at 3/4 thresholds   |
| Bronze (2/4)            | ~250  | Positive at 2/4 thresholds   |

### Gold Tier Configs (positive at all 4 thresholds)

| Config                                               | Avg Kelly | @250  | @500  | @750  | @1000 |
| ---------------------------------------------------- | --------- | ----- | ----- | ----- | ----- |
| `aggression_ratio_gt_p90__volume_per_trade_gt_p90`   | 0.158     | 0.031 | 0.063 | 0.100 | 0.438 |
| `aggregation_density_lt_p25__duration_us_gt_p90`     | 0.139     | 0.099 | 0.063 | 0.100 | 0.294 |
| `turnover_imbalance_gt_p90__volume_per_trade_gt_p90` | 0.132     | 0.012 | 0.029 | 0.250 | 0.238 |
| `aggression_ratio_gt_p75__volume_per_trade_gt_p90`   | 0.123     | 0.009 | 0.039 | 0.063 | 0.382 |
| `price_impact_lt_p25__aggregation_density_lt_p25`    | 0.106     | 0.011 | 0.127 | 0.077 | 0.211 |
| `ofi_gt_p90__volume_per_trade_gt_p90`                | 0.094     | 0.008 | 0.029 | 0.100 | 0.240 |

**Warning**: @1000dbps Kelly values are inflated by tiny sample sizes (4–20 signals). The @250/@500 values are more reliable.

### 3.3 Threshold-Specific Winners

Different thresholds surface **different microstructure regimes**:

| Threshold | Unique Winner Pattern          | Interpretation                                 |
| --------- | ------------------------------ | ---------------------------------------------- |
| @250dbps  | Low aggression + long duration | Contrarian mean-reversion in fine-grained bars |
| @500dbps  | OFI/vwap extremes              | Momentum capture at moderate granularity       |
| @750dbps  | High price impact + duration   | Liquidity events in coarse bars                |
| @1000dbps | Low OFI + high aggression      | Exhaustion reversals at very coarse bars       |

### 3.4 Signal Count Reliability by Threshold

| Threshold | p10 | p25 | p50    | p75   | p90   |
| --------- | --- | --- | ------ | ----- | ----- |
| @250dbps  | 137 | 426 | 936    | 1,942 | 3,501 |
| @500dbps  | 21  | 80  | 189    | 363   | 656   |
| @750dbps  | 9   | 28  | 72     | 177   | 308   |
| @1000dbps | 7   | 17  | **40** | 100   | 194   |

**At @1000dbps, 50% of configs have ≤40 signals** — statistical reliability is questionable. @750dbps is marginal (p50=72). Only @250 and @500 have sufficient sample sizes across most configs.

### 3.5 Bonferroni for Multi-Threshold

| Parameter                  | Value                        |
| -------------------------- | ---------------------------- |
| Total tests                | 4,032 (1,008 × 4 thresholds) |
| Bonferroni alpha           | 1.24×10⁻⁵                    |
| Required \|z\|-score       | 4.37                         |
| Survivors (positive Kelly) | **0**                        |
| Survivors (negative Kelly) | 26                           |

All 26 survivors are **negative Kelly at @250dbps** — same anti-pattern theme: short-duration, small-trade configs consistently lose.

---

## Part 4: The Holy Grail — Cross-Threshold × Cross-Asset Intersection

This is the **most powerful overfitting filter**: configs must generalize across BOTH:

- **Time granularity** (4 different range bar thresholds on SOLUSDT)
- **Market identity** (12 independent crypto assets)

### 56 Configs Survive Dual Validation

Only **56 of 1,008 configs** (5.6%) are positive at **both**:

- 3+/4 thresholds (cross-threshold robust)
- 3+/12 assets (cross-asset robust)

### Top 10 Most Robust Configs

| Rank | Config                                                   | Thresh+ | Assets+  | Avg Kelly (thresh) | Avg Kelly (asset) |
| ---- | -------------------------------------------------------- | ------- | -------- | ------------------ | ----------------- |
| 1    | `aggregation_density_lt_p10__duration_us_gt_p90`         | 3/4     | **7/12** | +0.214             | +0.035            |
| 2    | `turnover_imbalance_gt_p90__volume_per_trade_gt_p90`     | **4/4** | 6/12     | +0.132             | +0.020            |
| 3    | `ofi_gt_p90__volume_per_trade_gt_p90`                    | **4/4** | 6/12     | +0.094             | +0.018            |
| 4    | `aggregation_density_lt_p10__duration_us_gt_p75`         | 3/4     | **7/12** | +0.078             | +0.025            |
| 5    | `aggression_ratio_gt_p90__volume_per_trade_gt_p90`       | **4/4** | 6/12     | +0.158             | -0.024            |
| 6    | `price_impact_lt_p25__aggregation_density_lt_p25`        | **4/4** | 5/12     | +0.106             | +0.015            |
| 7    | `ofi_gt_p90__vwap_close_deviation_gt_p90`                | 3/4     | 5/12     | +0.194             | +0.012            |
| 8    | `turnover_imbalance_gt_p90__vwap_close_deviation_gt_p90` | 3/4     | 5/12     | +0.194             | +0.012            |
| 9    | `aggregation_density_lt_p25__duration_us_gt_p90`         | **4/4** | 5/12     | +0.139             | +0.018            |
| 10   | `aggression_ratio_gt_p75__volume_per_trade_gt_p90`       | **4/4** | 5/12     | +0.123             | +0.010            |

### Emergent Feature Themes

Two dominant microstructure narratives emerge from the robust set:

**Theme A: Slow Accumulation** (Ranks 1, 4, 6, 9)

- Low `aggregation_density` + high `duration_us`
- Unclustered, slow-forming bars = institutional accumulation before directional move
- Best cross-asset generalization (7/12 assets)

**Theme B: Institutional Directional Flow** (Ranks 2, 3, 5, 10)

- High `volume_per_trade` + extreme `OFI`/`turnover_imbalance`
- Large orders with strong directional bias = informed institutional flow
- Best cross-threshold stability (4/4 thresholds)

---

## Consolidated Statistical Summary

### What Survives Multiple Testing

| Test                   | Tests      | Bonferroni α  | Positive Survivors | Negative Survivors |
| ---------------------- | ---------- | ------------- | ------------------ | ------------------ |
| Gen500 cross-asset     | 12,096     | 4.13×10⁻⁶     | **0**              | 66                 |
| Gen510 barrier grid    | 180        | 2.78×10⁻⁴     | **0**              | 0                  |
| Gen520 multi-threshold | 4,032      | 1.24×10⁻⁵     | **0**              | 26                 |
| **Combined**           | **16,308** | **3.07×10⁻⁶** | **0**              | 92                 |

**No positive-Kelly config survives Bonferroni in any generation.**

The 92 Bonferroni survivors are all **anti-patterns** — they consistently LOSE money. These are "what NOT to do" signals.

### What's Real (Economic Significance)

Despite failing statistical tests, these findings have **economic significance**:

1. **Barrier inversion** (+283% Kelly improvement) — strongest single finding
2. **56 dual-validated configs** — 5.6% survival rate through two independent filters
3. **Feature hierarchy** confirmed across assets and thresholds:
   - `aggregation_density` (low) = most generalizable
   - `volume_per_trade` (high) = institutional flow proxy
   - `duration_us` (high) = slow accumulation signal
   - `OFI`/`turnover_imbalance` (extreme) = directional pressure

### What's Dead

1. **The SOLUSDT champion** (`aggression_ratio_gt_p50__duration_us_lt_p50`) — 1/12 assets positive
2. **All configs with <50 signals and high Kelly** — 421 flagged as noise
3. **@250dbps for feature discovery** — too noisy (9.5% positive rate)
4. **@1000dbps Kelly values** — inflated by tiny samples
5. **Standalone 2-feature trading** — insufficient edge for direct trading

---

## Recommendations

### Immediate Actions

1. **Adopt inverted barriers** (TP=0.25x, SL=0.50x, MB=100) for all future backtests
2. **Discard the SOLUSDT champion** as standalone signal
3. **Focus on @500–750dbps** threshold range for further research

### NN Feature Engineering

Use the **56 robust configs** as feature candidates for neural network input:

- Each config encodes 2 binary features (feature1 > threshold, feature2 > threshold)
- Ensemble across configs creates a rich feature vector
- This follows the "use as NN feature, not standalone signal" verdict from the [production readiness audit](/findings/2026-02-05-production-readiness-audit.md)

### Data Requirements

To achieve Bonferroni significance at Kelly=+0.03:

- Need N > **6,000 signals** per config
- Current max: ~1,500 signals at @500dbps
- Options: longer history, more assets, or accept economic significance without statistical proof

### Portfolio Strategy

The 7-asset winners (`aggregation_density` configs) across ADA, BTC, ETH, DOT, LTC, MATIC, XRP should be tested as:

- Equal-weight portfolio across assets
- Hypothesis: diversification reduces drawdown while preserving modest edge

---

## Cross-References

### Repository Files

| File                                                                                                      | Relevance                                     |
| --------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| [`logs/gen500/`](/logs/gen500/)                                                                           | 12 cross-asset JSONL files (12,096 configs)   |
| [`logs/gen510/barrier_grid.jsonl`](/logs/gen510/barrier_grid.jsonl)                                       | 180 barrier grid results                      |
| [`logs/gen520/`](/logs/gen520/)                                                                           | 3 multi-threshold JSONL files (3,024 configs) |
| [`logs/gen400/2feature.jsonl`](/logs/gen400/2feature.jsonl)                                               | Gen400 baseline @500dbps (1,008 configs)      |
| [`logs/CLAUDE.md`](/logs/CLAUDE.md)                                                                       | Generation index with verdicts                |
| [`findings/2026-02-05-production-readiness-audit.md`](/findings/2026-02-05-production-readiness-audit.md) | Champion pattern audit                        |
| [`findings/2026-02-02-brute-force-synthesis.md`](/findings/2026-02-02-brute-force-synthesis.md)           | Gen1–Gen110 evolution                         |
| [`sql/CLAUDE.md`](/sql/CLAUDE.md)                                                                         | SQL generation guide                          |

### GitHub Issues

| Issue                                                                                | Relevance                                |
| ------------------------------------------------------------------------------------ | ---------------------------------------- |
| [#11 Forensic Analysis](https://github.com/terrylica/rangebar-patterns/issues/11)    | **This analysis** — GitHub issue mirror  |
| [#9 Research Consolidation](https://github.com/terrylica/rangebar-patterns/issues/9) | Master reference for all research phases |
| [#8 Anti-Pattern Registry](https://github.com/terrylica/rangebar-patterns/issues/8)  | ClickHouse SQL constraints               |

### Methodology

- **Quantile method**: Rolling 1000-signal window (`ROWS BETWEEN 999 PRECEDING AND 1 PRECEDING`)
- **Barrier model**: Triple barrier (TP/SL/max_bars) per [Gen200-202 framework](/sql/CLAUDE.md)
- **Statistical test**: z = Kelly × sqrt(N), Bonferroni correction for multiple comparisons
- **Data source**: BigBlack ClickHouse (`rangebar_cache.range_bars`)
