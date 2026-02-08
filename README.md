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

**Verdict**: DEAD as standalone strategy. Use as ML/NN feature input only. Zero configs survive any multiple testing framework (Bonferroni, e-BH, Romano-Wolf, DSR).

## Quick Start

```bash
# List all SQL pattern files
mise run sql:list

# Reproduce champion pattern on local ClickHouse
mise run sql:reproduce

# Run backtest
mise run backtest:run

# Run validation tests
mise run test
```

## Structure

```
sql/          ClickHouse SQL pattern discovery (22 generations)
findings/     Research analysis documents (chronological)
issues/       GitHub issue snapshots (durable local records)
backtest/     backtesting.py + NautilusTrader integration
designs/      NN experiment designs
tmp/          Beyond-Kelly evaluation metrics POC
src/          Python validation package
tests/        Validation tests
```

## Setup

1. Install [mise](https://mise.jdx.dev/) and run `mise install`
2. Set up ClickHouse access:
   - **Local**: Install ClickHouse and sync data with `mise run ch:sync`
   - **Remote**: Create `.mise.local.toml` (gitignored) with your SSH host:

     ```toml
     [env]
     RANGEBAR_CH_HOST = "your-clickhouse-host"
     ```

3. For GitHub releases, add tokens to `.mise.local.toml`:

   ```toml
   [env]
   GH_TOKEN = "your-token"
   GITHUB_TOKEN = "your-token"
   ```

## Requirements

- Python 3.13+
- ClickHouse (local or remote via SSH tunnel)
- [mise](https://mise.jdx.dev/) for task management

## License

MIT
