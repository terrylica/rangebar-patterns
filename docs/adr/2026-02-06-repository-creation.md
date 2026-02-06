# ADR: rangebar-patterns Repository Creation

**Date**: 2026-02-06
**Status**: Accepted

## Context

All brute-force range bar pattern discovery research (14 SQL files, 8+ findings documents,
GitHub issue insights) lived scattered inside the alpha-forge research worktree at
`examples/research/`. This research is completely independent of alpha-forge's core
functionality (DSL compiler, plugin system, etc.).

## Decision

Create a dedicated repository `terrylica/rangebar-patterns` to house:

1. **SQL pattern discovery** - 15 ClickHouse SQL files across 8 generations + NLA corrections
2. **Research findings** - 7 analysis documents from brute-force pattern discovery
3. **GitHub issue snapshots** - 5 durable local records of research findings
4. **Backtesting scaffolding** - backtesting.py (research) + NautilusTrader (production)
5. **NN experiment designs** - BiLSTM design based on champion pattern features
6. **Python validation** - Champion pattern constants and SQL reproduction tests

## Consequences

### Positive

- Clean separation of concern - pattern research has no alpha-forge dependency
- Reproducibility - SQL queries runnable against ClickHouse to recreate findings
- Future research home - new range bar pattern work goes here, not alpha-forge
- Knowledge preservation - GitHub issue findings saved as local durable artifacts

### Negative

- Research artifacts now split across two repos (alpha-forge retains ML experiment scripts)
- Need to maintain ClickHouse connection to BigBlack for SQL reproduction

### Not Migrated

These files stay in alpha-forge because they depend on alpha-forge infrastructure:

- `exp079_metrics.py`, `exp079_sol_rich_telemetry.py` (WFO experiment)
- `exp080_derived_features.py`, `exp081_microstructure_sweep.py` (ML experiments)
- All `wfo/`, `training/`, `models/`, `infra/` modules
