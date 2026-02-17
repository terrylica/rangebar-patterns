"""Pydantic models for WFO telemetry schema versioning.

Schema version 1: Gen720 walk-forward barrier optimization.
Breaking changes (required fields added/removed/renamed/retyped) bump version.
Adding optional fields = same version (backward compatible).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- Tier 2: Per-Combo Summary ----


class FoldMetadata(BaseModel):
    """Metadata for a single WFO fold."""

    fold_id: int = Field(ge=0)
    train_start_bar: int = Field(ge=0)
    train_end_bar: int = Field(ge=0)
    test_start_bar: int = Field(ge=0)
    test_end_bar: int = Field(ge=0)
    train_start_ms: int
    train_end_ms: int
    test_start_ms: int
    test_end_ms: int
    purge_gap_bars: int = Field(ge=0)
    embargo_bars: int = Field(ge=0)
    n_train_raw: int = Field(ge=0)
    n_train_purged: int = Field(ge=0)
    n_purged: int = Field(ge=0)
    n_test: int = Field(ge=0)


class VorobStability(BaseModel):
    """Vorob'ev stability metrics for a single combo."""

    vorob_threshold: float
    vorob_deviation: float = Field(ge=0)
    hv_per_fold: list[float]
    hv_cv: float = Field(ge=0)


class BarrierSummary(BaseModel):
    """Summary of a top-performing barrier for a combo."""

    barrier_id: str
    consistency: float = Field(ge=0, le=1)
    avg_oos_omega: float
    avg_oos_rachev: float
    avg_oos_pf: float
    omega_cv: float = Field(ge=0)
    n_tamrs_viable_folds: int = Field(ge=0)
    n_total_folds: int = Field(ge=0)
    # Stage 2/3/4 annotations (optional — backward compatible)
    pbo: float | None = None
    pbo_pass: bool | None = None
    bootstrap_rejected: bool | None = None
    survived_all_stages: bool | None = None
    gt_composite: float | None = None
    omega_ci_lower: float | None = None
    omega_ci_upper: float | None = None
    rachev_ci_lower: float | None = None


class ComboEnvironment(BaseModel):
    """SQL/data provenance for a single combo."""

    sql_template: str
    sql_template_sha256: str
    tsv_file: str
    tsv_row_count: int = Field(ge=0)
    bar_count_aligned: int = Field(ge=0)
    end_ts_ms: int


class ComboTiming(BaseModel):
    """Timing breakdown for a single combo evaluation."""

    tsv_load_s: float = Field(ge=0)
    fold_build_s: float = Field(ge=0)
    barrier_eval_s: float = Field(ge=0)
    vorob_s: float = Field(ge=0)
    cpcv_s: float = Field(ge=0, default=0)
    bootstrap_s: float = Field(ge=0, default=0)
    total_s: float = Field(ge=0)


class WFComboV1(BaseModel):
    """Tier 2: Per-combo WFO summary (one per formation x symbol x threshold)."""

    schema_version: Literal[1] = 1
    direction: Literal["LONG", "SHORT"]
    formation: str
    strategy: str = "standard"  # "standard" for LONG, "A_mirrored"/"B_reverse" for SHORT
    symbol: str
    threshold: int = Field(ge=100, le=2000)
    n_signals: int = Field(ge=0)
    n_signals_subsampled_from: int | None = None
    subsample_factor: int | None = None
    n_wf_folds: int = Field(ge=0)
    n_barriers_tested: int = Field(ge=0, default=434)
    low_power: bool = False
    fold_metadata: list[FoldMetadata] = Field(default=[])  # noqa: fake-data
    vorob_stability: VorobStability | None = None
    top_barriers: list[BarrierSummary] = Field(default=[])  # noqa: fake-data
    # Stage 2/3/4 summaries (optional — backward compatible)
    stage2_cpcv: dict | None = None
    stage3_bootstrap: dict | None = None
    stage4_ranking: dict | None = None
    environment: ComboEnvironment | None = None
    timing: ComboTiming | None = None
    provenance: dict = Field(default={})  # noqa: fake-data


# ---- Tier 3: Aggregation ----


class DataLineage(BaseModel):
    """Cross-reference to lower-tier artifacts."""

    fold_parquet: str
    combo_jsonl: str
    raw_tsv_dir: str
    n_raw_tsv_files: int = Field(ge=0)
    n_combo_records: int = Field(ge=0)


class PerFormationSummary(BaseModel):
    """Cross-asset summary for a single formation."""

    n_tamrs_viable: int = Field(ge=0)
    n_total: int = Field(ge=0)
    avg_oos_omega: float
    avg_oos_rachev: float


class BarrierXAEntry(BaseModel):
    """Top barrier entry in cross-asset ranking."""

    barrier_id: str
    n_tamrs_viable: int = Field(ge=0)
    avg_oos_omega: float
    avg_oos_rachev: float
    xa_consistency: float = Field(ge=0, le=1)
    xf_consistency: float = Field(ge=0, le=1)
    hv_cv: float = Field(ge=0)


class KneeAnalysis(BaseModel):
    """Knee detection results."""

    n_knee_points: int = Field(ge=0)
    knee_barrier_ids: list[str] = Field(default=[])  # noqa: fake-data
    epsilon: float = Field(gt=0)


class TOPSISEntry(BaseModel):
    """TOPSIS-ranked barrier entry."""

    barrier_id: str
    topsis_score: float = Field(ge=0, le=1)
    rank: int = Field(ge=1)


class OracleSpotCheck(BaseModel):
    """Oracle validation spot-check result."""

    barrier_id: str
    formation: str
    sql_pf: float
    py_pf: float
    pf_diff: float
    signal_match_pct: float
    exit_type_match_pct: float
    gates_passed: int = Field(ge=0, le=5)
    gates_total: int = 5


class WFAggregationV1(BaseModel):
    """Tier 3: Cross-formation/cross-asset WFO aggregation."""

    schema_version: Literal[1] = 1
    direction: Literal["LONG", "SHORT"]
    data_lineage: DataLineage | None = None
    per_combo_summary: list[dict] = Field(default=[])  # noqa: fake-data
    cross_formation: dict = Field(default={})  # noqa: fake-data
    cross_asset: dict = Field(default={})  # noqa: fake-data
    knee_analysis: KneeAnalysis | None = None
    topsis_ranking: list[TOPSISEntry] = Field(default=[])  # noqa: fake-data
    oracle_validation: dict = Field(default={})  # noqa: fake-data
    timing: dict = Field(default={})  # noqa: fake-data
    provenance: dict = Field(default={})  # noqa: fake-data
