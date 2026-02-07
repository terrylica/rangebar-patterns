# Sweep Scripts - AI Context

**Scope**: Bash scripts for brute-force SQL sweep execution on BigBlack via pueue.

**Navigation**: [Root CLAUDE.md](/CLAUDE.md)

---

## Directory Convention

```
scripts/gen{NNN}/
├── generate.sh     # Pre-generate SQL files from templates (runs locally)
├── poc.sh          # Fail-fast POC (10 configs, validates pipeline end-to-end)
├── submit.sh       # rsync SQL to BigBlack + submit to pueue (p1 group, 4 parallel)
├── status.sh       # Check pueue status + result counts on BigBlack
├── collect.sh      # scp results from BigBlack to logs/gen{NNN}/
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

## Execution Pipeline (BigBlack)

```
Local (macOS)                    BigBlack (ClickHouse + pueue)
┌─────────────────┐              ┌──────────────────────────┐
│ 1. generate.sh  │              │                          │
│    Creates SQL   │   rsync →   │ /tmp/gen{NNN}_sql/       │
│    in /tmp/      │              │                          │
│                  │              │ 2. submit.sh             │
│                  │   ssh →     │    pueue add -g p1       │
│                  │              │    (4 parallel slots)    │
│                  │              │                          │
│ 3. status.sh    │   ssh →     │    pueue status -g p1    │
│                  │              │                          │
│ 4. collect.sh   │   ← scp     │ /tmp/gen{NNN}_*.jsonl    │
│    to logs/      │              │                          │
│                  │              │ Each pueue job:          │
│ 5. report.sh    │              │   clickhouse-client      │
│    Analyze       │              │     < config_N.sql       │
│                  │              │     >> results.jsonl     │
│                  │              │   (flock for concurrency)│
└─────────────────┘              └──────────────────────────┘
```

---

## Pueue Job Management

All jobs use **pueue group `p1`** with 4 parallel slots on BigBlack.

```bash
# Check status
ssh bigblack 'pueue status -g p1'

# Clean completed jobs before new submission
ssh bigblack 'pueue clean -g p1'

# Reset failed/stuck jobs
ssh bigblack 'pueue reset -g p1'
```

### Job Wrapper Pattern

Each pueue task runs a wrapper script on BigBlack that:

1. Executes SQL via `clickhouse-client --multiquery`
2. Parses tab-separated output
3. Constructs NDJSON telemetry line
4. Appends atomically using `flock` for concurrent write safety

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
