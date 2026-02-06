# Findings: Meta-Abstention Framework for Go/No-Go Trading Decisions

**Source**: EonLabs-Spartan/alpha-forge#129
**State**: open
**Labels**: findings, research, model:gemini-3-pro
**Exported**: 2026-02-06

---

## Summary

Comprehensive research on **Meta-Abstention** — a framework for making period-level go/no-go trading decisions based on validation-to-test predictiveness. This addresses the critical question: _"Can we use validation metrics to reliably predict whether to trade in an upcoming unseen period?"_

### Key Findings

1. **Meta-Labeling** (Lopez de Prado): Secondary model trained on primary model outcomes, aggregated for period-level abstention
2. **HMM Regime Detection**: Conditional performance metrics per regime state; abstain when current regime differs from validation
3. **Conformal Prediction**: Interval width as uncertainty proxy; wide intervals → NO-GO
4. **PSR/DSR/MinTRL**: Parameter-free probabilistic metrics that naturally trigger abstention
5. **Information-Theoretic**: Permutation Entropy, KL Divergence for distributional shift detection
6. **TDA**: Persistence Landscapes for structural regime change detection
7. **Contextual Bandits**: Online learning of optimal abstention policy

### Key Libraries (Open Source)

| Method        | Library             | pip install                |
| ------------- | ------------------- | -------------------------- |
| Meta-Labeling | mlfinlab, RiskLabAI | `pip install mlfinlab`     |
| HMM           | hmmlearn            | `pip install hmmlearn`     |
| Change Point  | ruptures            | `pip install ruptures`     |
| Conformal     | MAPIE, crepes       | `pip install mapie`        |
| Entropy       | antropy, ordpy      | `pip install antropy`      |
| TDA           | giotto-tda, gudhi   | `pip install giotto-tda`   |
| Bandits       | vowpal_wabbit       | `pip install vowpalwabbit` |

### Proposed Architecture

**Consensus Gate**: Combine multiple signals (HMM, Meta-Label, Conformal, Entropy, TDA, Bayesian) into weighted ensemble. Trade only when Score > 0.5.

---

## Why This Research Was Done

During exp077 execution, we observed that some test folds give identical Sharpe regardless of seed (market-driven) while others vary. This led to the critical question: **Can validation performance predict test performance at all?**

If validation is NOT predictive of test, we need a meta-level decision system that knows when to abstain entirely.

---

## Claude Code Context

- **claude_code_uuid**: `3d0512c5-fe15-4d74-86cc-b2e6ece321e9`
- **Project**: `~/.claude/projects/-Users-terryli-eon-alpha-forge-worktree-2025-12-24-ralph-ml-robustness-research/3d0512c5-fe15-4d74-86cc-b2e6ece321e9`
- **Conversation**: ML robustness research on WFO validation, exp077 in progress

---

## References

### Source

- **URL**: <https://gemini.google.com/share/71d7cfe0f139>
- **Type**: gemini-3-pro
- **Scraped**: 2026-02-01T02:33:44Z
- **Model**: Gemini 3 Pro Deep Research (2026-01)

### Saved File

- **Path**: `examples/research/findings/2026-02-01-stationarity-gap-framework/gemini-meta-abstention-framework.md`

### Related Files

- `examples/research/findings/2026-02-01-stationarity-gap-framework/forensic-analysis-go-no-go.md` - Internal forensic analysis
- `examples/research/findings/2026-02-01-stationarity-gap-framework/gemini-prompt-go-no-go-research.md` - Prompt used
- `examples/research/findings/2026-02-01-stationarity-gap-framework/gemini-time-to-convergence-analysis.md` - Prior MRH research

### Recent Commits

- `c7b7686c` feat(research): exp074 principled WFO validation - HYPOTHESIS REJECTED
- `f17daa27` docs(research): add principled WFO solutions from Claude and Gemini
- `bb828a5e` feat(research): WFO tooling synthesis + exp073 partial results

---

## Comments

### Comment by terrylica on 2026-02-05

## MAJOR BREAKTHROUGH: Brute-Force Microstructure Analysis Complete (2026-02-05)

### ULTIMATE Champion Pattern Found

**Pattern**: `2 DOWN bars + trade_intensity > p95 + kyle_lambda > 0 → LONG`

| Metric | Value |
|--------|-------|
| **Hit Rate** | **68.32%** |
| **Edge** | **+18.32%** directional accuracy above 50% |
| **Z-Score** | **9.74** (p < 0.0001, extremely significant) |
| Signal Count | 707 samples |

### Evolution Across 8 Generations

| Gen | Champion Pattern | Hit Rate | Key Discovery |
|-----|-----------------|----------|---------------|
| 2 | `ti_p95 + kyle>0` | 52.98% | Intensity + direction |
| 6 | `ti_p90_3bar_streak` | 52.12% | Intensity momentum persists |
| 7 | `meanrev_2down_ti_p90_long` | **60.90%** | Mean reversion breakthrough! |
| 8 | `combo_2down_ti_p95_kyle_gt_0_long` | **68.32%** | Combined Gen2 + Gen7 |

### Key Discoveries

1. **Mean Reversion is KING**: 2 consecutive DOWN bars create oversold condition → reversal UP
2. **SHORT signals LOSE**: All SHORT patterns underperform on SOL (44-50% hit rate)
3. **Intensity + Kyle + Direction**: Combining all three gives maximum edge
4. **Adding more features HURTS**: Gen3 (3 features) performed WORSE than Gen2 (2 features)
5. **ETH is INVERTED**: Pattern works on SOL/BTC/BNB but is opposite on ETH

### Next Steps → exp082

1. **Long-only BiLSTM**: Gate only opens for LONG positions
2. **Mean reversion features**: Add `direction(t-1)`, `direction(t-2)` to feature set
3. **Intensity regime filter**: Pre-filter to `trade_intensity > p90`
4. **SOL primary, validate on BTC/BNB, exclude ETH**

### Database & Files

- ClickHouse: `rangebar_cache.feature_combinations` (111 patterns across 8 generations)
- Analysis: `examples/research/findings/2026-02-02-ood-robustness-research/brute_force_microstructure_analysis.md`
- SQL files: `brute_force_gen1.sql` through `brute_force_gen8_divergence.sql`

---

**Session UUID**: `3d0512c5-fe15-4d74-86cc-b2e6ece321e9`

### Comment by terrylica on 2026-02-05

## Lookahead Bias Audit Update (2026-02-05)

### Issue Found

The original brute-force analysis computed percentile thresholds (p90, p95) over the **ENTIRE dataset**, including future bars. This is lookahead bias.

**Severity**: Trade intensity p95 varies wildly by year:
- 2020: p95 = 18.35 (94% LOWER than full-dataset)
- 2021: p95 = 500 (58% HIGHER)
- 2025: p95 = 695 (120% HIGHER)

Using full-dataset p95 = 316.37 would incorrectly time-travel thresholds.

### Correction Applied

Re-ran Gen8 patterns using **prior-year percentiles** (no within-year lookahead).

### Results Comparison

| Pattern | With Lookahead | NO Lookahead | Delta |
|---------|----------------|--------------|-------|
| `combo_2down_ti_p95_kyle_gt_0_long` | 68.32% | **66.76%** | -1.56% |
| `combo_2down_ti_p90_kyle_gt_0_long` | 60.26% | **60.67%** | +0.41% |

### Verdict: CORE FINDING HOLDS

- Edge dropped by ~1.5% after correction
- Z-score = 8.95 (still highly significant, p < 0.0001)
- The pattern `2 DOWN bars + high intensity + Kyle>0 → LONG` is **REAL**

### Remaining Work

- [ ] Re-validate cross-asset patterns (BTC, BNB) with no-lookahead
- [ ] Run full Gen1-Gen7 with no-lookahead for completeness
- [ ] Design exp082 using CORRECTED statistics

**Lag logic** (`lagInFrame`) and **direction vs features** logic were verified CORRECT. Only percentile thresholds had lookahead.
