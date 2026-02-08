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
THRESHOLD_PCT: float = THRESHOLD_DBPS / 10000.0

# ---- Default Barrier Configuration ----
TP_MULT: float = float(os.environ.get("RBP_TP_MULT", "0.5"))
SL_MULT: float = float(os.environ.get("RBP_SL_MULT", "0.25"))
MAX_BARS: int = int(os.environ.get("RBP_MAX_BARS", "50"))

# ---- Evaluation Parameters ----
N_TRIALS: int = int(os.environ.get("RBP_N_TRIALS", "1008"))
ALPHA: float = float(os.environ.get("RBP_ALPHA", "0.05"))
DSR_THRESHOLD: float = float(os.environ.get("RBP_DSR_THRESHOLD", "0.95"))
