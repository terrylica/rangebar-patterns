"""Load representative barrier configs from Gen720 Pareto front.

Selects diverse (phase1, sl_tight) combinations to cover the barrier
space without the full 434-config grid. Used by gen800_sweep.py.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

# Top 20 diverse barriers from Gen720 TOPSIS ranking (LONG direction).
# Selected: best per unique (phase1, sl_tight) pair, covering the full
# parameter space without redundant max_bars variants.
DEFAULT_BARRIER_IDS = [
    "p2_slt005_mb30",
    "p2_slt010_mb20",
    "p2_slt025_mb10",
    "p3_slt005_mb50",
    "p3_slt010_mb20",
    "p3_slt025_mb10",
    "p2_slt035_mb10",
    "p3_slt035_mb10",
    "p5_slt005_mb10",
    "p5_slt010_mb10",
    "p5_slt025_mb10",
    "p5_slt035_mb10",
    "p7_slt005_mb10",
    "p7_slt010_mb10",
    "p7_slt025_mb10",
    "p7_slt035_mb10",
    "p10_slt005_mb15",
    "p10_slt010_mb15",
    "p10_slt025_mb15",
    "p10_slt035_mb15",
]


def parse_barrier_id(barrier_id: str) -> dict:
    """Parse barrier_id string into parameter dict.

    Format: p{phase1}_slt{sl_tight*10:03d}_mb{max_bars}
    """
    import re

    m = re.match(r"^p(\d+)_slt(\d{3})_mb(\d+)$", barrier_id)
    if not m:
        raise ValueError(f"Invalid barrier_id: {barrier_id!r}")
    return {
        "phase1_bars": int(m.group(1)),
        "sl_tight_mult": int(m.group(2)) / 10.0,
        "max_bars": int(m.group(3)),
    }


def load_barrier_configs(
    barrier_ids: list[str] | None = None,
    tp_mult: float = 2.5,
    sl_mult: float = 5.0,
    bar_range: float = 0.0075,
) -> list[dict]:
    """Load barrier configs as dicts ready for BarrierConfig construction.

    Parameters
    ----------
    barrier_ids : list[str] or None
        Barrier ID strings. Defaults to DEFAULT_BARRIER_IDS.
    tp_mult : float
        Take profit multiplier (bar-widths). Default 2.5.
    sl_mult : float
        Wide SL multiplier (bar-widths). Default 5.0.
    bar_range : float
        Fractional bar width. Default 0.0075 (@750dbps).
    """
    if barrier_ids is None:
        barrier_ids = DEFAULT_BARRIER_IDS

    configs = []
    for bid in barrier_ids:
        params = parse_barrier_id(bid)
        configs.append({
            "tp_mult": tp_mult,
            "sl_mult": sl_mult,
            "sl_tight_mult": params["sl_tight_mult"],
            "phase1_bars": params["phase1_bars"],
            "max_bars": params["max_bars"],
            "bar_range": bar_range,
        })
    return configs
