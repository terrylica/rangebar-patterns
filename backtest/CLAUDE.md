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

## Data Loading

Both frameworks load range bars from BigBlack ClickHouse:

```
ssh bigblack 'clickhouse-client'
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
