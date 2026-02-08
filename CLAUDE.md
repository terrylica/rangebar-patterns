# CLAUDE.md - Range Bar Patterns

Range bar pattern discovery via ClickHouse SQL brute-force analysis of microstructure features.

**Architecture**: Link Farm + Hub-and-Spoke with Progressive Disclosure

---

## Documentation Hierarchy

```
CLAUDE.md (this file)            <-- Hub: Navigation + Essentials
    |
    +-- sql/CLAUDE.md            <-- Spoke: SQL guide, generations, ClickHouse
    +-- logs/CLAUDE.md           <-- Spoke: Telemetry archive conventions
    +-- scripts/CLAUDE.md        <-- Spoke: Sweep script patterns + pueue
    +-- findings/CLAUDE.md       <-- Spoke: Research findings index
    +-- issues/CLAUDE.md         <-- Spoke: GitHub issue snapshots
    +-- backtest/CLAUDE.md       <-- Spoke: backtesting.py + NautilusTrader
    +-- designs/CLAUDE.md        <-- Spoke: NN experiment designs
    +-- tmp/beyond-kelly-poc/CLAUDE.md  <-- Spoke: Evaluation metrics POC
```

## Navigation

| Topic              | Document                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------- |
| SQL Patterns       | [sql/CLAUDE.md](/sql/CLAUDE.md)                                                           |
| Telemetry Logs     | [logs/CLAUDE.md](/logs/CLAUDE.md)                                                         |
| Sweep Scripts      | [scripts/CLAUDE.md](/scripts/CLAUDE.md)                                                   |
| Research Findings  | [findings/CLAUDE.md](/findings/CLAUDE.md)                                                 |
| GitHub Issues      | [issues/CLAUDE.md](/issues/CLAUDE.md)                                                     |
| Backtesting        | [backtest/CLAUDE.md](/backtest/CLAUDE.md)                                                 |
| NN Designs         | [designs/CLAUDE.md](/designs/CLAUDE.md)                                                   |
| Evaluation Metrics | [tmp/beyond-kelly-poc/CLAUDE.md](/tmp/beyond-kelly-poc/CLAUDE.md)                         |
| Repository ADR     | [docs/adr/2026-02-06-repository-creation.md](/docs/adr/2026-02-06-repository-creation.md) |

---

## Champion Pattern (TRUE No-Lookahead)

`2 consecutive DOWN bars + trade_intensity > p95_expanding + kyle_lambda > 0 -> LONG`

| Metric         | Value                         |
| -------------- | ----------------------------- |
| Hit Rate       | 62.93% (TRUE NLA)             |
| Z-Score        | 8.25                          |
| DSR (N=111)    | 1.000                         |
| 2024-2025      | NOT significant (z=0.87-1.24) |
| Gen300 Filters | No feature filter rescues it  |
| Gen500 X-Asset | NOT cross-asset consistent    |

**Verdict**: DEAD as standalone strategy. Use as ML/NN feature input only.

---

## Evaluation Metrics (5-Metric Stack)

| Metric | Role               | Threshold      |
| ------ | ------------------ | -------------- |
| Kelly  | Primary ranker     | > 0            |
| Omega  | Distribution shape | > 1.0          |
| DSR    | Multiple testing   | > 0.95 (N-adj) |
| MinBTL | Data sufficiency   | n >= MinBTL    |
| PBO    | Overfitting detect | < 0.50         |

**Dropped** (r > 0.95 redundant with Omega): Sharpe, PSR, GROW, CF-ES

**Dropped** (insufficient evidence): E-values (max=1.04, need >= 20)

Decision: [Issue #12](https://github.com/terrylica/rangebar-patterns/issues/12) | POC: `tmp/beyond-kelly-poc/`

---

## Research Verdict

- **0 configs survive** any multiple testing framework (Bonferroni, e-BH, Romano-Wolf, DSR)
- **Gen300**: Feature filters don't rescue champion (best Kelly +0.011, none pass Bonferroni)
- **Gen500**: Cross-asset inconsistency — best SOLUSDT configs fail on other assets
- **Gen510**: Barrier optimization helps (Kelly +0.157 with TP=0.25x SL=0.50x) but not significant
- **PBO**: 0.3286 (marginal — between overfitting and not)
- **Path forward**: Champion pattern as ML feature input, not standalone strategy

---

## Essential Commands

| Task               | Command                                                 |
| ------------------ | ------------------------------------------------------- |
| Run tests          | `mise run test`                                         |
| List SQL files     | `mise run sql:list`                                     |
| Run SQL (local)    | `mise run sql:run file=sql/gen111_true_nolookahead.sql` |
| Reproduce champion | `mise run sql:reproduce`                                |
| Backtest champion  | `mise run backtest:run`                                 |
| Release            | `mise run release:full`                                 |

---

## Infrastructure

Queries run against ClickHouse (local or remote via SSH tunnel):

- Database: `rangebar_cache`
- Table: `range_bars`
- Column: `threshold_decimal_bps` (NOT threshold_dbps)
- Remote host: Set `RANGEBAR_CH_HOST` in `.mise.local.toml`

---

## Key Files

| File                                                   | Purpose                                 |
| ------------------------------------------------------ | --------------------------------------- |
| `src/rangebar_patterns/champion.py`                    | Champion pattern constants (SSoT)       |
| `sql/gen111_true_nolookahead.sql`                      | Production-ready pattern query          |
| `sql/verify_atomic_nolookahead.sql`                    | Forensic audit (expanding window proof) |
| `findings/2026-02-05-production-readiness-audit.md`    | Audit verdict: CONDITIONAL GO           |
| `designs/exp082-long-only-meanrev-nn.md`               | NN design using champion features       |
| `tmp/beyond-kelly-poc/results/verdict.md`              | Beyond-Kelly POC final verdict          |
| `tmp/beyond-kelly-poc/results/rank_correlations.jsonl` | Metric redundancy evidence (Spearman r) |
