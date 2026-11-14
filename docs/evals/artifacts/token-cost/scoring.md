# Token cost: scoring (frozen before the first run)

Question: does installing Flow change what a Claude Code user spends to reach a verified fix?

## Arms

- **PLAIN**: the fixture alone. No `CLAUDE.md`, no skills.
- **FLOW**: the same fixture plus what a project install of Flow puts there: the 18 skills from
  `skills/` at the tested commit under `.claude/skills/`, and `adapters/bootstrap.md` as
  `CLAUDE.md`.

Both arms: Claude Code CLI 2.1.325 in print mode, `claude-opus-5-5` at effort `medium`,
`--setting-sources project,local --strict-mcp-config` (no user settings, skills, hooks or MCP
servers), web tools disallowed, all other built-in tools allowed, a fresh copy per run. Each
task runs twice per arm, interleaved, four runs at a time.

Manipulation check: the `init` event of every FLOW run lists `nobrainer-tech-flow` among the
skills, and no PLAIN run does. A run that fails this check is discarded and rerun.

## Measures (from the `result` events of the stream-json transcripts, both turns summed)

- **C**: `total_cost_usd`, the client's list-price estimate, subagents included. Not a bill:
  subscription users pay a plan, and this measures how much of it a task uses.
- **Tokens**: from `modelUsage`, summed over models: input, cache write, cache read, output.
- **P1**: hidden check passes after the first turn. **P2**: passes after the retry turn.
- **Turns** (agent loop iterations) and wall time, reported only.

## Primary result

Cost per verified fix = sum of C over all runs of an arm / number of runs with P2 pass.

RATIO = FLOW cost per verified fix / PLAIN cost per verified fix.

- `FLOW_SAVES`: RATIO <= 0.90 and FLOW P2 passes >= PLAIN P2 passes.
- `EVEN`: 0.90 < RATIO < 1.10.
- `FLOW_COSTS_MORE`: RATIO >= 1.10.

Also reported per task: mean C per arm and the per-task ratio, so one expensive run cannot
hide behind the total. No public claim of savings unless the result is `FLOW_SAVES`.

## Not measured

Caveman or any other compressor (third-party binaries, owner decision pending); other models,
efforts and clients; interactive desktop sessions; long multi-hour work.
