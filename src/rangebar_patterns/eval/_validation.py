"""Pandera schemas for Tier 1 Parquet validation.

Validates per-fold WFO results before writing to Parquet.
Uses Pandera's Polars-native integration for zero-copy validation.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

import pandera.polars as pa


class FoldSchema(pa.DataFrameModel):
    """Schema for Tier 1 per-fold Parquet (long_folds.parquet / short_folds.parquet)."""

    formation: str
    strategy: str  # "standard" for LONG, "A_mirrored"/"B_reverse" for SHORT
    symbol: str
    threshold: int = pa.Field(isin=[500, 750, 1000])
    barrier_id: str
    fold_id: int = pa.Field(ge=0)
    n_trades: int = pa.Field(ge=0)
    win_rate: float = pa.Field(ge=0.0, le=1.0)
    profit_factor: float = pa.Field(ge=0.0)
    omega: float = pa.Field(ge=0.0)
    rachev: float = pa.Field(ge=0.0)
    cdar: float = pa.Field(ge=0.0)
    total_return: float
    avg_return: float
    max_drawdown: float = pa.Field(ge=0.0, le=1.0)
    train_start_bar: int = pa.Field(ge=0)
    train_end_bar: int = pa.Field(ge=0)
    test_start_bar: int = pa.Field(ge=0)
    test_end_bar: int = pa.Field(ge=0)
    train_start_ms: int
    train_end_ms: int
    test_start_ms: int
    test_end_ms: int
    n_train_raw: int = pa.Field(ge=0)
    n_train_purged: int = pa.Field(ge=0)
    n_purged: int = pa.Field(ge=0)
