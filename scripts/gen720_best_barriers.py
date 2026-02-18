#!/usr/bin/env python3
"""Gen720 best risk-adjusted barrier configurations across ALL formations.

Reads fold-level Parquet, aggregates across all symbols and thresholds
per formation x barrier_id, then filters and ranks.
"""

import polars as pl


def analyze_direction(parquet_path: str, direction: str) -> None:
    """Analyze one direction (long or short)."""
    print(f"\n{'='*120}")
    print(f"  {direction.upper()} DIRECTION — Best Risk-Adjusted Barriers Across All Formations")
    print(f"{'='*120}\n")

    df = pl.read_parquet(parquet_path)
    print(f"Loaded {df.shape[0]:,} rows, {df.shape[1]} columns")
    print(f"Formations: {sorted(df['formation'].unique().to_list())}")
    print(f"Barrier IDs: {df['barrier_id'].n_unique()}")
    print(f"Symbols: {sorted(df['symbol'].unique().to_list())}")
    print(f"Thresholds: {sorted(df['threshold'].unique().to_list())}")

    n_sym_thr = df.select("symbol", "threshold").unique().shape[0]
    print(f"Symbol x Threshold combos: {n_sym_thr}")
    print()

    # Each row = one fold (formation x barrier_id x symbol x threshold x fold_id)
    # Step 1: Aggregate folds -> per (formation, barrier_id, symbol, threshold)
    #   Use median across folds for stability
    per_asset = df.group_by("formation", "barrier_id", "symbol", "threshold").agg(
        pl.col("n_trades").sum().alias("n_trades"),
        pl.col("win_rate").median().alias("win_rate"),
        pl.col("profit_factor").median().alias("profit_factor"),
        pl.col("omega").median().alias("omega"),
        pl.col("rachev").median().alias("rachev"),
        pl.col("total_return").median().alias("total_return"),
        pl.col("avg_return").median().alias("avg_return"),
        pl.col("max_drawdown").median().alias("max_drawdown"),
        pl.col("cdar").median().alias("cdar"),
    )

    print(f"After fold aggregation: {per_asset.shape[0]:,} asset-level rows")

    # Step 2: Aggregate across all symbols x thresholds per (formation, barrier_id)
    agg = per_asset.group_by("formation", "barrier_id").agg(
        pl.col("profit_factor").median().alias("med_pf"),
        pl.col("omega").median().alias("med_omega"),
        pl.col("total_return").median().alias("med_total_return"),
        pl.col("win_rate").median().alias("med_win_rate"),
        pl.col("max_drawdown").median().alias("med_max_dd"),
        pl.col("rachev").median().alias("med_rachev"),
        pl.col("cdar").median().alias("med_cdar"),
        pl.col("n_trades").sum().alias("total_trades"),
        # Cross-asset consistency: fraction with PF > 1.0
        (pl.col("profit_factor") > 1.0).mean().alias("xa_consistency"),
        # Count of assets tested
        pl.len().alias("n_assets"),
        # Mean total_return for context
        pl.col("total_return").mean().alias("mean_total_return"),
        # Avg return per trade
        pl.col("avg_return").median().alias("med_avg_return"),
    )

    print(f"After cross-asset aggregation: {agg.shape[0]:,} formation x barrier combos")

    # Step 3: Filter
    filtered = agg.filter(
        (pl.col("med_pf") > 1.05)
        & (pl.col("xa_consistency") > 0.6)
        & (pl.col("total_trades") > 500)
    )

    print(f"After filtering (PF>1.05, XA>0.6, trades>500): {filtered.shape[0]:,} combos remain")

    if filtered.shape[0] == 0:
        print("\n  ** No combos pass the filters. Relaxing to PF > 1.0, XA > 0.5 **\n")
        filtered = agg.filter(
            (pl.col("med_pf") > 1.0)
            & (pl.col("xa_consistency") > 0.5)
            & (pl.col("total_trades") > 500)
        )
        print(f"  After relaxed filtering: {filtered.shape[0]:,} combos remain")

        if filtered.shape[0] == 0:
            print("\n  ** Still no combos. Showing top 30 unfiltered by omega **\n")
            filtered = agg.filter(pl.col("total_trades") > 100)

    # Step 4: Sort by median omega descending
    result = filtered.sort("med_omega", descending=True).head(30)

    # Step 5: Parse barrier_id for readability
    # barrier_id format: p{tp_pct}_slt{sl_pct}_mb{max_bars}
    result = result.with_columns(
        pl.col("barrier_id")
        .str.extract(r"p(\d+)_slt(\d+)_mb(\d+)")
        .alias("tp_pct"),
        pl.col("barrier_id")
        .str.extract(r"p\d+_slt(\d+)_mb\d+")
        .alias("sl_pct"),
        pl.col("barrier_id")
        .str.extract(r"p\d+_slt\d+_mb(\d+)")
        .alias("max_bars"),
    )

    # Print results
    print(f"\n{'─'*120}")
    print(f"  TOP {min(30, result.shape[0])} BARRIER CONFIGS — Sorted by Median Omega (descending)")
    print(f"{'─'*120}")

    header = (
        f"{'#':>3}  {'Formation':<14} {'Barrier ID':<22} "
        f"{'Med PF':>8} {'Med Omega':>10} {'Med WR%':>8} "
        f"{'XA Cons%':>9} {'Med RetPct':>10} {'Med MDD%':>9} "
        f"{'Med Rachev':>11} {'Trades':>8} {'N Assets':>9}"
    )
    print(header)
    print("─" * 120)

    for i, row in enumerate(result.iter_rows(named=True), 1):
        print(
            f"{i:>3}  {row['formation']:<14} {row['barrier_id']:<22} "
            f"{row['med_pf']:>8.3f} {row['med_omega']:>10.3f} {row['med_win_rate']*100:>7.2f}% "
            f"{row['xa_consistency']*100:>8.1f}% {row['med_total_return']*100:>9.2f}% {row['med_max_dd']*100:>8.2f}% "
            f"{row['med_rachev']:>11.3f} {row['total_trades']:>8,} {row['n_assets']:>9}"
        )

    print()

    # Also show summary stats
    print(f"{'─'*80}")
    print("  FORMATION SUMMARY (all barrier_ids, no filters)")
    print(f"{'─'*80}")

    formation_summary = agg.group_by("formation").agg(
        pl.col("med_pf").max().alias("best_pf"),
        pl.col("med_omega").max().alias("best_omega"),
        pl.col("xa_consistency").max().alias("best_xa"),
        pl.col("med_pf").median().alias("typical_pf"),
        pl.col("xa_consistency").median().alias("typical_xa"),
        pl.len().alias("n_barriers"),
        (
            (pl.col("med_pf") > 1.05)
            & (pl.col("xa_consistency") > 0.6)
            & (pl.col("total_trades") > 500)
        )
        .sum()
        .alias("n_pass_strict"),
    ).sort("best_omega", descending=True)

    header2 = (
        f"  {'Formation':<14} {'Best PF':>8} {'Best Omega':>11} {'Best XA%':>9} "
        f"{'Typ PF':>8} {'Typ XA%':>8} {'N Barriers':>11} {'N Pass':>7}"
    )
    print(header2)
    print("  " + "─" * 78)

    for row in formation_summary.iter_rows(named=True):
        print(
            f"  {row['formation']:<14} {row['best_pf']:>8.3f} {row['best_omega']:>11.3f} {row['best_xa']*100:>8.1f}% "
            f"{row['typical_pf']:>8.3f} {row['typical_xa']*100:>7.1f}%"
            f" {row['n_barriers']:>11} {row['n_pass_strict']:>7}"
        )

    print()


def main() -> None:
    base = "results/eval/gen720/folds"

    analyze_direction(f"{base}/long_folds.parquet", "long")
    analyze_direction(f"{base}/short_folds.parquet", "short")


if __name__ == "__main__":
    main()
