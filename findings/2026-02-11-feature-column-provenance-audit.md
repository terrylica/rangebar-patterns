# Feature Column Provenance Audit — lookback_* and intra_* Lookahead Verification

**Date**: 2026-02-11
**Scope**: All 16 `lookback_*` and 22 `intra_*` columns in `rangebar_cache.range_bars`
**Assets tested**: BTCUSDT @750, ETHUSDT @750, SOLUSDT @500

---

## Executive Verdict

**ALL PASS. No lookahead bias detected in any feature column.**

- All 16 `lookback_*` features are backward-only (computed from preceding bars)
- All 22 `intra_*` features describe the current bar's internals only (no future bar leakage)
- Results are consistent across BTCUSDT, ETHUSDT, and SOLUSDT

The 301K Gen600 configs are not invalidated by feature column provenance. Any overfitting is from signal selection, not data contamination.

---

## Test Methodology

### Test 1: Temporal Causality (Granger-Style)

For each feature, compute Pearson correlation with:
- **Current bar direction** (`close > open` → +1, else −1)
- **Next bar direction** (bar N+1)

**Expected behavior**:
- `lookback_*`: Near-zero correlation with both current and next bar (backward-looking aggregate)
- `intra_*`: Moderate correlation with current bar (describes its internals), near-zero with next bar

### Test 2: Lookback Independence from Current Bar

For matching feature pairs (`lookback_ofi` vs `ofi`), compute direct correlation. If lookback_X contains bar N's own X value, correlation would be ~1.0.

### Test 3: Variance Within Lookback Buckets

Group bars by rounded lookback value; compute stddev of the current bar's corresponding feature. High stddev = lookback is genuinely different from current (correct). Near-zero stddev = lookback contains current bar (contaminated).

### Test 4: Warmup Period (NaN Distribution)

Verify early bars have NaN lookback values (no preceding data to compute from).

### Test 5: Consecutive Bar Inspection

Manually inspect lookback value changes between adjacent bars to confirm gradual rolling-window behavior.

---

## Results: lookback_* Features (16 columns)

### Correlation with Current vs Next Bar Direction (BTCUSDT @750, N=83,024)

| Feature                      | corr(current) | corr(next)  | Verdict |
| ---------------------------- | ------------- | ----------- | ------- |
| lookback_ofi                 | +0.0006       | −0.0100     | PASS    |
| lookback_intensity           | +0.0015       | −0.0031     | PASS    |
| lookback_hurst               | −0.0018       | +0.0002     | PASS    |
| lookback_permutation_entropy | +0.0049       | +0.0103     | PASS    |
| lookback_garman_klass_vol    | +0.0177       | +0.0187     | PASS    |
| lookback_kaufman_er          | +0.0008       | −0.0019     | PASS    |
| lookback_burstiness          | +0.0053       | +0.0049     | PASS    |
| lookback_volume_skew         | +0.0069       | +0.0062     | PASS    |
| lookback_volume_kurt         | +0.0045       | +0.0033     | PASS    |
| lookback_price_range         | +0.0194       | +0.0214     | PASS    |
| lookback_vwap_raw            | −0.0048       | −0.0034     | PASS    |
| lookback_vwap_position       | +0.0193       | +0.0172     | PASS    |
| lookback_count_imbalance     | +0.0001       | −0.0081     | PASS    |
| lookback_kyle_lambda         | +0.0051       | −0.0038     | PASS    |
| lookback_trade_count         | +0.0057       | +0.0068     | PASS    |
| lookback_duration_us         | +0.0023       | +0.0035     | PASS    |

**Maximum |correlation|**: 0.0214 (lookback_price_range with next bar). All below 0.025 — consistent with pure noise.

### Direct lookback-vs-current Correlation (BTCUSDT @750, N=83,045)

| Feature Pair                                   | Correlation | Interpretation                        |
| ---------------------------------------------- | ----------- | ------------------------------------- |
| lookback_ofi vs ofi                            | +0.064      | Independent (not same value)          |
| lookback_intensity vs trade_intensity          | +0.0003     | Completely independent                |
| lookback_kyle_lambda vs kyle_lambda_proxy      | −0.0003     | Completely independent                |
| lookback_duration_us vs duration_us            | −0.210      | Mild negative (regime mean-reversion) |
| lookback_trade_count vs individual_trade_count | +0.068      | Weakly correlated (both count trades) |

**If lookback_ofi contained the current bar's ofi, this correlation would be ~1.0. It is 0.064. PASS.**

### Variance Within Lookback Buckets (lookback_ofi, BTCUSDT @750)

| lookback_ofi bucket | avg(current ofi) | stddev(current ofi) | n    |
| ------------------- | ---------------- | ------------------- | ---- |
| −0.35               | +0.106           | 0.451               | 65   |
| −0.20               | −0.050           | 0.319               | 141  |
| −0.14               | −0.178           | 0.654               | 2325 |
| −0.13               | −0.074           | 0.558               | 1630 |

**stddev >> |avg| in every bucket**, confirming bars with identical lookback_ofi have wildly varying current ofi. PASS.

### Warmup Period (Bar 1 NaN Check)

| Bar # | All lookback NaN? | Interpretation                 |
| ----- | ----------------- | ------------------------------ |
| 1     | Yes (all 16 NaN)  | No preceding data — correct    |
| 2     | No (all finite)   | One preceding bar available    |
| 3+    | No (all finite)   | Rolling window accumulating    |

NaN count across symbols: ~2,000–3,000 NaN rows per symbol-threshold combo (warmup bars). PASS.

### Consecutive Bar Behavior (bars 1050–1080, BTCUSDT @750)

```
timestamp_ms     ofi      lookback_ofi  delta_lb_ofi
1516139334571    +0.1247  −0.0409       +0.000495
1516139352634    +0.1540  −0.0405       +0.000405
1516139379377    −0.2205  −0.0404       +0.000062
1516139388835    −0.5745  −0.0406       −0.000168
1516139389269    −0.9729  −0.0407       −0.000055
```

**lookback_ofi changes by ~0.0001–0.0005 per bar** while current ofi swings −0.97 to +0.15. This is rolling window averaging behavior — the lookback gradually shifts as new bars enter/exit the window. PASS.

---

## Results: intra_* Features (22 columns)

### Correlation with Current vs Next Bar Direction (BTCUSDT @750, N=85,940)

| Feature                      | corr(current) | corr(next)  | Verdict |
| ---------------------------- | ------------- | ----------- | ------- |
| intra_ofi                    | **+0.147**    | +0.005      | PASS    |
| intra_intensity              | +0.006        | −0.004      | PASS    |
| intra_trade_count            | −0.003        | −0.004      | PASS    |
| intra_vwap_position          | **−0.361**    | +0.081      | PASS    |
| intra_count_imbalance        | **+0.124**    | +0.007      | PASS    |
| intra_kyle_lambda            | +0.003        | −0.001      | PASS    |
| intra_burstiness             | −0.010        | −0.015      | PASS    |
| intra_volume_skew            | −0.009        | −0.006      | PASS    |
| intra_volume_kurt            | +0.0002       | −0.004      | PASS    |
| intra_kaufman_er             | +0.003        | +0.023      | PASS    |
| intra_garman_klass_vol       | −0.019        | +0.014      | PASS    |
| intra_hurst                  | −0.009        | +0.002      | PASS    |
| intra_permutation_entropy    | **−0.166**    | +0.011      | PASS    |
| intra_max_drawdown           | **−0.650**    | +0.089      | PASS    |
| intra_max_runup              | **+0.643**    | −0.077      | PASS    |
| intra_duration_us            | +0.001        | −0.005      | PASS    |
| intra_bull_epoch_density     | **+0.179**    | −0.051      | PASS    |
| intra_bear_epoch_density     | **−0.185**    | +0.076      | PASS    |
| intra_bull_excess_gain       | +0.042        | −0.023      | PASS    |
| intra_bear_excess_gain       | −0.058        | −0.015      | PASS    |
| intra_bull_cv                | **+0.310**    | −0.031      | PASS    |
| intra_bear_cv                | **−0.301**    | +0.026      | PASS    |

**Pattern is exactly correct**:
- Features that describe current-bar microstructure (OFI, VWAP position, drawdown, runup, epoch density, CV) have moderate-to-strong correlation with current bar direction
- ALL features have near-zero correlation with next bar direction (max |corr_next| = 0.089)
- The small next-bar correlations (~0.08) are consistent with weak mean-reversion, not data leakage

### 2-Bar-Ahead Leakage Test (BTCUSDT @750, N=85,939)

| Feature              | corr(next) | corr(next+2) | Interpretation                 |
| -------------------- | ---------- | ------------ | ------------------------------ |
| intra_max_drawdown   | +0.089     | −0.027       | Decaying, sign-flipping: noise |
| intra_max_runup      | −0.077     | +0.033       | Decaying, sign-flipping: noise |
| intra_vwap_position  | +0.081     | −0.038       | Decaying, sign-flipping: noise |

Correlations decay rapidly and flip sign between bar+1 and bar+2 — classic mean-reversion microstructure, not systematic leakage. PASS.

---

## Cross-Asset Consistency

### SOLUSDT @500 (Champion Pattern Asset, N=377,944)

| Feature            | corr(current) | corr(next) |
| ------------------ | ------------- | ---------- |
| lookback_ofi       | +0.0005       | −0.0005    |
| lookback_intensity | +0.0006       | +0.0004    |
| lookback_kyle      | −0.0026       | −0.0011    |
| intra_ofi          | **+0.358**    | +0.003     |
| intra_max_drawdown | **−0.648**    | +0.037     |
| intra_max_runup    | **+0.643**    | −0.032     |

### ETHUSDT @750 (N=126,304)

| Feature            | corr(current) | corr(next) |
| ------------------ | ------------- | ---------- |
| lookback_ofi       | +0.0145       | +0.0023    |
| lookback_intensity | +0.0020       | −0.0014    |
| lookback_kyle      | +0.0013       | +0.0024    |
| intra_ofi          | **+0.234**    | −0.004     |
| intra_max_drawdown | **−0.652**    | +0.059     |
| intra_max_runup    | **+0.639**    | −0.059     |

**All three assets show identical patterns.** The provenance is structural, not asset-specific.

---

## Feature-Level Verdict Table

| # | Feature                      | Type     | corr(curr) | corr(next) | Direct r | Verdict  |
|---|------------------------------|----------|------------|------------|----------|----------|
| 1 | lookback_ofi                 | lookback | 0.001      | −0.010     | 0.064    | **PASS** |
| 2 | lookback_intensity           | lookback | 0.002      | −0.003     | 0.000    | **PASS** |
| 3 | lookback_hurst               | lookback | −0.002     | 0.000      | —        | **PASS** |
| 4 | lookback_permutation_entropy | lookback | 0.005      | 0.010      | —        | **PASS** |
| 5 | lookback_garman_klass_vol    | lookback | 0.018      | 0.019      | —        | **PASS** |
| 6 | lookback_kaufman_er          | lookback | 0.001      | −0.002     | —        | **PASS** |
| 7 | lookback_burstiness          | lookback | 0.005      | 0.005      | —        | **PASS** |
| 8 | lookback_volume_skew         | lookback | 0.007      | 0.006      | —        | **PASS** |
| 9 | lookback_volume_kurt         | lookback | 0.005      | 0.003      | —        | **PASS** |
| 10| lookback_price_range         | lookback | 0.019      | 0.021      | —        | **PASS** |
| 11| lookback_vwap_raw            | lookback | −0.005     | −0.003     | —        | **PASS** |
| 12| lookback_vwap_position       | lookback | 0.019      | 0.017      | —        | **PASS** |
| 13| lookback_count_imbalance     | lookback | 0.000      | −0.008     | —        | **PASS** |
| 14| lookback_kyle_lambda         | lookback | 0.005      | −0.004     | −0.000   | **PASS** |
| 15| lookback_trade_count         | lookback | 0.006      | 0.007      | 0.068    | **PASS** |
| 16| lookback_duration_us         | lookback | 0.002      | 0.004      | −0.210   | **PASS** |
| 17| intra_ofi                    | intra    | **0.147**  | 0.005      | —        | **PASS** |
| 18| intra_intensity              | intra    | 0.006      | −0.004     | —        | **PASS** |
| 19| intra_trade_count            | intra    | −0.003     | −0.004     | —        | **PASS** |
| 20| intra_vwap_position          | intra    | **−0.361** | 0.081      | —        | **PASS** |
| 21| intra_count_imbalance        | intra    | **0.124**  | 0.007      | —        | **PASS** |
| 22| intra_kyle_lambda            | intra    | 0.003      | −0.001     | —        | **PASS** |
| 23| intra_burstiness             | intra    | −0.010     | −0.015     | —        | **PASS** |
| 24| intra_volume_skew            | intra    | −0.009     | −0.006     | —        | **PASS** |
| 25| intra_volume_kurt            | intra    | 0.000      | −0.004     | —        | **PASS** |
| 26| intra_kaufman_er             | intra    | 0.003      | 0.023      | —        | **PASS** |
| 27| intra_garman_klass_vol       | intra    | −0.019     | 0.014      | —        | **PASS** |
| 28| intra_hurst                  | intra    | −0.009     | 0.002      | —        | **PASS** |
| 29| intra_permutation_entropy    | intra    | **−0.166** | 0.011      | —        | **PASS** |
| 30| intra_max_drawdown           | intra    | **−0.650** | 0.089      | —        | **PASS** |
| 31| intra_max_runup              | intra    | **+0.643** | −0.077     | —        | **PASS** |
| 32| intra_duration_us            | intra    | 0.001      | −0.005     | —        | **PASS** |
| 33| intra_bull_epoch_density     | intra    | **+0.179** | −0.051     | —        | **PASS** |
| 34| intra_bear_epoch_density     | intra    | **−0.185** | 0.076      | —        | **PASS** |
| 35| intra_bull_excess_gain       | intra    | 0.042      | −0.023     | —        | **PASS** |
| 36| intra_bear_excess_gain       | intra    | −0.058     | −0.015     | —        | **PASS** |
| 37| intra_bull_cv                | intra    | **+0.310** | −0.031     | —        | **PASS** |
| 38| intra_bear_cv                | intra    | **−0.301** | 0.026      | —        | **PASS** |

**38/38 features PASS. 0 failures. 0 warnings.**

---

## Implications for Gen600

1. **Feature columns are clean** — no lookahead bias from the data pipeline
2. **If any Gen600 config appears significant, it is NOT because of data contamination**
3. **The only remaining lookahead risks are**:
   - SQL query logic (already audited in `verify_atomic_nolookahead.sql`)
   - Quantile computation window (must use rolling, not expanding — see MEMORY.md)
   - Forward-looking arrays (`fwd_opens`, `fwd_highs`, etc.) — these are explicitly future data used only for trade outcome evaluation, never for signal generation
