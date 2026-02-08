# Backtesting - AI Context

**Scope**: Wire range bar champion patterns into backtesting frameworks for PnL validation.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Two Frameworks

| Framework      | Path              | Use Case                 | Range Bar Support  |
| -------------- | ----------------- | ------------------------ | ------------------ |
| backtesting.py | `backtesting_py/` | Research, fast iteration | Native (DataFrame) |
| NautilusTrader | `nautilus/`       | Production, live trading | Custom adapter     |

## Recommended Workflow

1. Develop + validate in **backtesting.py** (fast iteration, 5-line setup)
2. Once strategy is stable, port to **NautilusTrader** for live testing

## Champion Strategy Logic

```
IF 2 consecutive DOWN bars
AND trade_intensity > p95_expanding
AND kyle_lambda > 0
THEN -> LONG (hold 1 bar)
ELSE -> FLAT (no position)
```

No SHORT signals (they lose on SOL).

**Verdict**: DEAD as standalone strategy. Use as ML/NN feature input only. No configs survive multiple testing (Bonferroni, e-BH, Romano-Wolf, DSR). See [Issue #12](https://github.com/terrylica/rangebar-patterns/issues/12).

## Triple Barrier Framework (Gen200-202)

Exit logic uses triple barrier method:

| Barrier     | Best Config (Gen510) | Description             |
| ----------- | -------------------- | ----------------------- |
| Take Profit | 0.25x threshold      | Tight TP captures edge  |
| Stop Loss   | 0.50x threshold      | Wide SL avoids whipsaws |
| Max Bars    | 100                  | Time-based expiry       |

- **Gen200**: PF=1.27 @500dbps (97/100 combos > 1.0)
- **Gen201**: Trailing stop adds no value (PF=1.26 vs 1.27)
- **Gen510**: Barrier optimization: Kelly +0.157 (3.8x improvement over default barriers)

**Key insight**: Asymmetric barriers (tight TP, wide SL) suit mean-reversion patterns.

## Evaluation Metrics (5-Metric Stack)

All backtesting results should be evaluated with:
Kelly > 0, Omega > 1.0, DSR > 0.95, n >= MinBTL, PBO < 0.50

See [Root CLAUDE.md](/CLAUDE.md) for full metric stack details.

## Data Loading

Both frameworks load range bars from ClickHouse (local or remote via SSH tunnel):

```
clickhouse-client
SELECT * FROM rangebar_cache.range_bars
WHERE symbol = 'SOLUSDT' AND threshold_decimal_bps = 250
```

## Existing Reference Implementations

| File                                                 | Framework      | Repo              |
| ---------------------------------------------------- | -------------- | ----------------- |
| rangebar-py/examples/backtesting_integration.py      | backtesting.py | rangebar-py       |
| KMeansTransformer/backtest/nautilus_strategy_fast.py | NautilusTrader | KMeansTransformer |

## Dependencies

```bash
# backtesting.py (lightweight)
uv pip install backtesting

# NautilusTrader (heavy, needs Rust backend)
uv pip install nautilus_trader
```
