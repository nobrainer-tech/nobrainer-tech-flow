---
name: nobrainer-context
description: "Use when one project's instructions for coding agents (AGENTS.md, CLAUDE.md, GEMINI.md, Cursor rules, Copilot instructions) need setup, an audit or tidying: find what each client loads and its size against documented limits, report duplicates and contradictions, then propose one source of truth with short pointers, applied only after approval and read back. Alias: nb-context."
---

# NoBrainer Context

Keep one tidy set of project instructions that every coding agent in use reads.
This module owns the project-instruction boundary of one repository: which files
each client loads, what they cost, where they repeat or disagree, and one
consolidation change. It does not own model selection, global client settings,
session transfer, goal tracking or the delivery workflow.

## Select a mode

- `inspect` (default) - inventory and report. Do not write.
- `consolidate` - inspect, propose one source of truth with pointers, show the
  exact preview, wait for explicit approval, apply project-local edits only,
  then inspect again.
- `repair` - fix one known defect, such as a duplicate managed block, a dangling
  import or a truncated Codex chain. Do not rewrite unrelated instructions.

A question gets `inspect`. Use `consolidate` only when the owner asks to tidy or
set up the project's instructions. Findings are evidence to report, not
permission to edit.

## 1. Inventory what each client loads

Run the bundled read-only probe from the project with Python 3.11+, replacing
`<context-skill-dir>` with this module's directory:

```bash
python3 <context-skill-dir>/scripts/context_inventory.py --json
```

It lists, per client (Codex, Claude Code, Gemini CLI, Cursor, GitHub Copilot,
OpenCode), the files loaded at start, on demand or by import, with bytes, lines
and words; the Codex byte budget and truncation; files over documented line
guidance; byte-identical copies; lines repeated across files; imports of missing
files; settings or Codex configuration it cannot parse; and the Flow goal pointer
state. Instructions in folders below the current one are listed as on demand and
left out of the start-up totals. Add `--include-global` to include each client's
user-level file and, for Claude and Gemini, its recursive imports in the same
size, duplicate and goal-pointer checks. Claude's 200-line guidance applies only
to `CLAUDE.md` files discovered directly, not imported files, `AGENTS.md` fallbacks
or `.claude/rules/*.md` rules. Use `--client NAME` to narrow the report and
`--goal-file PATH` for an explicit goal file.
`scripts/codex_context.py --check --json` keeps the detailed Codex chain probe.

The probe applies the rules in [clients.md](references/clients.md). Only those
documented behaviours count; anything marked `UNVERIFIED` there is reported as
unknown, never as a limit. Ask which clients the team actually uses when the
files alone do not say, and drop the others from the report.

## 2. Report duplicates and contradictions

Repeated lines come from the probe. Contradictions need reading: compare the
files a client loads together for different commands, package managers, test
gates, branch rules, languages or tone, and for a file that tells the agent to
read another file in words instead of importing it. Report each with exact
`file:line` pairs. This step is report-only.

## 3. Propose one source of truth

Follow [consolidate.md](references/consolidate.md). The usual shape is
`AGENTS.md` as the source of truth, `CLAUDE.md` holding `@AGENTS.md` plus only
Claude-specific lines, and each other client's file reduced to a pointer or to
the lines that client alone needs. Show the full preview (new bytes or a diff
per file), what each client will load afterwards and the rollback, then wait
for explicit approval. Apply only inside the project. Never edit global
instruction files, `~/.codex/config.toml`, `~/.gemini/settings.json`, client
settings, credentials or plugin installs unless the owner asks for that
separate action.

## 4. Read back

After a change, run the probe again and compare it with the preview. That is a
file-level readback. Mark `RUNTIME_READBACK: VERIFIED` only from a client's own
output that lists loaded files in a fresh session, as listed per client in
[clients.md](references/clients.md); otherwise `UNKNOWN`. A probe exit code or
an installed module does not prove a client followed the instructions.

## 5. Goal pointer

When the project keeps a Flow goal file (`GOAL_ID:` block, see
[long-run state](../nobrainer-tech-flow/references/long-run-state.md)), check
that the instructions name the current one and no stale or missing goal path.
Propose the one-line pointer fix in the same preview. Goal content, status and
handoff stay with `nobrainer-tech-flow` and `nobrainer-sessions`.
If no active goals remain, the pointer state is `NONE`, including when completed
goals are still mentioned; a pointer to a missing file remains `STALE_POINTER`.

## Closeout

```text
CONTEXT: CURRENT | ATTENTION | UPDATED | BLOCKED
PROJECT_ROOT: <path or UNKNOWN>
CLIENTS: <client: loaded files and bytes, one per line>
LIMITS: <truncated or over-guidance files, or NONE>
DUPLICATES: <count and top file:line pairs, or NONE>
CONTRADICTIONS: <file:line pairs, or NONE>
SOURCE_OF_TRUTH: <file, or NOT_PROPOSED>
GOAL_POINTER: NONE | POINTED | NOT_POINTED | STALE_POINTER
PROJECT_WRITE: NONE | <files changed>
RUNTIME_READBACK: VERIFIED | UNKNOWN | UNSUPPORTED
OWNER_ACTION_REQUIRED: <one exact action or NONE>
ROLLBACK: <exact preimages or NOT_APPLICABLE>
```

Route audits across many projects or skill portfolios to
`nobrainer-skill-doctor`, broader setup and delivery to `nobrainer-tech-flow`,
context transfer to `nobrainer-sessions` and release closeout to
`nobrainer-review`.
