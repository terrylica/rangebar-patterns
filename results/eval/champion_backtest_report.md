# Universal Champion Backtest Report

**Strategy**: `turnover_imbalance_lt_p25__price_impact_lt_p25`
**Asset**: SOLUSDT @500 dbps | **Period**: Aug 2020 — Feb 2025 (4.5 years)
**Pattern**: 2 consecutive DOWN bars + trade intensity > p95 + kyle_lambda > 0
**Features**: turnover_imbalance < rolling p25 AND price_impact < rolling p25
**Barriers**: TP = 0.25x threshold (tight), SL = 0.50x threshold (wide), max_bars = 100
**GitHub Issue**: [Issue 26](https://github.com/terrylica/rangebar-patterns/issues/26)

---

## Executive Summary

The universal champion shows a **78.8% win rate** with a **profit factor of 1.99** (nearly 2:1 winners vs losers) across 113 trades over 4.5 years. The system quality number (SQN) of **3.44** rates as **"Excellent"** on Van Tharp's scale. Maximum consecutive losses is only **2 trades**, while the longest winning streak spans **18 trades**.

However, the strategy fires infrequently (113 trades in 4.5 years = ~25 trades/year) and is in the market only **0.37% of the time**. The total portfolio return of +0.54% is tiny because each position sizes at 1% of equity (required for multi-position oracle matching). With proper position sizing, the per-trade edge is real but small.

**Trader verdict**: High win rate, excellent SQN, minimal drawdowns, but low trade frequency and small per-trade edge. This is a **niche signal** — valuable as one input among many, not as a standalone system.

---

## 1. Returns

| Metric            | Value   | What This Means                                            |
| ----------------- | ------- | ---------------------------------------------------------- |
| Total Return      | +0.54%  | Cumulative portfolio return (with 1% position sizing)      |
| Annualized Return | +0.12%  | Yearly rate — tiny because position size is 1% per trade   |
| Buy & Hold Return | +5,867% | SOL went from ~$0.48 to ~$29 — massive bull market context |
| Best Trade        | +1.30%  | Roughly equals the TP barrier distance (0.25 x 5% = 1.25%) |
| Worst Trade       | -2.52%  | Roughly equals the SL barrier distance (0.50 x 5% = 2.50%) |
| Avg Trade         | +0.47%  | Mean return across all 113 trades                          |
| Expectancy        | +0.48%  | Expected $ return per trade (similar to avg trade)         |

**Interpretation**: The per-trade returns are consistent and match the barrier distances. Winners average +1.23% (close to the 1.25% TP barrier) and losers average -2.29% (close to the 2.50% SL barrier). The win rate of 78.8% more than compensates for the asymmetric barriers (winners are smaller than losers in dollar terms, but happen almost 4x more often).

The Buy & Hold return of +5,867% tells us SOL had an extraordinary bull run during this period. The strategy's +0.54% looks terrible in comparison — but that's misleading because position sizing is 1% per trade. If you risked 10% per trade, the returns would be roughly 10x higher (with correspondingly larger drawdowns).

---

## 2. Risk Management

| Metric                 | Value     | What This Means                                                   |
| ---------------------- | --------- | ----------------------------------------------------------------- |
| Max Drawdown           | -0.09%    | Largest peak-to-trough decline (tiny due to small position sizes) |
| Avg Drawdown           | -0.02%    | Typical decline during losing periods                             |
| Max DD Duration        | 637 days  | Longest time spent underwater (1.7 years — very long)             |
| Avg DD Duration        | 18.6 days | Typical recovery time from a drawdown                             |
| Calmar Ratio           | 1.37      | Annual return / max drawdown — above 1.0 is decent                |
| Max Consecutive Losses | 2         | Worst losing streak was only 2 trades in a row                    |
| Max Consecutive Wins   | 18        | Best winning streak was 18 trades in a row                        |

**Interpretation**: The strategy has exceptional streak behavior — the longest losing streak is just 2 trades, while winning streaks can reach 18. This makes it psychologically easy to trade. The max drawdown of 0.09% is negligible (an artifact of 1% sizing). The 637-day max drawdown duration is concerning — there are long periods where the strategy simply doesn't fire, creating extended underwater periods for the equity curve.

---

## 3. Quality Indicators

| Metric          | Value  | Rating    | What This Means                                                     |
| --------------- | ------ | --------- | ------------------------------------------------------------------- |
| Win Rate        | 78.76% | Excellent | Almost 4 out of 5 trades are winners                                |
| Profit Factor   | 1.99   | Good      | $1.99 of gross profit for every $1.00 of gross loss                 |
| SQN             | 3.44   | Excellent | Van Tharp's System Quality Number (>2.5 = excellent, >3.0 = superb) |
| Sharpe Ratio    | 1.22   | Above Avg | Risk-adjusted return (>1.0 is generally considered good)            |
| Sortino Ratio   | 2.81   | Very Good | Same as Sharpe but only penalizes downside volatility               |
| Calmar Ratio    | 1.37   | Decent    | Return per unit of max drawdown                                     |
| Kelly Criterion | 35.5%  | High      | Optimal bet fraction — suggests significant edge                    |

**Interpretation**: All quality indicators paint a consistently positive picture. The SQN of 3.44 is the standout — Van Tharp considers anything above 3.0 "superb." The Sortino ratio of 2.81 (which ignores upside volatility) is excellent. The Kelly fraction of 35.5% is aggressive — in practice, most traders would use quarter-Kelly (8.9%) or less.

**Caveat**: These metrics are computed on only 113 trades over 4.5 years. With so few trades, all statistics have wide confidence intervals. A strategy that looks excellent with 113 trades could easily look mediocre with the next 113.

---

## 4. Trade Profile

| Metric             | Value      | What This Means                                           |
| ------------------ | ---------- | --------------------------------------------------------- |
| Total Trades       | 113        | Across 4.5 years (~25 trades per year, ~2 per month)      |
| Exposure Time      | 0.37%      | Strategy is in the market only 0.37% of the time          |
| Avg Trade Duration | 59 minutes | Most trades resolve within 1 hour                         |
| Max Trade Duration | 23.2 hours | Longest trade lasted less than 1 day                      |
| Winning Trades     | 89         | 78.8% of all trades                                       |
| Losing Trades      | 24         | 21.2% of all trades (includes TIME exits ending negative) |
| Avg Win            | +1.23%     | Close to TP barrier (0.25 x 5% = 1.25%)                   |
| Avg Loss           | -2.29%     | Close to SL barrier (0.50 x 5% = 2.50%)                   |

**Interpretation**: This is an extremely selective strategy — it only trades ~2 times per month. Trades resolve quickly (average under 1 hour), which means you're not exposed to overnight risk or weekend gaps. The win/loss sizes are highly predictable, clustering tightly around the barrier distances.

The low exposure time (0.37%) means your capital is free 99.6% of the time — you could run many such strategies in parallel without capital conflicts.

---

## 5. Oracle Validation Summary

The strategy was validated 1:1 between ClickHouse SQL and backtesting.py:

| Gate | Check           | Result | Detail                           |
| ---- | --------------- | ------ | -------------------------------- |
| 1    | Signal Count    | PASS   | SQL=111, PY=113 (1.77% diff)     |
| 2    | Timestamp Match | PASS   | 111/113 = 98.2% overlap          |
| 3    | Entry Price     | PASS   | 111/111 = 100% match             |
| 4    | Exit Type       | PASS   | 106/111 = 95.5% match            |
| 5    | Kelly Fraction  | PASS   | SQL=0.405, PY=0.391 (0.014 diff) |

**Discrepancies**: 2 signals appear only in Python (edge effects at data boundaries). 5 exit type mismatches (SQL says TP/SL, Python says TIME) occur at trades near the 100-bar time boundary — a known minor difference in how the two systems evaluate the final barrier bar.

---

## 6. TAMRS Context

Our custom evaluation stack provides additional context beyond traditional trading metrics:

| Our Metric       | Value  | What It Means for a Trader                                                      |
| ---------------- | ------ | ------------------------------------------------------------------------------- |
| Kelly (custom)   | +0.051 | Positive edge — bet ~5% per trade optimally                                     |
| TAMRS            | 0.078  | Positive tail-adjusted quality (combines 3 factors below)                       |
| Rachev Ratio     | 2.000  | Your best 5% of trades are 2x bigger than your worst 5% — maximum possible      |
| SL/CDaR Ratio    | 0.100  | Stop loss covers only 10% of clustered drawdown risk — **WARNING**: this is low |
| OU Barrier Ratio | 0.392  | Mean-reversion model supports 39% of our TP target — moderate fit               |
| Omega            | 1.236  | Win/loss distribution is positive (above 1.0 threshold)                         |

**Key TAMRS insight**: The Rachev ratio is saturated at 2.0 (maximum), meaning the strategy's tail behavior is excellent — extreme winners dominate extreme losers. However, the SL/CDaR ratio of 0.10 is a concern: it means the stop loss is much tighter than the strategy's historical clustered drawdowns. In a regime of sustained losses, the SL may not protect as well as it appears from simple win-rate statistics.

---

## 7. Verdict

### Strengths

- **High win rate** (78.8%): Psychologically comfortable to trade
- **Excellent SQN** (3.44): One of Van Tharp's highest quality categories
- **Short losing streaks** (max 2): Quick recovery from losses
- **Quick trades** (avg 59 min): Low overnight exposure
- **Predictable P&L**: Trade sizes cluster tightly around barrier distances
- **Low market exposure** (0.37%): Capital efficient, parallelizable

### Weaknesses

- **Low trade frequency** (~25/year): Not enough to generate meaningful standalone income
- **Small per-trade edge** (avg +0.47%): Needs significant capital or leverage
- **Long underwater periods** (max 637 days): Extended periods without new trades
- **Asymmetric barriers**: Average loss (-2.29%) is 1.86x average win (+1.23%)
- **SL/CDaR gap**: Stop loss may not protect against clustered drawdown regimes
- **No statistical significance**: Does NOT survive Bonferroni correction with 1,008 strategies tested

### Bottom Line

The universal champion has the **profile of a real but weak edge**. A traditional quant trader would note: high win rate + excellent SQN + good Sharpe/Sortino + predictable trade sizes. But the low frequency, small per-trade edge, and failure to pass multiple testing corrections mean this is **not tradeable as a standalone strategy**.

Its best use is as a **feature input** to a more sophisticated model — the microstructure signals it captures (calm absorption moments with low selling pressure and low price impact) are genuine market dynamics, even if they're too weak alone to form a profitable system.

**Path forward**: Neural network feature engineering (see `designs/exp082-long-only-meanrev-nn.md`).

---

## Raw Data

- **Backtest stats**: `results/eval/champion_backtest_stats.jsonl`
- **Oracle comparison**: `/tmp/oracle_result_solusdt_500.tsv`
- **SQL query**: `sql/champion_oracle_trades.sql`
- **Oracle script**: `scripts/champion_oracle_compare.py`
- **Strategy code**: `backtest/backtesting_py/gen600_strategy.py`
