# rangebar-patterns

Range bar pattern discovery via ClickHouse SQL brute-force analysis of microstructure features.

## Champion Pattern (TRUE No-Lookahead)

```
2 consecutive DOWN bars + trade_intensity > p95_expanding + kyle_lambda > 0 -> LONG
```

| Metric      | Value                         |
| ----------- | ----------------------------- |
| Hit Rate    | 62.93% (TRUE NLA)             |
| Z-Score     | 8.25                          |
| DSR (N=111) | 1.000                         |
| 2024-2025   | NOT significant (z=0.87-1.24) |

**Verdict**: Use as NN FEATURE, not standalone signal.

## Quick Start

```bash
# List all SQL pattern files
mise run sql:list

# Reproduce champion pattern on BigBlack ClickHouse
mise run sql:reproduce

# Run backtest
mise run backtest:run

# Run validation tests
mise run test
```

## Structure

```
sql/          ClickHouse SQL pattern discovery (15 files, 8 generations + NLA corrections)
findings/     Research analysis documents (chronological)
issues/       GitHub issue snapshots (durable local records)
backtest/     backtesting.py + NautilusTrader integration
designs/      NN experiment designs
src/          Python validation package
tests/        Validation tests
```

## Infrastructure

Queries run against **BigBlack** ClickHouse:

- Database: `rangebar_cache`
- Table: `range_bars`
- Column: `threshold_decimal_bps` (NOT threshold_dbps)

## Requirements

- Python 3.13+
- ClickHouse access (BigBlack via SSH)
- [mise](https://mise.jdx.dev/) for task management

## License

MIT
