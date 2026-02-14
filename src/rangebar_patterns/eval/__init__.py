"""Strategy evaluation metrics: DSR, MinBTL, Omega, CSCV/PBO, E-values, TAMRS.

GitHub Issues: #12 (eval stack), #16 (TAMRS)

Usage::

    from rangebar_patterns.eval import compute_omega, compute_minbtl
    from rangebar_patterns.eval import compute_rachev, compute_cdar, compute_tamrs
    from rangebar_patterns.eval.dsr import compute_psr, expected_max_sr
    from rangebar_patterns.eval.ou_barriers import calibrate_ou, ou_barrier_ratio
"""

from rangebar_patterns.eval.cdar import compute_cdar
from rangebar_patterns.eval.dsr import compute_psr, expected_max_sr, sr_standard_error
from rangebar_patterns.eval.evalues import compute_evalues
from rangebar_patterns.eval.minbtl import compute_minbtl
from rangebar_patterns.eval.omega import compute_omega
from rangebar_patterns.eval.rachev import compute_rachev
from rangebar_patterns.eval.tamrs import compute_tamrs

__all__ = [
    "compute_cdar",
    "compute_evalues",
    "compute_minbtl",
    "compute_omega",
    "compute_psr",
    "compute_rachev",
    "compute_tamrs",
    "expected_max_sr",
    "sr_standard_error",
]
