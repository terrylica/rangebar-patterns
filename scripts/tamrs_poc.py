"""TAMRS Fail-Fast POC — synthetic profile validation.

Runs 4 synthetic trade profiles matching Gemini 3 Pro worked examples,
computes all TAMRS components, and validates against expected ranges.
If any profile fails its expected range, the POC is NO-GO.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from rangebar_patterns.eval.cdar import compute_cdar
from rangebar_patterns.eval.rachev import compute_rachev

PROFILES = [
    {
        "name": "penny_picker_clustered",
        "description": "97% WR, small gains, rare large losses, clustered",
        "returns": [0.001] * 97 + [-0.05] * 3,
        "expected_rachev": (0.01, 0.15),
        "expected_cdar_gt": 0.01,
    },
    {
        "name": "penny_picker_scattered",
        "description": "97% WR, small gains, rare large losses, scattered",
        "returns": (
            [0.001] * 32 + [-0.05] + [0.001] * 32 + [-0.05] + [0.001] * 32 + [-0.05]
        ),
        "expected_rachev": (0.01, 0.15),
        "expected_cdar_gt": 0.005,
    },
    {
        "name": "healthy_symmetric",
        "description": "60% WR, balanced gains/losses",
        "returns": [0.005] * 60 + [-0.005] * 40,
        "expected_rachev": (0.80, 1.30),
        "expected_cdar_gt": 0.0,
    },
    {
        "name": "healthy_mean_reversion",
        "description": "55% WR, slightly larger gains than losses",
        "returns": [0.008] * 55 + [-0.006] * 45,
        "expected_rachev": (0.80, 1.50),
        "expected_cdar_gt": 0.0,
    },
]


def _git_commit() -> str:
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


def main():
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "results" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "tamrs_poc.jsonl"

    git_commit = _git_commit()
    timestamp = datetime.now(tz=UTC).isoformat()
    provenance = {
        "git_commit": git_commit,
        "timestamp": timestamp,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }

    print("=" * 60)
    print("TAMRS Fail-Fast POC")
    print("=" * 60)

    results = []
    all_pass = True

    for profile in PROFILES:
        name = profile["name"]
        returns = profile["returns"]
        np.random.default_rng(42).shuffle(returns)

        rr = compute_rachev(returns)
        cd = compute_cdar(returns)

        # Kelly for comparison
        arr = np.asarray(returns, dtype=float)
        win_rate = float(np.mean(arr > 0))
        avg_win = float(np.mean(arr[arr > 0])) if np.any(arr > 0) else 0.0
        avg_loss = float(np.abs(np.mean(arr[arr < 0]))) if np.any(arr < 0) else 0.0
        kelly = (win_rate - (1 - win_rate) / (avg_win / avg_loss)) if avg_loss > 0 else 0.0

        # Validate Rachev
        rachev_pass = True
        if rr is None:
            rachev_pass = False
        else:
            lo, hi = profile["expected_rachev"]
            if not (lo <= rr <= hi):
                rachev_pass = False

        # Validate CDaR
        cdar_pass = cd is not None and cd >= profile["expected_cdar_gt"]

        profile_pass = rachev_pass and cdar_pass
        if not profile_pass:
            all_pass = False

        status = "PASS" if profile_pass else "FAIL"
        print(f"\n  [{status}] {name}: {profile['description']}")
        print(f"    Rachev:  {rr:.4f}" if rr else "    Rachev:  None")
        if rr is not None:
            lo, hi = profile["expected_rachev"]
            print(f"    Expected Rachev: [{lo}, {hi}] -> {'OK' if rachev_pass else 'FAIL'}")
        print(f"    CDaR:    {cd:.6f}" if cd else "    CDaR:    None")
        print(f"    Kelly:   {kelly:.4f}")

        record = {
            "phase": "synthetic",
            "test_case": name,
            "n_trades": len(returns),
            "kelly_fraction": round(kelly, 6),
            "rachev_ratio": round(rr, 6) if rr is not None else None,
            "cdar_095": round(cd, 6) if cd is not None else None,
            "rachev_pass": rachev_pass,
            "cdar_pass": cdar_pass,
            "profile_pass": profile_pass,
            "provenance": provenance,
        }
        results.append(record)

    print("\n" + "=" * 60)
    verdict = "GO" if all_pass else "NO-GO"
    print(f"POC Verdict: {verdict}")
    print("=" * 60)

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"Output: {output_file}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
