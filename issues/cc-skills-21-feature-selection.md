# Findings: Parameter-Free Feature Selection for High-ACF Financial Time Series

**Source**: terrylica/cc-skills#21
**State**: open
**Labels**: research, model:gemini-3-pro, model:claude
**Exported**: 2026-02-06

---

## Summary of Findings

Research on **parameter-free feature selection methods** for high-autocorrelation financial time series (ACF=0.94) with OOD robustness requirements. Key findings from two AI research agents:

### Key Takeaways

1. **Standard methods fail**: LASSO, Random Forest importance, and mutual information all break under ACF=0.94 due to inflated significance and i.i.d. assumptions

2. **Recommended Pipeline** (both sources agree):
   - **Phase 1**: mRMR for fast initial filtering (160→15 features)
   - **Phase 2**: Distance Correlation for nonlinear redundancy (parameter-free)
   - **Phase 3**: PCMCI (tigramite) for causal filtering with autocorrelation control
   - **Phase 4**: Walk-forward importance stability validation

3. **Critical Methods Identified**:
   | Method | Package | Purpose |
   |--------|---------|---------|
   | PCMCI | `tigramite` | Causal discovery under autocorrelation |
   | mRMR | `mrmr-selection` | Fast redundancy-aware filtering |
   | Distance Correlation | `dcor` | Parameter-free nonlinear dependence |
   | HSIC Lasso | `pyHSICLasso` | Nonlinear feature selection |
   | Block Bootstrap | `tsbootstrap` | Temporal structure preservation |
   | Scattering Transform | `kymatio` | Automatic multi-scale features |

4. **Lookback Selection Solution**: Use **scattering transform** (kymatio) to sidestep lb20/lb100/lb500 choice entirely - extracts features at ALL scales automatically

5. **OOD Robustness**: Use walk-forward importance stability + Anchor Regression with volatility regimes as anchors

### Effective Sample Size Warning
With ACF=0.94: `N_eff ≈ N × (1-ACF)/(1+ACF) ≈ N × 0.03`
A 10,000 sample dataset contains only ~300 effective independent samples!

---

## Why This Research Was Done

The trading-fitness project has 160 bounded [0,1] features from ITH (Investment Time Horizon) analysis with:
- Extreme redundancy: 160 → ~10 effective dimensions
- High autocorrelation: lag-1 ACF = 0.94
- Need for OOD robustness across market regimes

Current feature selection (correlation > 0.95 threshold) uses arbitrary "magic numbers" and doesn't account for:
- Temporal dependence
- Nonlinear redundancy
- Regime-invariant importance

---

## Claude Code Conversational Context

- **claude_code_uuid**: `14ac6476-077b-4c82-a3fe-217dae94cff6`
- **Project path**: `~/.claude/projects/-Users-terryli-eon-trading-fitness/14ac6476-077b-4c82-a3fe-217dae94cff6`

**Context**: User asked for layman explanation of feature analysis findings, then requested a prompt for Gemini 3 Pro Deep Research to find SOTA, parameter-free solutions for principled feature selection. Research focused on ceteris paribus experimental design for improved OOD robustness.

---

## Full References

| Source | Type | URL | Scraped |
|--------|------|-----|---------|
| Gemini 3 Pro Deep Research | gemini-3-pro | https://gemini.google.com/share/623be87160ee | 2026-02-02T09:03:00-08:00 |
| Claude Artifact | claude-artifact | https://claude.ai/public/artifacts/a49965f8-bca5-46cb-b791-50abd0492102 | 2026-02-02T09:03:46-08:00 |

### Saved Files (trading-fitness repo)
- `docs/research/external/2026-02-02-feature-selection-ood-robustness-gemini.md`
- `docs/research/external/2026-02-02-feature-selection-ood-robustness-claude.md`

---

## Recent Relevant Commits

- `65351f7` - chore(release): 3.0.1 [skip ci]
- `87b8163` - docs(claude-md): reorganize project memory with hub-and-spoke pattern
- Related files: `docs/forensic/COMPREHENSIVE_AUDIT_20260125.md`, `docs/forensic/SYMMETRIC_AUDIT_20260125.md`

---

## Comments

### Comment by terrylica on 2026-02-02

## Canonical Backlink Block

**Saved Files:**
- `trading-fitness/docs/research/external/2026-02-02-feature-selection-ood-robustness-gemini.md`
- `trading-fitness/docs/research/external/2026-02-02-feature-selection-ood-robustness-claude.md`

**Sources:**
| source_url | source_type | scraped_at |
|------------|-------------|------------|
| https://gemini.google.com/share/623be87160ee | gemini-3-pro | 2026-02-02T09:03:00-08:00 |
| https://claude.ai/public/artifacts/a49965f8-bca5-46cb-b791-50abd0492102 | claude-artifact | 2026-02-02T09:03:46-08:00 |

**Models:**
- Gemini 3 Pro Deep Research (v3.0)
- Claude Artifact (3.5-sonnet)

**Claude Code Context:**
- `claude_code_uuid`: 14ac6476-077b-4c82-a3fe-217dae94cff6
- `claude_code_project_path`: ~/.claude/projects/-Users-terryli-eon-trading-fitness/14ac6476-077b-4c82-a3fe-217dae94cff6

### Comment by terrylica on 2026-02-04

## Phase 4 Implementation Complete (2026-02-04)

All four phases of the principled feature selection pipeline are now implemented and tested:

### Implementation Summary

| Phase | Module | Functions | Tests |
|-------|--------|-----------|-------|
| 1 | `mrmr.py` | `filter_mrmr()`, `compute_mrmr_scores()`, `get_mrmr_summary()` | 12 |
| 2 | `dcor_filter.py` | `filter_dcor_redundancy()`, `compute_dcor_matrix()`, `get_redundancy_pairs()` | 13 |
| 3 | `pcmci_filter.py` | `filter_pcmci()`, `compute_causal_strengths()`, `get_pcmci_summary()` | 12 |
| 4a | `block_bootstrap.py` | `compute_bootstrap_importance()`, `compute_optimal_block_length()`, `filter_by_stability()` | 14 |
| 4b | `walk_forward.py` | `compute_walk_forward_stability()`, `filter_stable_features()`, `select_top_k_stable()` | 13 |

**Total**: 160 tests passing

### Key Implementation Notes

1. **Block Bootstrap**: Implemented native circular block bootstrap due to tsbootstrap/scikit-learn 1.8 incompatibility (`force_all_finite` → `ensure_all_finite`). Uses `recombinator` for Politis-White optimal block length.

2. **Walk-Forward CV**: Uses sklearn `TimeSeriesSplit` with coefficient of variation (CV) for stability filtering.

3. **Suppression Integration**: All modules integrate with the Feature Suppression Registry (`suppression.py`) for filtering known-unstable features.

4. **Pipeline Flow**: 
   ```
   suppression → mRMR (160→50) → dCor (50→30) → PCMCI (30→15) → Bootstrap+WalkForward (15→10)
   ```

### Next Steps

- [ ] #29 Scattering Transform (optional, for automatic scale selection)
- [ ] #30 Run integrated pipeline on real littleblack data
- [ ] #31 Create mise tasks for pipeline orchestration
- [ ] #32 Update CLAUDE.md documentation

### Files

Location: `packages/ith-python/src/ith_python/statistical_examination/`
Tests: `packages/ith-python/tests/test_statistical_examination/`

### Comment by terrylica on 2026-02-04

## Feature Selection Pipeline - Complete (2026-02-04)

The principled feature selection pipeline is now fully implemented, tested, and documented.

### Summary

| Task | Status | Deliverable |
|------|--------|-------------|
| #24 mRMR | Done | `mrmr.py` - 12 tests |
| #25 dCor | Done | `dcor_filter.py` - 13 tests |
| #26 PCMCI | Done | `pcmci_filter.py` - 12 tests |
| #27 Block Bootstrap | Done | `block_bootstrap.py` - 14 tests |
| #28 Walk-Forward | Done | `walk_forward.py` - 13 tests |
| #30 Integration | Done | `test_pipeline_integration.py` - 12 tests |
| #31 mise tasks | Done | 9 tasks in `packages/ith-python/mise.toml` |
| #32 Documentation | Done | Updated `CLAUDE.md` |

**Total: 172 tests passing**

### mise Commands

```bash
mise run feature-selection:pipeline   # Full run (160→10 features)
mise run feature-selection:test       # Pipeline tests (64)
mise run feature-selection:validate   # Full suite (172)
```

### Pipeline Flow

```
suppression → mRMR (160→50) → dCor (50→30) → PCMCI (30→15) → Stability (15→10)
```

### Key Implementation Notes

1. **Suppression**: Pattern-based filtering (rb25-rb500 and lb20 suppressed)
2. **mRMR**: Uses `mrmr-selection` package via pandas bridge
3. **dCor**: Parameter-free nonlinear dependence (`dcor` package)
4. **PCMCI**: Causal discovery handling ACF=0.94 (`tigramite`)
5. **Block Bootstrap**: Native circular implementation (tsbootstrap/sklearn 1.8 incompatibility)
6. **Walk-Forward**: TimeSeriesSplit CV with coefficient of variation filter

### Next Steps (Optional)

- #29 Scattering Transform for automatic scale selection (kymatio fork available)
- Run pipeline on real littleblack data when ClickHouse connectivity established

### Files

- Module: `packages/ith-python/src/ith_python/statistical_examination/`
- Tests: `packages/ith-python/tests/test_statistical_examination/`
- Documentation: `packages/ith-python/src/ith_python/statistical_examination/CLAUDE.md`
