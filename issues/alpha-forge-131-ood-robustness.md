# Findings: OOD Robustness Research for Selective Prediction

**Source**: EonLabs-Spartan/alpha-forge#131
**State**: open
**Labels**: (none)
**Exported**: 2026-02-06

---

## Summary

Deep research on **parameter-free OOD robustness** for financial ML with selective abstention, conducted via Gemini 3 Pro Deep Research and Claude artifact synthesis.

### Key Findings

1. **Deep Gamblers** (NeurIPS 2019) - Replace SelectiveNet with Kelly-aligned loss function
   - Embeds cost of capital directly into training objective
   - Single parameter O (reservation return) is a financial constant, not a tuning value
   - GitHub: https://github.com/Z-T-WANG/NIPS2019DeepGamblers

2. **Conformal PID Control** (NeurIPS 2023) - Adaptive coverage guarantees
   - Tested on market data specifically
   - PID controller for online threshold adjustment
   - GitHub: https://github.com/aangelopoulos/conformal-time-series

3. **Ensemble Disagreement** - Parameter-free uncertainty signal
   - Use `σ = std([p_seed1, ..., p_seedM])` as abstention signal
   - Already available from multi-seed training
   - No code changes needed

4. **Energy-Based OOD Detection** (NeurIPS 2020) - Fast baseline
   - E(x) = -T·log(Σ_i exp(f_i(x)/T)) from BiLSTM logits
   - Parameter-free with T=1 default
   - GitHub: https://github.com/wetliu/energy_ood

### Open Questions (Not Addressed by Literature)

1. Binary classification near i.i.d. (up-rate ≈ 0.496) challenges all methods
2. Range bar non-uniform timing complicates temporal methods
3. Negative Kelly despite positive profit factors indicates distribution mismatch
4. Pareto frontier epoch selection interacts with selective prediction
5. Transaction costs interact non-linearly with abstention

## Research Context

**Why this research was done**: exp079 showed negative Kelly edge (-0.4 to -0.7) despite positive profit factors. High seed disagreement suggested need for principled uncertainty handling.

**Claude Code context**:
- `claude_code_uuid`: 3d0512c5-fe15-4d74-86cc-b2e6ece321e9
- Session: ML robustness research for WFO cryptocurrency trading
- Current experiment: exp079 train_bars sweep with rich per-bar telemetry

## Saved Files

- `examples/research/findings/2026-02-02-ood-robustness-research/gemini-3-pro-deep-research.md`
- `examples/research/findings/2026-02-02-ood-robustness-research/claude-artifact-synthesis.md`

## Source URLs

- Gemini 3 Pro: https://gemini.google.com/share/9bcd199946a0
- Claude Artifact: https://claude.ai/public/artifacts/27e12556-2f05-40da-a3fb-a092ab121084

## Proposed Experimental Roadmap (Ceteris Paribus)

### Phase 1: No architecture changes
- exp080a: Ensemble disagreement as abstention signal
- exp080b: Energy-based OOD scoring

### Phase 2: Adaptive coverage
- exp081a: ACI update rule on SelectiveNet gate
- exp081b: Conformal PID control

### Phase 3: Loss function change
- exp082: Deep Gamblers loss (replace SelectiveNet)

### Phase 4: Adaptive windowing
- exp083: MDL-based window selection

## Related Commits

- exp079_metrics.py: Per-bar telemetry functions
- exp079_sol_rich_telemetry.py: Rich telemetry experiment

## Labels

research:ood, research:selective-prediction, model:gemini-3-pro, model:claude

---

## Comments

(no comments)
