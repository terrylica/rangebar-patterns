**Skill**: [Sweep Methodology](../SKILL.md)

# Validated Patterns and Microstructure Themes

Detailed reference for patterns discovered across Gen300-Gen520. Each entry includes the validation evidence, signal count, and microstructure interpretation.

---

## Champion Base Pattern

All sweep generations build on top of this base:

```
2 consecutive DOWN bars + trade_intensity > p95_rolling + kyle_lambda_proxy > 0 → LONG
```

| Metric              | Value                            | Source            |
| ------------------- | -------------------------------- | ----------------- |
| Hit Rate (TRUE NLA) | 62.93%                           | Gen111            |
| Z-Score             | 8.25                             | Gen111            |
| Signal Count        | 1,017                            | SOLUSDT @1000dbps |
| 2024 edge           | +3.79% (z=0.87, NOT significant) | Gen112            |
| 2025 edge           | +4.25% (z=1.24, NOT significant) | Gen112            |

**Verdict**: Valid as ML feature input. Dead as standalone strategy.

---

## Top Dual-Validated Configs (Cross-Asset + Cross-Threshold)

These 5 configs survived both cross-asset (3+/12 assets) and cross-threshold (3+/4 thresholds) validation:

### 1. `price_impact_lt_p10__volume_per_trade_gt_p75`

- **Cross-asset**: 10/12 assets positive Kelly (best overall)
- **Avg Kelly**: +0.036 cross-asset
- **Story**: Very low spread impact + large institutional orders = informed accumulation with minimal market friction

### 2. `ofi_gt_p75__price_impact_gt_p75`

- **Kelly**: 0.112 | **Omega**: 1.505 | **N**: 130 trades
- **Tier 3 strict** screening pass
- **Story**: Strong order flow imbalance + high price impact = aggressive informed trading

### 3. `turnover_imbalance_gt_p75__price_impact_gt_p75`

- **Kelly**: 0.112 | **Omega**: 1.505 | **N**: 130 trades
- **Note**: Nearly identical to #2 (OFI and turnover_imbalance are proxies for each other)

### 4. `price_impact_lt_p50__aggregation_density_lt_p25`

- **Kelly**: 0.101 | **Omega**: 1.371 | **N**: 164 trades
- **Story**: Low spread + unclustered large trades = individual institutional orders without herding

### 5. `volume_per_trade_gt_p75__aggregation_density_lt_p25`

- **Kelly**: 0.094 | **Omega**: 1.414 | **N**: 105 trades
- **Story**: Large per-trade volume + low density = concentrated institutional flow

---

## Microstructure Theme A: Slow Accumulation

**Signature**: Low `aggregation_density` + high `duration_us`

**Interpretation**: Bars that form slowly and contain unclustered trades suggest patient institutional accumulation. The institution is building a position gradually, avoiding market impact. When 2 consecutive DOWN bars occur in this regime, the down move is likely temporary (institution absorbing selling pressure), leading to a reliable mean reversion.

**Cross-asset reach**: 7/12 assets positive (best generalization)
**Best cross-threshold Kelly**: +0.214 (averaged across thresholds)

---

## Microstructure Theme B: Institutional Flow

**Signature**: High `volume_per_trade` + extreme `ofi`/`turnover_imbalance`

**Interpretation**: Large individual orders with strong directional order flow pressure. When 2 consecutive DOWN bars fire in this regime with kyle_lambda > 0, it signals that a large buyer is absorbing the selling. The order flow imbalance confirms directional intent.

**Cross-threshold stability**: 4/4 thresholds positive (best stability)
**Best single-config Kelly**: +0.112

---

## Barrier Optimization Results (Gen510)

The top barrier configuration for mean-reversion patterns:

| Dimension     | Range Tested             | Optimal   | Kelly Impact                               |
| ------------- | ------------------------ | --------- | ------------------------------------------ |
| TP multiplier | [0.25, 0.50, 0.75, 1.00] | **0.25x** | Strongest single dimension (range = 0.302) |
| SL multiplier | [0.125, 0.25, 0.50]      | **0.50x** | Moderate impact (range = 0.151)            |
| Max bars      | [20, 50, 100]            | **100**   | Strong impact (range = 0.282)              |

**Key finding**: Time exits are catastrophic. Correlation between time_exit_rate and Kelly is r = -0.965.

---

## Threshold Sweet Spot (Gen520)

| Threshold | % Configs Positive | Best Kelly | Interpretation                             |
| --------- | ------------------ | ---------- | ------------------------------------------ |
| @250dbps  | 9.5%               | +0.087     | Too noisy — 5.29x more signals but diluted |
| @500dbps  | 21.7%              | +0.165     | Baseline                                   |
| @750dbps  | **40.7%**          | +0.180     | Sweet spot for Kelly                       |
| @1000dbps | 35.2%              | +0.165     | Inflated by tiny samples (p50=40 signals)  |

---

## Anti-Patterns (Configs That Consistently Lose)

92 configs survive **negative** Bonferroni — they consistently lose money across assets and thresholds. Common traits:

- High `aggression_ratio` on SHORT-biased signals
- Extreme `duration_us_gt_p90` on SHORT-biased signals
- Low `volume_per_trade` (retail flow, not institutional)

These anti-patterns represent "what NOT to do" and could theoretically be traded in reverse.

---

## Near-Miss Configs (Insufficient Data)

These configs show extreme metrics but have too few trades for statistical confidence:

| Config                                    | Kelly | Omega | N Trades | Action                         |
| ----------------------------------------- | ----- | ----- | -------- | ------------------------------ |
| `ofi_gt_p75__aggression_ratio_lt_p25`     | 0.624 | 5.94  | 8        | Paper trade to accumulate data |
| `ofi_gt_p90__vwap_close_deviation_gt_p90` | 0.436 | 3.31  | 8        | Paper trade to accumulate data |

These are candidates for monitoring (E-value based sequential testing) rather than deployment.

---

## Available Feature Space (47 Total)

### Bar-Level (9 features — EXHAUSTIVELY TESTED in Gen300-520)

`ofi`, `aggression_ratio`, `turnover_imbalance`, `price_impact`, `vwap_close_deviation`, `volume_per_trade`, `aggregation_density`, `duration_us`, `trade_intensity`

### Lookback Window (16 features — TESTING IN GEN600)

`lookback_ofi`, `lookback_intensity`, `lookback_hurst`, `lookback_permutation_entropy`, `lookback_garman_klass_vol`, `lookback_kaufman_er`, `lookback_burstiness`, `lookback_volume_skew`, `lookback_volume_kurt`, `lookback_price_range`, `lookback_vwap_raw`, `lookback_vwap_position`, `lookback_count_imbalance`, `lookback_kyle_lambda`, `lookback_trade_count`, `lookback_duration_us`

### Intra-Bar (22 features — TESTING IN GEN600)

`intra_bull_epoch_density`, `intra_bear_epoch_density`, `intra_bull_excess_gain`, `intra_bear_excess_gain`, `intra_bull_cv`, `intra_bear_cv`, `intra_max_drawdown`, `intra_max_runup`, `intra_trade_count`, `intra_ofi`, `intra_duration_us`, `intra_intensity`, `intra_vwap_position`, `intra_count_imbalance`, `intra_kyle_lambda`, `intra_burstiness`, `intra_volume_skew`, `intra_volume_kurt`, `intra_kaufman_er`, `intra_garman_klass_vol`, `intra_hurst`, `intra_permutation_entropy`

**Note**: `intra_hurst` and `intra_permutation_entropy` have 65-90% population rates (need minimum trade count within bar). All others ~100% populated.

**Dead combination**: NEARUSDT @250 has all lookback zeros and all intra NULLs. Exclude from sweeps.
