# CLAUDE.md - Range Bar Patterns

Range bar pattern discovery via ClickHouse SQL brute-force analysis of microstructure features.

**Architecture**: Link Farm + Hub-and-Spoke with Progressive Disclosure

---

## Documentation Hierarchy

```
CLAUDE.md (this file)        <-- Hub: Navigation + Essentials
    |
    +-- sql/CLAUDE.md        <-- Spoke: SQL guide, generations, ClickHouse
    +-- logs/CLAUDE.md       <-- Spoke: Telemetry archive conventions
    +-- scripts/CLAUDE.md    <-- Spoke: Sweep script patterns + pueue
    +-- findings/CLAUDE.md   <-- Spoke: Research findings index
    +-- issues/CLAUDE.md     <-- Spoke: GitHub issue snapshots
    +-- backtest/CLAUDE.md   <-- Spoke: backtesting.py + NautilusTrader
    +-- designs/CLAUDE.md    <-- Spoke: NN experiment designs
```

## Navigation

| Topic             | Document                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------- |
| SQL Patterns      | [sql/CLAUDE.md](/sql/CLAUDE.md)                                                           |
| Telemetry Logs    | [logs/CLAUDE.md](/logs/CLAUDE.md)                                                         |
| Sweep Scripts     | [scripts/CLAUDE.md](/scripts/CLAUDE.md)                                                   |
| Research Findings | [findings/CLAUDE.md](/findings/CLAUDE.md)                                                 |
| GitHub Issues     | [issues/CLAUDE.md](/issues/CLAUDE.md)                                                     |
| Backtesting       | [backtest/CLAUDE.md](/backtest/CLAUDE.md)                                                 |
| NN Designs        | [designs/CLAUDE.md](/designs/CLAUDE.md)                                                   |
| Repository ADR    | [docs/adr/2026-02-06-repository-creation.md](/docs/adr/2026-02-06-repository-creation.md) |

---

## Champion Pattern (TRUE No-Lookahead)

`2 consecutive DOWN bars + trade_intensity > p95_expanding + kyle_lambda > 0 -> LONG`

| Metric      | Value                         |
| ----------- | ----------------------------- |
| Hit Rate    | 62.93% (TRUE NLA)             |
| Z-Score     | 8.25                          |
| DSR (N=111) | 1.000                         |
| 2024-2025   | NOT significant (z=0.87-1.24) |

**Verdict**: Use as NN FEATURE, not standalone signal.

---

## Essential Commands

| Task                | Command                                                 |
| ------------------- | ------------------------------------------------------- |
| Run tests           | `mise run test`                                         |
| List SQL files      | `mise run sql:list`                                     |
| Run SQL on BigBlack | `mise run sql:run file=sql/gen111_true_nolookahead.sql` |
| Reproduce champion  | `mise run sql:reproduce`                                |
| Backtest champion   | `mise run backtest:run`                                 |
| Release             | `mise run release:full`                                 |

---

## Infrastructure

Queries run against **BigBlack** ClickHouse:

- Database: `rangebar_cache`
- Table: `range_bars`
- Column: `threshold_decimal_bps` (NOT threshold_dbps)
- Connection: `ssh bigblack 'clickhouse-client'`

---

## Key Files

| File                                                | Purpose                                 |
| --------------------------------------------------- | --------------------------------------- |
| `src/rangebar_patterns/champion.py`                 | Champion pattern constants (SSoT)       |
| `sql/gen111_true_nolookahead.sql`                   | Production-ready pattern query          |
| `sql/verify_atomic_nolookahead.sql`                 | Forensic audit (expanding window proof) |
| `findings/2026-02-05-production-readiness-audit.md` | Audit verdict: CONDITIONAL GO           |
| `designs/exp082-long-only-meanrev-nn.md`            | NN design using champion features       |
