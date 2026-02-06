# exp079: SOL Rich Per-Bar Telemetry

**Source**: EonLabs-Spartan/alpha-forge#130
**State**: open
**Labels**: (none)
**Exported**: 2026-02-06

---

## Summary

exp079 implements rich per-bar telemetry for SOL trading simulation, enabling:
- Bar-by-bar PnL reconstruction without lookahead bias
- Streak detection (max consecutive losses/wins)
- % Profit metric based on range bar threshold (2.5% per bar)
- Bayesian credible intervals for statistical rigor

## Experimental Arms

| Arm | train_bars | Purpose |
|-----|------------|---------|
| T1 | 2000 | Shorter training window |
| T2 | 2800 | Baseline (exp078 default) |
| T3 | 4000 | Longer training window |

## Fixed Parameters (from exp078-SOL)

- `val_bars=1200` (43% of train, exp078 winner)
- `gap_bars=50` (hardcoded, ACF was worse)
- `n_origins=8` (statistical parity)
- `test_bars=560`

## Per-Bar Telemetry (21 fields)

**Tier 1 (13 fields)**: timestamp, duration, OHLCV, actual return/direction, prediction raw/binary/direction, gate probability

**Tier 2 (8 fields)**: is_active, position, pnl_pct, cumulative_pnl, equity, drawdown_pct, is_correct

## New Metrics

- `max_loss_streak`: Longest consecutive losing bars
- `max_win_streak`: Longest consecutive winning bars  
- `pct_profit`: (n_correct - n_wrong) x threshold%
- Bayesian credible intervals via `scipy.stats.bayes_mvs`

## Files

- `examples/research/exp079_metrics.py` - Telemetry and metric functions
- `examples/research/exp079_sol_rich_telemetry.py` - Main experiment script

## Predecessor

- exp078: Validation sizing sweep (found val_bars=1200 optimal for SOL)

## Execution

Run on BigBlack (RTX 4090):
```bash
ssh bigblack "cd ~/alpha-forge-research/examples/research && uv run python exp079_sol_rich_telemetry.py --arm all"
```

Estimated runtime: ~24 hours (3 arms x 8 origins x 10 seeds)

---

## Comments

(no comments)
