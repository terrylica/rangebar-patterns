# NN Experiment Designs - AI Context

**Scope**: Neural network designs and evaluation methodology based on brute-force pattern discoveries.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Designs

| File                           | Experiment                       | Status          |
| ------------------------------ | -------------------------------- | --------------- |
| exp082-long-only-meanrev-nn.md | Long-only BiLSTM with 8 features | DESIGN COMPLETE |

## Beyond-Kelly Evaluation POC

The `tmp/beyond-kelly-poc/` directory contains the 9-agent, 8-layer evaluation metrics POC. Key outcome: the **5-metric evaluation stack** (Kelly, Omega, DSR, MinBTL, PBO) should be used to evaluate all future experiments including exp082.

See [tmp/beyond-kelly-poc/CLAUDE.md](/tmp/beyond-kelly-poc/CLAUDE.md) for details.

## Key Insight

The champion SQL pattern (62.93% hit rate) is **DEAD as standalone strategy** — 0 configs survive multiple testing. It serves as the feature engineering foundation for exp082. The NN aims to learn nuanced variations the fixed rule misses.
