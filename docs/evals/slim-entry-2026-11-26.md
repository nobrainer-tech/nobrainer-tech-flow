# Slimmer entry skill: done-gap rerun for 2.13.0 — 2026-11-26

The question: after cutting `skills/nobrainer-tech-flow/SKILL.md` and making a separate
worktree optional, does Flow on request still finish the same tasks, and does it cost at
least 15% less per verified fix than in the [2.12 run](done-gap-2026-11-21.md)?

## What changed

Candidate `2206abf` (skills and `adapters/bootstrap.md` frozen from that commit):

- **Entry skill:** from 2208 to 1575 words. The scope contract, the detailed-ledger gate,
  readiness and receive-audit detail moved to
  [full lifecycle](../../skills/nobrainer-tech-flow/references/full-lifecycle.md), which
  the skill sends an agent to only for multi-session, delegated or public-contract work.
  The stages are a checklist that skips any stage adding nothing.
- **Worktree:** [worktree rule](../../skills/nobrainer-tech-flow/references/worktrees.md):
  the agent works in the opened checkout unless the user asks for a worktree, the checkout
  holds work the task must not touch, or another writer shares it.
- **Delegation and PR watching:** `skills/nobrainer-team/SKILL.md` and `delivery.md` no
  longer read as "dispatch as many as fit"; in Claude Code, `/ship` and `/steward` own PR
  watching when the user runs them. `skills/nobrainer-sessions/SKILL.md` uses a task
  worktree when a session shares its repository with another writer, in line with the
  new rule. Neither skill is loaded in these single-session tasks, so this eval does not
  exercise their change; it checks only that the entry path did not regress.

Why these: three diagnostic FLOW_ASK runs on `247d39d` (D1, D4, D8) read no reference
file. The extra cost came from the skill body, which is resent every turn, and from extra
work it asked for. The one 2.12 failure came from the default worktree.

## Method

The same harness, tasks and hidden checks as the 2.12 run
([artifacts](artifacts/done-gap/)). Two arms only, **PLAIN** and **FLOW_ASK**, two runs
per task (40 runs). Claude Code CLI 2.1.331, `claude-opus-5-5` at `medium`. The pass
line was fixed before the first run: FLOW_ASK passes at least 19 of 20 on the first turn
and costs at most 0.337 per verified fix (15% below 0.397). Counted with
[gate_213.py](artifacts/done-gap/gate_213.py), which reuses `score.py`'s loader and its
validity checks (cost telemetry, manipulation check, client errors).
[Per-run table](artifacts/done-gap/results-2.13.0.tsv).

## Results

| Arm | Passed on turn 1 | Passed in the end | False "done" | Cost | Cost per fix | Mean turns |
|---|---|---|---|---|---|---|
| PLAIN | 20 of 20 | 20 of 20 | 0 | 5.375 | 0.269 | 9.0 |
| FLOW_ASK, 2.13.0 candidate | 20 of 20 | 20 of 20 | 0 | 6.654 | 0.333 | 10.7 |
| FLOW_ASK, 2.12 (2026-11-21) | 19 of 20 | 20 of 20 | 0 or 1 | 7.935 | 0.397 | 12.5 (median) |

GATE: `PASS`. Flow on request costs 16% less per verified fix than in 2.12 (0.333 against
0.397) and passed every task on the first turn. Against plain Claude Code it now costs
1.24 times as much per fix, down from 1.47. PLAIN was stable: 0.269 per fix in both runs.

No FLOW_ASK run created a worktree, and every one ended with the handoff block.

| Task | PLAIN | FLOW_ASK | Ratio |
|---|---|---|---|
| D1 | 0.194 | 0.234 | 1.21 |
| D2 | 0.254 | 0.341 | 1.34 |
| D3 | 0.298 | 0.358 | 1.20 |
| D4 | 0.305 | 0.426 | 1.40 |
| D5 | 0.242 | 0.373 | 1.54 |
| D6 | 0.356 | 0.395 | 1.11 |
| D7 | 0.285 | 0.288 | 1.01 |
| D8 | 0.168 | 0.247 | 1.48 |
| D9 | 0.327 | 0.327 | 1.00 |
| D10 | 0.260 | 0.338 | 1.30 |

## Limits

- The pass was narrow: 0.333 against a line of 0.337. Two runs per task; a rerun could
  land on either side.
- About two fifths of the saving is D4 (1.390 against 0.852): in 2.12 one D4 run needed
  a retry turn after the worktree miss, and here none did. On the other nine tasks the
  cost per fix fell from 0.364 to 0.322, about 11%.
- The FLOW arm (installed, not asked for) was not rerun; its always-on cost was 1.11 times
  PLAIN in 2.12 and is not re-measured here.
- Plain Claude Code still fell into no trap, so this set shows cost, not benefit. Flow
  remains more expensive than plain Claude Code on these tasks; the release claims only
  that it got cheaper.
