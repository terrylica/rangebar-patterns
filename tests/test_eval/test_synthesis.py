"""Test synthesis: e-BH and Romano-Wolf procedures.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from rangebar_patterns.eval.synthesis import ebh_procedure, romano_wolf_stepdown


def test_ebh_no_evalues():
    result = ebh_procedure([])
    assert result["k_star"] == 0
    assert result["discoveries"] == []
    assert result["k_total"] == 0


def test_ebh_weak_evalues():
    """E-values < 1/alpha should yield no discoveries."""
    evalues = [
        {"config_id": "a", "final_evalue": 1.5},
        {"config_id": "b", "final_evalue": 0.8},
        {"config_id": "c", "final_evalue": 2.0},
    ]
    result = ebh_procedure(evalues)
    assert result["k_star"] == 0


def test_ebh_strong_evalue():
    """A single E-value > K/alpha should be discovered."""
    evalues = [
        {"config_id": "strong", "final_evalue": 100.0},
        {"config_id": "weak", "final_evalue": 0.5},
    ]
    result = ebh_procedure(evalues)
    assert result["k_star"] >= 1
    assert any(d["config_id"] == "strong" for d in result["discoveries"])


def test_romano_wolf_no_data():
    result = romano_wolf_stepdown([], n_bootstrap=100)
    assert result["n_rejections"] == 0
    assert result["discoveries"] == []


def test_romano_wolf_strong_signal():
    """Strongly positive mean returns with variance should survive bootstrap."""
    import numpy as np

    rng = np.random.default_rng(99)
    # Mean 0.05, std 0.01 -> very high t-stat
    rets = (rng.normal(0.05, 0.01, 500)).tolist()
    data = [
        {"config_id": "strong", "n_trades": 500, "returns": rets},
    ]
    result = romano_wolf_stepdown(data, n_bootstrap=100)
    assert result["n_rejections"] >= 1


def test_romano_wolf_noise():
    """Pure noise should not survive."""
    import numpy as np

    rng = np.random.default_rng(42)
    data = [
        {"config_id": f"noise_{i}", "n_trades": 50, "returns": rng.normal(0, 0.01, 50).tolist()}
        for i in range(20)
    ]
    result = romano_wolf_stepdown(data, n_bootstrap=100)
    # Noise shouldn't consistently reject (may get lucky occasionally)
    assert result["n_rejections"] <= 3
