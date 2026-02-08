"""Strategy evaluation metrics: DSR, MinBTL, Omega, CSCV/PBO, E-values.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12

Usage::

    from rangebar_patterns.eval import compute_omega, compute_minbtl
    from rangebar_patterns.eval.dsr import compute_psr, expected_max_sr
    from rangebar_patterns.eval.cornish_fisher import cf_var
"""

from rangebar_patterns.eval.dsr import compute_psr, expected_max_sr, sr_standard_error
from rangebar_patterns.eval.evalues import compute_evalues
from rangebar_patterns.eval.minbtl import compute_minbtl
from rangebar_patterns.eval.omega import compute_omega

__all__ = [
    "compute_evalues",
    "compute_minbtl",
    "compute_omega",
    "compute_psr",
    "expected_max_sr",
    "sr_standard_error",
]
