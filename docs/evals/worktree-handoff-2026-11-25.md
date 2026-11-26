# Worktree handoff: say where the work is — 2026-11-25

Changed skill: `skills/nobrainer-tech-flow` (`references/worktrees.md`).

## Scenario

In the [done-gap eval](done-gap-2026-11-21.md), task D4 with `Use NBFlow.`, second run: Flow
followed its worktree default, wrote a correct change into a new worktree in a scratch
folder on branch `feat/returns`, and closed with "Not checked: None". The checkout the user
opened showed no change, and the hidden acceptance check run there failed. The report named
the branch but not the worktree path, and did not say the checkout was unchanged.

## Change

- Every handoff and final report names the worktree path and task branch, states that the
  original checkout is unchanged, and gives the one command that shows the result.
- The worktree goes where the host keeps worktrees for that repository (in Claude Code,
  `.claude/worktrees/<name>`), not in a temporary folder the host may clear.

## Check

The same task and harness (done-gap `run.py`, Claude Code CLI print mode,
`claude-opus-5-5` at `medium`), FLOW_ASK arm, four fresh runs with the changed skills:

| Run | Passed on turn 1 | Separate worktree | Cost |
|---|---|---|---|
| 1 | yes | no | 0.420 |
| 2 | yes | no | 0.421 |
| 3 | yes | no | 0.418 |
| 4 | yes | no | 0.398 |

Before the change: 1 of 2 runs of this task failed turn 1 for this reason.

## Limits

No rerun used a separate worktree, so the new report line itself was not exercised; the
check shows only that the change did not break the task (4 of 4 passed). Four runs cannot
tell whether the change, or chance, removed the worktree use. The deterministic suite
covers structure, not this behaviour.
