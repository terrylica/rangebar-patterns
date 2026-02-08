# Experiment 082: Long-Only Mean Reversion NN

**Date**: 2026-02-05
**Status**: DESIGN COMPLETE - Ready for Implementation
**GitHub Issue**: #129
**Predecessor**: Brute-force microstructure analysis (Gen 108-110)

---

## Executive Summary

exp082 implements a neural network that learns the champion pattern discovered through brute-force analysis:

**Champion Pattern**: `2 consecutive DOWN bars + trade_intensity > p95 + kyle_lambda > 0 → LONG`

Key innovation: **Long-only selective trading** - the model can only go LONG or abstain (no shorts).

---

## Hypothesis

**H1**: A BiLSTM can learn the mean reversion + microstructure pattern better than the fixed rule
**H2**: Neural network can capture nuanced variations the fixed rule misses
**H3**: Long-only constraint improves performance (shorts consistently lose on SOL)

**Expected Performance**:

- Baseline (random): 50% directional accuracy
- Fixed rule: 66.76% (no-lookahead validated)
- NN target: 55-65% (lower edge but more samples)

---

## Design Based on Brute-Force Findings

### Key Discoveries (Gen 108-110)

| Finding                                  | Implication for NN                                  |
| ---------------------------------------- | --------------------------------------------------- |
| 2 DOWN bars predict UP                   | Use `direction(t-1)`, `direction(t-2)` as features  |
| Trade intensity > p95 filters noise      | Use `trade_intensity_z` (z-scored for stationarity) |
| Kyle lambda > 0 confirms buying pressure | Use `kyle_lambda_z` (z-scored for stationarity)     |
| SHORT signals lose money                 | **LONG-ONLY gate** - never predict short            |
| ETH is inverted                          | Train on SOL only, validate on BTC/BNB              |
| Pattern decays over time (82%→52%)       | Use rolling percentiles, not fixed                  |

### Feature Engineering

**Primary Features (8 features)**:

| Feature             | Type           | Description                    | Range        |
| ------------------- | -------------- | ------------------------------ | ------------ |
| `returns_vs`        | Price          | Vol-standardized returns       | [-4, 4]      |
| `direction_lag1`    | Direction      | 1 if prev bar UP, 0 if DOWN    | {0, 1}       |
| `direction_lag2`    | Direction      | 2 bars ago direction           | {0, 1}       |
| `down_streak`       | Pattern        | Count of consecutive DOWN bars | [0, seq_len] |
| `trade_intensity_z` | Microstructure | Log intensity, z-scored        | [-4, 4]      |
| `kyle_lambda_z`     | Microstructure | Kyle lambda, z-scored          | [-4, 4]      |
| `ti_above_p90`      | Regime         | 1 if intensity > rolling p90   | {0, 1}       |
| `kyle_positive`     | Direction      | 1 if kyle > 0                  | {0, 1}       |

**Why these features**:

- `direction_lag1/2` + `down_streak`: Captures mean reversion setup
- `trade_intensity_z` + `ti_above_p90`: Filters to high-conviction bars
- `kyle_lambda_z` + `kyle_positive`: Confirms buying pressure despite DOWN bars
- `returns_vs`: General price context

### Model Architecture: Long-Only BiLSTM

```
Input (batch, seq_len, 8 features)
          ↓
      BiLSTM(64)
          ↓
     ┌────┴────┐────────┐
     ↓         ↓        ↓
  HEAD 1    HEAD 2   HEAD 3
  (pred)    (gate)   (aux)
     ↓         ↓        ↓
  sigmoid   sigmoid  sigmoid
  [0,1]     [0,1]    [0,1]
     ↓         ↓
   × gate      │
     ↓         │
  LONG only  abstain
  (pred>0.5) (gate<0.5)
```

**Key Modification: Long-Only Gate**

Standard SelectiveNet: `output = gate * sign(pred)` → can be LONG (+1) or SHORT (-1)

Long-Only: `output = gate * 1 if pred > 0.5 else 0` → can only be LONG (+1) or FLAT (0)

Implementation in loss function:

```python
# Long-only: Position is +1 (long) if gate > 0.5, else 0 (flat)
# No short positions allowed
position = gate * (pred > 0.5).float()  # Binary: 1 or 0
pnl = position * returns  # Positive returns when correct long, 0 when flat
```

### Rolling Percentile Computation (No Lookahead)

**Critical**: Use expanding window percentiles, NOT full-dataset percentiles.

```python
def compute_rolling_percentiles(df: pd.DataFrame, lookback: int = 1000) -> pd.DataFrame:
    """Compute rolling p90/p95 without lookahead."""
    df['ti_p90_rolling'] = df['trade_intensity'].rolling(lookback, min_periods=100).quantile(0.90)
    df['ti_p95_rolling'] = df['trade_intensity'].rolling(lookback, min_periods=100).quantile(0.95)
    df['ti_above_p90'] = (df['trade_intensity'] > df['ti_p90_rolling'].shift(1)).astype(float)
    df['ti_above_p95'] = (df['trade_intensity'] > df['ti_p95_rolling'].shift(1)).astype(float)
    return df
```

The `.shift(1)` is crucial - we compare current intensity to PRIOR percentile.

---

## Experimental Arms

| Arm    | Features        | Gate Type     | Description                          |
| ------ | --------------- | ------------- | ------------------------------------ |
| **A0** | Baseline v2 (9) | Standard      | Control - no microstructure          |
| **A1** | Champion (8)    | **Long-only** | Full champion pattern features       |
| **A2** | Simple (6)      | **Long-only** | Direction + kyle only (no intensity) |
| **A3** | Champion (8)    | Standard      | Long-only hypothesis test            |

**Arm A1 vs A3**: Tests whether long-only constraint improves performance.

---

## Loss Function: LongOnlySelectiveTradingLoss

New loss function that only rewards long positions:

```python
class LongOnlySelectiveTradingLoss(nn.Module):
    """Selective trading loss for long-only strategies.

    Key differences from standard SelectiveTradingLoss:
    1. Position is always 0 or +1 (never -1)
    2. Returns are only earned when gate AND pred both > 0.5
    3. Coverage constraint applies to long entries only
    """

    def forward(self, pred, gate, returns, aux_pred=None):
        # Long-only position: +1 if gate active AND pred suggests up
        pred_up = (pred > 0.5).float()  # 1 if predicting UP
        position = gate * pred_up  # Only long when both active

        # PnL: returns * position (0 when flat, returns when long)
        pnl = position * returns

        # Coverage: fraction of bars where we go LONG
        long_coverage = position.mean()

        # Sortino: penalize downside only
        downside = torch.clamp(-pnl, min=0)
        downside_std = torch.sqrt(torch.mean(downside ** 2) + 1e-8)
        mean_pnl = pnl.mean()
        sortino = mean_pnl / downside_std

        # Coverage constraint (long-only)
        coverage_gap = torch.clamp(self.min_long_coverage - long_coverage, min=0)
        coverage_loss = self.lambda_coverage * coverage_gap ** 2

        # Auxiliary loss (on ALL predictions, not just longs)
        aux_loss = self.lambda_aux * F.mse_loss(aux_pred, returns.sign())

        return -sortino + coverage_loss + aux_loss
```

---

## WFO Configuration

Based on exp078 findings (val_bars=1200 optimal for SOL):

| Parameter           | Value   | Rationale                            |
| ------------------- | ------- | ------------------------------------ |
| symbol              | SOLUSDT | Primary asset (most samples)         |
| threshold           | 1000    | 10% range bars (matches brute-force) |
| train_bars          | 2800    | Validated in exp078                  |
| val_bars            | 1200    | exp078 winner for SOL                |
| test_bars           | 560     | Standard                             |
| gap_bars            | 50      | exp077: ACF gap was worse            |
| n_origins           | 8       | Statistical parity                   |
| seeds               | 10      | 43-52                                |
| max_epochs          | 800     | Wide range for frontier              |
| checkpoint_interval | 10      | 80 checkpoints                       |

---

## Metrics

**Primary** (same as brute-force):

- Directional Edge: accuracy - 0.5
- Profit Factor: sum(wins) / abs(sum(losses))
- Kelly Edge: win_rate - (1-win_rate) \* (avg_loss/avg_win)

**Secondary**:

- Long coverage: fraction of bars where model goes long
- Abstention rate: fraction of bars where gate < 0.5
- Long accuracy: accuracy on bars where model went long

---

## Expected Results

| Arm | Expected Edge | Expected Coverage | Notes                     |
| --- | ------------- | ----------------- | ------------------------- |
| A0  | 1-2%          | 50%               | Baseline control          |
| A1  | **8-12%**     | 10-20%            | Champion pattern          |
| A2  | 2-4%          | 30-50%            | Simpler, more samples     |
| A3  | 5-8%          | 15-25%            | Standard gate (can short) |

**Success Criteria**:

- A1 directional edge > 5% (z > 2)
- A1 > A0 with p < 0.05
- A1 long-only >= A3 standard gate

---

## Implementation Steps

1. **Create `exp082_mean_reversion_long.py`** (copy from exp078_sol_validation_sweep.py)
2. **Add feature computation** for direction lookback and rolling percentiles
3. **Implement LongOnlySelectiveTradingLoss** in models/
4. **Add arm configurations** for A0-A3
5. **Dry run** on remote GPU workstation with 1 seed
6. **Full run** all arms

---

## Files to Create/Modify

| File                            | Action | Purpose                                     |
| ------------------------------- | ------ | ------------------------------------------- |
| `exp082_mean_reversion_long.py` | NEW    | Main experiment script                      |
| `models/long_only_loss.py`      | NEW    | Long-only loss function                     |
| `exp082_features.py`            | NEW    | Feature computation with direction lookback |

---

## Risks and Mitigations

| Risk                              | Impact                     | Mitigation                                 |
| --------------------------------- | -------------------------- | ------------------------------------------ |
| Pattern decay (2024 edge was 52%) | Low edge in recent data    | Use rolling percentiles, not fixed         |
| Overfitting to mean reversion     | False positives            | Maintain coverage constraint               |
| Small sample size (713 signals)   | High variance              | Use simple pattern (18K signals) as backup |
| Cross-asset generalization        | BTC/BNB different dynamics | Validate on BTC/BNB separately             |

---

## Decision Log

| Decision                    | Rationale                                    |
| --------------------------- | -------------------------------------------- |
| Long-only gate              | Shorts consistently lose on SOL (Gen2, Gen5) |
| Rolling percentiles         | Avoid lookahead bias (Gen108 lesson)         |
| 8 features (not 9 baseline) | Champion pattern is parsimonious             |
| SOL primary                 | Most samples, strongest edge                 |
| val_bars=1200               | exp078 winner for SOL                        |
