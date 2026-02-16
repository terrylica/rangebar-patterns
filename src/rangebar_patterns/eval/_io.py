"""Shared I/O utilities for the eval subpackage.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def git_commit_short() -> str:
    """Return short git commit hash, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def provenance_dict(*, include_env: bool = False) -> dict:
    """Build standard provenance metadata for telemetry records.

    GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
    """
    p: dict = {
        "git_commit": git_commit_short(),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    if include_env:
        from rangebar_patterns import config as cfg

        p["environment"] = {
            "symbol": cfg.SYMBOL,
            "threshold_dbps": cfg.THRESHOLD_DBPS,
            "tp_mult": cfg.TP_MULT,
            "sl_mult": cfg.SL_MULT,
            "max_bars": cfg.MAX_BARS,
            "rachev_alpha": cfg.RACHEV_ALPHA,
            "cdar_alpha": cfg.CDAR_ALPHA,
            "wf_min_train_splits": cfg.WF_MIN_TRAIN_SPLITS,
            "wf_max_train_splits": cfg.WF_MAX_TRAIN_SPLITS,
            "wf_cpcv_n_test_folds": cfg.WF_CPCV_N_TEST_FOLDS,
            "wf_cpcv_embargo_bars": cfg.WF_CPCV_EMBARGO_BARS,
            "wf_bootstrap_resamples": cfg.WF_BOOTSTRAP_RESAMPLES,
            "wf_bootstrap_block_size": cfg.WF_BOOTSTRAP_BLOCK_SIZE,
            "wf_screen_top_k": cfg.WF_SCREEN_TOP_K,
            "wf_inner_k": cfg.WF_INNER_K,
            "wf_n_regimes": cfg.WF_N_REGIMES,
        }
    return p


def results_dir() -> Path:
    """Resolve results/eval/ directory relative to repo root.

    Walks up from this file to find pyproject.toml, then returns
    <repo_root>/results/eval/. Creates the directory if it doesn't exist.
    """
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            d = current / "results" / "eval"
            d.mkdir(parents=True, exist_ok=True)
            return d
        current = current.parent
    msg = "Cannot find repo root (no pyproject.toml found)"
    raise RuntimeError(msg)


def load_jsonl(path: Path) -> list[dict]:
    """Load NDJSON file into list of dicts."""
    records = []
    with open(path) as f:
        for line in f:
            records.append(json.loads(line))
    return records
