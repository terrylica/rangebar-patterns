# Sweep Scripts - AI Context

**Scope**: Bash scripts for brute-force SQL sweep execution on remote ClickHouse via pueue.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Directory Convention

```
scripts/gen{NNN}/
├── generate.sh     # Pre-generate SQL files from templates (runs locally)
├── poc.sh          # Fail-fast POC (10 configs, validates pipeline end-to-end)
├── submit.sh       # rsync SQL to remote ClickHouse + submit to pueue (p1 group, 4 parallel)
├── status.sh       # Check pueue status + result counts on remote ClickHouse
├── collect.sh      # scp results from remote ClickHouse to logs/gen{NNN}/
└── report.sh       # Analyze results: top Kelly, Bonferroni, feature frequency
```

Each generation has its own directory. No shared scripts between generations (copy + adapt).

---

## Mise Integration

Each generation has a corresponding `.mise/tasks/gen{NNN}.toml`:

```toml
["gen{NNN}:generate"]
run = "bash scripts/gen{NNN}/generate.sh"

["gen{NNN}:submit"]
run = "bash scripts/gen{NNN}/submit.sh"
```

**CRITICAL**: After creating a new task file, add it to `.mise.toml` `[task_config] includes`:

```toml
[task_config]
includes = [
    ".mise/tasks/gen300.toml",
    ".mise/tasks/gen400.toml",
    ".mise/tasks/gen{NNN}.toml",  # <-- ADD THIS
]
```

---

## Production Patterns

Current baseline from Gen600 (most mature pipeline). Gen500 established the foundations; Gen600 evolved to batch submission with pueue state management for 301K configs.

**Detailed methodology**: See [sweep-methodology skill](/.claude/skills/sweep-methodology/SKILL.md#infrastructure-patterns)

### Invariants (what matters)

| Concern              | Invariant                                                      | Current Baseline (Gen600)                                                            |
| -------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Parallel writes**  | Atomic NDJSON appends                                          | `flock "${LOG_FILE}.lock"`                                                           |
| **Crash recovery**   | Idempotent re-submission                                       | `--skip-done` flag builds done-set from JSONL before command gen                     |
| **Data integrity**   | Valid JSONL after collection                                   | `sed` for `\N`/`nan`/`inf` + python3 validation                                      |
| **Reproducibility**  | Provenance in every telemetry line                             | `quantile_method`, `template_sha256`, `git_commit`                                   |
| **Error visibility** | Failed queries produce error lines, not silence                | Wrapper writes error NDJSON with truncated message                                   |
| **Submission speed** | Queue stays filled (no idle execution slots)                   | Two-tier: pueue sequential units + `xargs -P16` per unit (no `pueue add` per query)  |
| **State hygiene**    | `pueue clean` before/during bulk submission                    | Periodic clean between 5K batches (keeps state.json < 50MB)                          |
| **Shell safety**     | Scripts under `set -euo pipefail` avoid pipe-breaking patterns | Process substitution for while-read; no `ls\|head`; temp files for intermediate data |

The mechanisms can evolve. The invariants should hold.

---

## Critical Traps

### Tera/TOML Template Conflict

mise uses Tera templating that interprets `{{}}`, `{%}`, and `#}` sequences.

**RULE**: Complex bash MUST go in standalone `.sh` files. Never inline multi-line scripts in TOML.

```toml
# GOOD — mise toml just calls the script
run = "bash scripts/gen400/generate.sh"

# BAD — Tera will fail on bash syntax
run = '''
#!/bin/bash
for f in "${FEATURES[@]}"; do  # Tera interprets {%
    echo "processing #${f}"     # Tera interprets #}
done
'''
```

### Shellcheck Compliance

| Issue                                | Fix                                         |
| ------------------------------------ | ------------------------------------------- |
| SC2029: ssh client-side expansion    | `# shellcheck disable=SC2029` (intentional) |
| SC2095: ssh swallowing stdin in loop | Add `-n` flag to ssh calls                  |
| SC2034: Unused variables in read     | Use `_` for discarded fields                |

### ClickHouse NULL Handling

ClickHouse TSV output uses `\N` for NULL values. In JSON context:

- `\N` is invalid JSON escape → post-process with `sed 's/\\N/NULL/g'`
- `nan` from division by zero → post-process with `sed 's/:nan,/:null,/g; s/:nan}/:null}/g'`
- Always validate JSONL after collection: `python3 -c "import json; [json.loads(l) for l in open('file.jsonl')]"`
