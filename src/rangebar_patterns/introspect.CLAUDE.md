# introspect — Atomic Trade Reconstruction

**Navigation**: [Root CLAUDE.md](/CLAUDE.md) | [Eval Metrics](/src/rangebar_patterns/eval/CLAUDE.md) | [Issue #13](https://github.com/terrylica/rangebar-patterns/issues/13)

---

## What This Does (Plain English)

Imagine you ran 1,008 trading strategies and one says "I made money on 370 trades." But **which** trades? **Why** did each one win or lose? This tool lets you pick any single trade and watch it unfold bar-by-bar — like slow-motion replay of a sports play.

For each trade you see:

- **Why it fired** — which microstructure features passed their quantile thresholds
- **How it played out** — bar-by-bar distance to take-profit and stop-loss barriers
- **Where it exited** — the exact bar where a barrier was hit (or time ran out)

---

## How It Works (The Big Picture)

```
YOU TYPE:                                    YOU SEE:

  RBP_INSPECT_CONFIG_ID=                     ══════════════════════════
    price_impact_lt_p10__                      Trade #4 / 370
    volume_per_trade_gt_p75                  ══════════════════════════
  RBP_INSPECT_TRADE_N=4                        Config: price_impact...
  mise run trade:inspect                       Entry:  3.0876
                                               Exit:   3.0490 (SL)
         |                                     P&L:   -1.25%
         v                                     Bars:   5 / 50 max

  +------------------+                       Feature Diagnostic:
  | parse_config_id  |  Decode the             price_impact  YES
  | "what strategy?" |  strategy name          volume_per_t  YES
  +--------+---------+
           |                                 Barrier Progression:
           v                                   Bar  Open   ...  ->SL
  +------------------+                           1  3.087  ... +0.006
  | build_inspect_sql|  Build SQL query          2  3.055  ... +0.006
  | for ClickHouse   |  (2 queries)              3  3.087  ... +0.017
  +--------+---------+                           4  3.055  ... +0.005
           |                                     5  3.085  ... HIT SL
           v
  +------------------+
  | SSH Tunnel to    |  Connect to
  | ClickHouse       |  bigblack server
  +--------+---------+
           |
           v
  +------------------+
  | Query 1: trade   |  Get all 370 trades
  | list (pick #4)   |  for this strategy
  +--------+---------+
           |
           v
  +------------------+
  | Query 2: bar-by- |  Expand trade #4
  | bar detail        |  into 5 rows (bars)
  +------------------+
```

---

## File Map

```
rangebar-patterns/
  |
  +-- src/rangebar_patterns/
  |     |
  |     +-- introspect.py        <-- THIS MODULE (parse + query + render)
  |     +-- config.py            <-- Reads RBP_* env vars (symbol, barriers)
  |     |
  |     +-- eval/
  |           +-- extraction.py  <-- Shares: _CTE_TEMPLATE, FEATURES, GRID
  |
  +-- .mise/tasks/
  |     +-- trade.toml           <-- Defines "mise run trade:inspect"
  |
  +-- .mise.toml                 <-- Sets env vars (symbol, threshold, barriers)
  +-- .mise.local.toml           <-- Sets RANGEBAR_CH_HOST=bigblack (gitignored)
  |
  +-- backtest/backtesting_py/
  |     +-- ssh_tunnel.py        <-- SSHTunnel class (reused for ClickHouse)
  |
  +-- tests/
        +-- test_introspect.py   <-- 14 tests (parse + SQL + render)
```

### What Each File Does

| File                 | Role                                                                                                       | Analogy                                    |
| -------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `introspect.py`      | The whole tool — parses config, builds SQL, queries ClickHouse, renders output                             | The entire sports replay system            |
| `extraction.py`      | Provides the shared SQL template (`_CTE_TEMPLATE`) that builds 10 CTEs from raw bar data to trade outcomes | The stadium (shared infrastructure)        |
| `config.py`          | Reads `RBP_*` environment variables into typed Python constants                                            | The settings panel                         |
| `ssh_tunnel.py`      | Creates an SSH tunnel so your laptop can reach ClickHouse on bigblack                                      | The cable connecting your TV to the camera |
| `trade.toml`         | One-line mise task definition so you can type `mise run trade:inspect`                                     | The remote control button                  |
| `test_introspect.py` | 14 automated tests: 6 for parsing, 4 for SQL, 4 for rendering                                              | Quality control                            |

---

## The SQL Pipeline (What Happens Inside ClickHouse)

The tool reuses the same SQL CTE chain as the evaluation pipeline. Think of it as 10 stages of data processing, each feeding into the next:

```
Stage 1    base_bars           Raw OHLC bars from the database
              |                (filtered by symbol + threshold)
              v
Stage 2    running_stats       Add rolling p95 of trade_intensity
              |                (1000-bar window, no lookahead)
              v
Stage 3    signal_detection    Compute lagged features for each bar
              |                (what happened 1-2 bars ago?)
              v
Stage 4    champion_signals    Filter: 2 DOWN bars + high intensity + kyle > 0
              |                (~3000 signals from ~200,000 bars)
              v
Stage 5    feature1_quantile   Compute rolling quantile for feature 1
              |                (within champion signals only)
              v
Stage 6    feature2_quantile   Compute rolling quantile for feature 2
              |
              v
Stage 7    signals             Apply feature filters (e.g., price_impact < p10)
              |                (~370 signals that pass both filters)
              v
Stage 8    forward_arrays      For each signal, collect next 50 bars as arrays
              |                (fwd_opens, fwd_highs, fwd_lows, fwd_closes)
              v
Stage 9    barrier_scan        Compute TP/SL prices, find which bar hits first
              |                (arrayFirstIndex for barrier detection)
              v
Stage 10   trade_outcomes      Determine exit type (TP/SL/TIME) and exit price
              |
              v
         +---------+
    QUERY 1: trade_list         "Give me all 370 trades, numbered"
    QUERY 2: trade_detail       "Give me bar-by-bar for trade #4"
         +---------+
```

**Query 1** (trade list) just reads from `trade_outcomes`.
**Query 2** (trade detail) joins `signals` + `param_with_prices` + `trade_outcomes` + a subquery that computes the exact exit bar, then uses `ARRAY JOIN` to expand the forward arrays into individual bar rows.

---

## The Three Output Sections

### 1. Trade Summary

Shows the big picture: which strategy, which asset, when, entry/exit, P&L, how many bars.

```
══════════════════════════════════════════════════
  Trade #4 / 370
══════════════════════════════════════════════════
  Config:  price_impact_lt_p10__volume_per_trade_gt_p75
  Symbol:  SOLUSDT @500dbps
  Signal:  2020-08-18 00:33:16 UTC
  Entry:   3.087600 -> Exit: 3.049005 (SL)
  P&L:     -1.2500%
  Bars:    5 / 50 max
```

### 2. Feature Diagnostic

Shows **why** this trade was taken. Each feature must pass its quantile threshold. Both must say YES for the signal to fire.

```
Feature Diagnostic:
  Feature                          Value     Threshold  Quantile  Filter  Pass
  ------------------------- ------------  ------------  --------  ------  ----
  price_impact                  0.000002      0.000003       p10       <   YES
  volume_per_trade            218.297059    137.246696       p75       >   YES
```

Reading this: "price_impact was 0.000002, which is below the rolling p10 threshold of 0.000003 — that means unusually low price impact, so the filter passes."

### 3. Barrier Progression

The bar-by-bar replay. Shows how close the price got to take-profit (->TP) and stop-loss (->SL) on each bar, plus running P&L. The last bar shows which barrier was HIT.

```
Barrier Progression:
   Bar          Open     ...      ->TP        ->SL       P&L
     1      3.087600     ...   +0.077090   +0.006395  -1.0429%
     2      3.055400     ...   +0.077190   +0.006395  +0.0000%
     ...
     5      3.085200     ...                  HIT SL  -1.3538%
```

Reading this: "On bar 1, the high was 0.077 away from TP and the low was only 0.006 away from SL — a near miss. By bar 5, the low breached the SL price."

---

## How to Use

```bash
# Basic: inspect trade #1 of any config
RBP_INSPECT_CONFIG_ID=price_impact_lt_p10__volume_per_trade_gt_p75 \
RBP_INSPECT_TRADE_N=1 \
mise run trade:inspect

# Change trade number to see different trades
RBP_INSPECT_TRADE_N=4    # SL exit example
RBP_INSPECT_TRADE_N=59   # TIME exit example

# JSON output (for feeding into ML pipelines)
RBP_INSPECT_CONFIG_ID=... \
python -m rangebar_patterns.introspect -- --json

# Try different configs (any of the 1,008 2-feature combos)
RBP_INSPECT_CONFIG_ID=ofi_gt_p50__aggression_ratio_gt_p50
RBP_INSPECT_CONFIG_ID=duration_us_lt_p25__volume_per_trade_gt_p90
```

### Config ID Format Explained

```
price_impact_lt_p10__volume_per_trade_gt_p75
|____________| |  |  |________________| |  |
  feature 1   |  |     feature 2       |  |
              lt p10                   gt p75
              "less than"              "greater than"
              "10th percentile"        "75th percentile"

Translation: "Take trades where price_impact is below its
rolling 10th percentile AND volume_per_trade is above its
rolling 75th percentile"
```

---

## Exit Types

| Exit                 | What Happened                              | Typical Bar Count   |
| -------------------- | ------------------------------------------ | ------------------- |
| **TP** (Take Profit) | Price rose enough to hit the profit target | Varies (1-50)       |
| **SL** (Stop Loss)   | Price fell enough to hit the loss limit    | Usually fast (1-10) |
| **TIME**             | Neither barrier hit within 50 bars         | Always 50           |

The TP/SL barrier prices are computed from the entry price:

- **TP** = entry × (1 + 0.5 × threshold) — a 2.5% move up for @500dbps
- **SL** = entry × (1 - 0.25 × threshold) — a 1.25% move down for @500dbps

This is asymmetric by design: the take-profit target is 2x wider than the stop-loss, which suits mean-reversion patterns.

---

## Dependencies (What This Module Imports)

```
introspect.py
    |
    +-- rangebar_patterns.config        (SYMBOL, THRESHOLD_DBPS, TP_MULT, SL_MULT, MAX_BARS)
    +-- rangebar_patterns.eval.extraction (_CTE_TEMPLATE, FEATURES, GRID)
    +-- clickhouse_connect              (ClickHouse client — lazy import in main())
    +-- backtest.backtesting_py.ssh_tunnel (SSHTunnel — lazy import in main())
    +-- json, os, sys, datetime         (stdlib only)
```

No new dependencies were added. The ClickHouse and SSH tunnel imports are lazy (inside `main()`) so the module can be imported for testing without a live connection.

---

## Test Coverage

| Test Group       | Count  | What It Validates                                             |
| ---------------- | ------ | ------------------------------------------------------------- |
| Parse config_id  | 6      | All 1,008 configs roundtrip, multi-word features, error cases |
| SQL construction | 4      | Trade list SQL, trade detail SQL, missing args, unknown mode  |
| Renderers        | 4      | Summary, feature diagnostic, barrier progression, JSON export |
| **Total**        | **14** | All pass without ClickHouse (synthetic data for renderers)    |

Run: `uv run -p 3.13 pytest tests/test_introspect.py -v`
