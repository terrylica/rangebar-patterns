"""Shared I/O utilities for the eval subpackage.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
from pathlib import Path


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
