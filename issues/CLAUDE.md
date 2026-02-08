# GitHub Issue Snapshots - AI Context

**Scope**: Durable local records of research findings posted to GitHub Issues.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Why Local Snapshots?

GitHub Issues are the insight repository during active research. These snapshots preserve
findings even if issues are edited, closed, or repos restructured.

## rangebar-patterns Issues

| #   | Title                                                         | State  | Key Content                                             |
| --- | ------------------------------------------------------------- | ------ | ------------------------------------------------------- |
| 12  | Beyond-Kelly POC: 5-metric stack (Kelly+Omega+DSR+MinBTL+PBO) | Open   | 0 survive multiple testing, 5-metric decision           |
| 11  | Forensic Analysis: Gen500-520 Overnight Sweep                 | Open   | 15,300 configs, 0 survive Bonferroni, 56 dual-validated |
| 10  | Gen300: Feature filter sweep                                  | Closed | Expanding window false positive, no edge                |
| 9   | Research Consolidation: 17 SQL generations                    | Open   | Champion 62.93% HR, PF=1.27 with barriers               |
| 8   | Anti-Pattern Registry: 13 ClickHouse SQL constraints          | Open   | SQL + infra constraints from Gen200-202                 |
| 7   | Update champion_strategy.py: Triple Barrier + Trailing Stop   | Closed | Backtesting framework exit logic                        |
| 6   | Atomic Validation: 96% exit price match                       | Closed | SQL vs backtesting.py alignment verified                |
| 5   | Gen202: Combined barrier = Gen201 (identical)                 | Closed | Fixed SL champion: PF=1.27                              |
| 4   | Gen201: Trailing stop DOES NOT improve fixed SL               | Closed | PF 1.26 vs 1.27, edge is short-lived                    |
| 3   | Gen200: Triple barrier SQL — PF=1.27 @500dbps                 | Closed | Tight TP + wide SL + long patience dominates            |
| 2   | SQL Hit Rate vs Backtesting.py Win Rate Mismatch              | Closed | Structural mismatch diagnosis                           |
| 1   | Gen200-202 Triple Barrier Framework COMPLETE                  | Closed | Fixed SL champion, pattern is ML feature                |

## Cross-Repo Issue Snapshots

| File                                | Source                           | Key Content                                                 |
| ----------------------------------- | -------------------------------- | ----------------------------------------------------------- |
| alpha-forge-129-meta-abstention.md  | EonLabs-Spartan/alpha-forge #129 | Brute-force breakthrough, 8-gen evolution, champion pattern |
| alpha-forge-130-exp079-telemetry.md | EonLabs-Spartan/alpha-forge #130 | 21-field per-bar telemetry schema                           |
| alpha-forge-131-ood-robustness.md   | EonLabs-Spartan/alpha-forge #131 | Deep Gamblers, Conformal PID, Energy OOD                    |
| alpha-forge-133-feature-audit.md    | EonLabs-Spartan/alpha-forge #133 | Look-ahead bias audit (22 files, 12 issues)                 |
| cc-skills-21-feature-selection.md   | terrylica/cc-skills #21          | Parameter-free feature selection pipeline                   |
