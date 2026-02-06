# fix(features): Address look-ahead bias issues found by QLA audit

**Source**: EonLabs-Spartan/alpha-forge#133
**State**: closed
**Labels**: bug
**Exported**: 2026-02-06

---

## Summary

Batch audit of 22 feature plugins using the new `/audit` skill (Quant Logic Auditor) revealed **12 files with potential issues**. **All 12 have been addressed** - 5 required code fixes, 7 required documentation clarification (using standard TA-Lib conventions).

**Audit Results**: 
- Total: 22 files
- PASS: 8 (36%)
- WARNING: 2 (9%)  
- FAIL: 12 (55%) → All addressed

---

## Code Fixes (5 files)

| File | Issue | Fix |
|------|-------|-----|
| `factors.py` | `composite_score` missing z-score normalization | Added per-timestamp cross-sectional z-score before weighting |
| `masked_return.py` | Window `[i-lookback+1, i]` included current day | Changed to `[i-lookback, i-1]` (excludes current) |
| `quote_volume.py` | Per-symbol percentile included current value | Changed `values[start_idx:i+1]` to `values[start_idx:i]` |
| `trend_indicators.py` | Ichimoku chikou span used `shift(-26)` (future data!) | Changed to `shift(26)` (past data) |
| `inverse_volatility.py` | Missing `requires_history` and `warmup_formula` | Added required decorator parameters |

---

## Documentation Clarifications (7 files)

These plugins follow standard TA-Lib conventions where indicators are calculated at bar close using data known at that time. Added timing documentation to clarify this is intentional behavior, not look-ahead bias.

| File | Original Concern | Resolution |
|------|------------------|------------|
| `volume_features.py` | Cross-sectional z-score includes self | Added note: "standard practice, not temporal look-ahead" |
| `divergence.py` | Rolling includes current bar | Verified correct: already uses `.shift(1)` in comparisons |
| `oscillators.py` | RSI includes current bar | Added timing note: "calculated using data up to and including bar t (standard TA-Lib convention)" |
| `price_levels.py` | Rolling window includes current | Added assumption: "Window includes current bar (standard TA-Lib convention, value known at bar close)" |
| `quality_score.py` | Max drawdown includes current | Verified correct: max drawdown definition is standard finance practice |
| `volume.py` | ROCP without shift | Added timing notes for `norm_vrocp` and `price_volume` functions |
| `volume_ma.py` | VMA divided by current volume | Added timing documentation and corrected formula description |

---

## Design Decisions

The audit revealed an important distinction:

1. **True Look-Ahead Bias** (FIXED): Using future data that wouldn't be available at decision time
   - Example: `shift(-26)` in ichimoku - uses data 26 bars into the future
   - Example: Including current day in "past N days" window for returns

2. **Standard TA Conventions** (DOCUMENTED): Using current bar data at bar close
   - TA-Lib functions calculate indicators at bar close using data known at close
   - Cross-sectional normalization includes all assets at the same timestamp
   - These are industry standard practices, not bugs

---

## Related

- `/audit` skill: `.claude/skills/audit/SKILL.md`
- Auditor script: `scripts/quant_auditor.py`
- ADR-2025-12-06: Warmup formula requirements

---

## Comments

### Comment by Mayweiwang on 2026-02-04

All 12 plugins have been addressed:
- 5 code fixes for actual look-ahead bias issues
- 7 documentation clarifications for standard TA-Lib timing conventions

Key learning: The audit distinguished between true look-ahead bias (using future data) and standard TA convention (calculating at bar close with data known at close). Both are now properly handled.
