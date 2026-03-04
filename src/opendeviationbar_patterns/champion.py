"""Champion pattern constants (SSoT).

ADR: docs/adr/2026-02-06-repository-creation.md

The champion pattern emerged from 8 generations of brute-force SQL pattern discovery
on ClickHouse range bar data. Gen111 (TRUE no-lookahead with expanding-window percentiles)
is the production-ready version.

Pattern: 2 consecutive DOWN bars + trade_intensity > p95_expanding + kyle_lambda > 0 -> LONG
"""

CHAMPION = {
    "name": "combo_2down_ti_p95_kyle_gt_0_long",
    "hit_rate_biased": 0.6832,
    "hit_rate_true_nla": 0.6293,
    "z_score_true_nla": 8.25,
    "dsr": 1.000,
    "n_patterns_searched": 111,
    "signal_count": 1017,
}

# Per-year TRUE NLA hit rates (Gen112)
TEMPORAL_HIT_RATES = {
    2020: {"hit_rate": 0.7143, "z_score": 3.05, "significant": True},
    2021: {"hit_rate": 0.6800, "z_score": 3.13, "significant": True},
    2022: {"hit_rate": 0.6667, "z_score": 2.89, "significant": True},
    2023: {"hit_rate": 0.6250, "z_score": 2.24, "significant": True},
    2024: {"hit_rate": 0.5600, "z_score": 1.24, "significant": False},
    2025: {"hit_rate": 0.5400, "z_score": 0.87, "significant": False},
}

# Cross-asset TRUE NLA results (Gen110)
CROSS_ASSET = {
    "SOLUSDT": {"hit_rate": 0.6293, "direction": "long"},
    "BNBUSDT": {"hit_rate": 0.7172, "direction": "long"},
    "BTCUSDT": {"hit_rate": 0.6267, "direction": "long"},
    "ETHUSDT": {"hit_rate": 0.4500, "direction": "inverted"},  # Pattern fails on ETH
}
