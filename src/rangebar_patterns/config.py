"""Research parameters from environment (mise [env]) with typed defaults.

All values read from RBP_* environment variables set in .mise.toml.
Override in .mise.local.toml or shell: RBP_SYMBOL=BTCUSDT mise run ...

Mathematical constants (EULER_GAMMA) and implementation guards (MIN_BET,
MAX_EVALUE) are NOT externalized -- they belong in their respective modules.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import os

# ---- Data Selection ----
SYMBOL: str = os.environ.get("RBP_SYMBOL", "SOLUSDT")
THRESHOLD_DBPS: int = int(os.environ.get("RBP_THRESHOLD_DBPS", "500"))
BAR_RANGE: float = THRESHOLD_DBPS / 100_000.0  # Aligned with rangebar-py: 500 dbps = 0.005 = 0.5%

# ---- Default Barrier Configuration ----
# Multipliers are in bar-widths: tp_mult=5.0 means TP at 5.0× the bar range from entry
TP_MULT: float = float(os.environ.get("RBP_TP_MULT", "5.0"))
SL_MULT: float = float(os.environ.get("RBP_SL_MULT", "2.5"))
MAX_BARS: int = int(os.environ.get("RBP_MAX_BARS", "50"))

# ---- Evaluation Parameters ----
N_TRIALS: int = int(os.environ.get("RBP_N_TRIALS", "1008"))
ALPHA: float = float(os.environ.get("RBP_ALPHA", "0.05"))
DSR_THRESHOLD: float = float(os.environ.get("RBP_DSR_THRESHOLD", "0.95"))

# ---- TAMRS Parameters (Issue #16) ----
RACHEV_ALPHA: float = float(os.environ.get("RBP_RACHEV_ALPHA", "0.05"))
CDAR_ALPHA: float = float(os.environ.get("RBP_CDAR_ALPHA", "0.95"))
MIN_TRADES_RACHEV: int = int(os.environ.get("RBP_MIN_TRADES_RACHEV", "20"))
MIN_TRADES_CDAR: int = int(os.environ.get("RBP_MIN_TRADES_CDAR", "10"))
CSCV_RANKER: str = os.environ.get("RBP_CSCV_RANKER", "tamrs")
CSCV_SPLITS: int = int(os.environ.get("RBP_CSCV_SPLITS", "8"))
TP_EMP: float = TP_MULT * BAR_RANGE  # Derived: 5.0 * 0.005 = 0.025
SL_EMP: float = SL_MULT * BAR_RANGE  # Derived: 2.5 * 0.005 = 0.0125

# ---- Screening Tier Thresholds (Issue #16) ----
SCREEN_TAMRS_MIN: tuple[float, ...] = (
    float(os.environ.get("RBP_SCREEN_TAMRS_MIN_T1", "0.0")),
    float(os.environ.get("RBP_SCREEN_TAMRS_MIN_T2", "0.05")),
    float(os.environ.get("RBP_SCREEN_TAMRS_MIN_T3", "0.15")),
)
SCREEN_RACHEV_MIN: tuple[float, ...] = (
    float(os.environ.get("RBP_SCREEN_RACHEV_MIN_T1", "0.0")),
    float(os.environ.get("RBP_SCREEN_RACHEV_MIN_T2", "0.30")),
    float(os.environ.get("RBP_SCREEN_RACHEV_MIN_T3", "0.50")),
)
SCREEN_OU_RATIO_MIN: tuple[float, ...] = (
    float(os.environ.get("RBP_SCREEN_OU_RATIO_MIN_T1", "0.0")),
    float(os.environ.get("RBP_SCREEN_OU_RATIO_MIN_T2", "0.30")),
    float(os.environ.get("RBP_SCREEN_OU_RATIO_MIN_T3", "0.50")),
)

# ---- Signal Regularity Parameters (Issue #17) ----
MIN_TRADES_REGULARITY: int = int(os.environ.get("RBP_MIN_TRADES_REGULARITY", "10"))
SCREEN_REGULARITY_CV_MAX: tuple[float, ...] = (
    float(os.environ.get("RBP_SCREEN_REGULARITY_CV_MAX_T1", "999.0")),
    float(os.environ.get("RBP_SCREEN_REGULARITY_CV_MAX_T2", "0.80")),
    float(os.environ.get("RBP_SCREEN_REGULARITY_CV_MAX_T3", "0.50")),
)
SCREEN_COVERAGE_MIN: tuple[float, ...] = (
    float(os.environ.get("RBP_SCREEN_COVERAGE_MIN_T1", "0.0")),
    float(os.environ.get("RBP_SCREEN_COVERAGE_MIN_T2", "0.50")),
    float(os.environ.get("RBP_SCREEN_COVERAGE_MIN_T3", "0.70")),
)

# ---- Ranking Cutoffs (Issue #17) ----
# Per-metric percentile cutoff: top X% survives. 100 = no filter. 0 = nothing passes.
# All default to 100 (wide open). Evolutionary optimizer tightens from here.
RANK_CUT_TAMRS: int = int(os.environ.get("RBP_RANK_CUT_TAMRS", "100"))
RANK_CUT_RACHEV: int = int(os.environ.get("RBP_RANK_CUT_RACHEV", "100"))
RANK_CUT_OU_RATIO: int = int(os.environ.get("RBP_RANK_CUT_OU_RATIO", "100"))
RANK_CUT_SL_CDAR: int = int(os.environ.get("RBP_RANK_CUT_SL_CDAR", "100"))
RANK_CUT_OMEGA: int = int(os.environ.get("RBP_RANK_CUT_OMEGA", "100"))
RANK_CUT_DSR: int = int(os.environ.get("RBP_RANK_CUT_DSR", "100"))
RANK_CUT_HEADROOM: int = int(os.environ.get("RBP_RANK_CUT_HEADROOM", "100"))
RANK_CUT_EVALUE: int = int(os.environ.get("RBP_RANK_CUT_EVALUE", "100"))
RANK_CUT_REGULARITY_CV: int = int(os.environ.get("RBP_RANK_CUT_REGULARITY_CV", "100"))
RANK_CUT_COVERAGE: int = int(os.environ.get("RBP_RANK_CUT_COVERAGE", "100"))
RANK_CUT_N_TRADES: int = int(os.environ.get("RBP_RANK_CUT_N_TRADES", "100"))
# Kelly removed from ranking per Issue #17 (contradictory with TAMRS)

# ---- Cross-Asset Ranking Cutoffs ----
RANK_CUT_XA_N_POSITIVE: int = int(os.environ.get("RBP_RANK_CUT_XA_N_POSITIVE", "100"))
RANK_CUT_XA_AVG_PF: int = int(os.environ.get("RBP_RANK_CUT_XA_AVG_PF", "100"))
RANK_CUT_XA_TOTAL_SIGNALS: int = int(os.environ.get("RBP_RANK_CUT_XA_TOTAL_SIGNALS", "100"))
RANK_CUT_XA_CONSISTENCY: int = int(os.environ.get("RBP_RANK_CUT_XA_CONSISTENCY", "100"))

RANK_TOP_N: int = int(os.environ.get("RBP_RANK_TOP_N", "50"))
RANK_OBJECTIVE: str = os.environ.get("RBP_RANK_OBJECTIVE", "max_survivors_min_cutoff")
RANK_N_TRIALS: int = int(os.environ.get("RBP_RANK_N_TRIALS", "200"))
RANK_TARGET_N: int = int(os.environ.get("RBP_RANK_TARGET_N", "10"))

# ---- Knee Detection (Issue #28) ----
RANK_KNEE_EPSILON: float = float(os.environ.get("RBP_RANK_KNEE_EPSILON", "0.125"))

# ---- Walk-Forward Optimization (Issue #28) ----
WF_MIN_TRAIN_SPLITS: int = int(os.environ.get("RBP_WF_MIN_TRAIN_SPLITS", "3"))
WF_MAX_TRAIN_SPLITS: int = int(os.environ.get("RBP_WF_MAX_TRAIN_SPLITS", "5"))
WF_CPCV_N_TEST_FOLDS: int = int(os.environ.get("RBP_WF_CPCV_N_TEST_FOLDS", "2"))
WF_CPCV_EMBARGO_BARS: int = int(os.environ.get("RBP_WF_CPCV_EMBARGO_BARS", "10"))
WF_BOOTSTRAP_RESAMPLES: int = int(os.environ.get("RBP_WF_BOOTSTRAP_RESAMPLES", "10000"))
WF_BOOTSTRAP_BLOCK_SIZE: int = int(os.environ.get("RBP_WF_BOOTSTRAP_BLOCK_SIZE", "20"))
WF_SCREEN_TOP_K: int = int(os.environ.get("RBP_WF_SCREEN_TOP_K", "50"))
WF_INNER_K: int = int(os.environ.get("RBP_WF_INNER_K", "10"))
WF_N_REGIMES: int = int(os.environ.get("RBP_WF_N_REGIMES", "3"))
