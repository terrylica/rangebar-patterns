**Skill**: [ClickHouse Anti-Patterns](../SKILL.md)

# Infrastructure Anti-Patterns

Environment and toolchain issues that can cause silent failures or misleading results.

---

### INF-01: Stale SSH Tunnels on Port 8123

**Severity**: MEDIUM | **Regression Risk**: MEDIUM

**Symptom**: `data_loader.py` connects to wrong ClickHouse server. Queries return unexpected results or timeout. Local queries unexpectedly route to remote ClickHouse.

**Root Cause**: SSH tunnel `-N -L 8123:localhost:8123 $RANGEBAR_CH_HOST` from a previous session remains open. New session connects to stale tunnel instead of local ClickHouse.

**Resolution**:

1. Kill stale tunnels before querying: `pkill -f "ssh.*8123"`
2. Use dedicated tunnel port for remote ClickHouse: `ssh -N -L 19000:localhost:9000 $RANGEBAR_CH_HOST`
3. Check `_is_port_open(localhost:8123)` before assuming local server
4. Verify with: `clickhouse client --query "SELECT hostName()"`

---

### INF-02: clickhouse Binary Not on PATH

**Severity**: LOW | **Regression Risk**: LOW

**Symptom**: `zsh: command not found: clickhouse-client` or `clickhouse-client`.

**Root Cause**: ClickHouse installed via mise at `~/.local/share/mise/installs/clickhouse/`. Requires mise shim activation in PATH.

**Resolution**:

1. Ensure mise shims first in PATH (via `~/.zshenv`): `export PATH="$HOME/.local/share/mise/shims:$PATH"`
2. Use `clickhouse client` (not `clickhouse-client` — single binary with subcommand)
3. Verify: `which clickhouse` should show mise shim path

---

### INF-03: Schema Mismatch Between remote ClickHouse and Local

**Severity**: MEDIUM | **Regression Risk**: MEDIUM

**Symptom**: `INSERT INTO ... SELECT FROM remote()` fails or inserts wrong columns. Column order differs between remote ClickHouse and local ClickHouse.

**Root Cause**: remote ClickHouse's `range_bars` table was created with different column ordering than `schema.sql`. ClickHouse INSERT depends on column order, not names, when using `SELECT *`.

**Resolution**: Always use explicit column lists. Before syncing, run `SHOW CREATE TABLE` on remote ClickHouse to verify order.

```sql
-- CORRECT: Explicit column list
INSERT INTO rangebar_cache.range_bars (timestamp_ms, symbol, threshold_decimal_bps, ...)
SELECT timestamp_ms, symbol, threshold_decimal_bps, ...
FROM remote('localhost:19000', 'rangebar_cache', 'range_bars', 'default', '')

-- WRONG: Implicit column order
INSERT INTO rangebar_cache.range_bars
SELECT * FROM remote(...)
```
