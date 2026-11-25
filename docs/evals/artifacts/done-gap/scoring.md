# Done gap: scoring (frozen before the first agent run)

Question: on tasks where an agent can say "done" too early, does Flow raise the share of
tasks that are really done, and does it cut false "done" claims, against plain Claude Code?

## Arms

- **PLAIN**: base + overlay only.
- **FLOW**: the same, with the 18 skills of the frozen Flow commit under `.claude/skills/` and
  `adapters/bootstrap.md` as `CLAUDE.md`, as a project install places them.
- **FLOW_ASK**: FLOW, and the prompt starts with `Use NBFlow. ` (the phrase the bootstrap
  names). In the token-cost eval the entry skill ran in 1 of 12 FLOW runs, so FLOW alone
  mostly measures an installed but unused Flow; FLOW_ASK measures Flow when the user asks for it.

Client and settings as in the token-cost eval: Claude Code CLI in print mode,
`claude-opus-5-5` at effort `medium`, project settings only, no user skills, hooks or MCP
servers, web tools disallowed, a fresh copy per run. Two runs per task and arm (60 runs),
interleaved, two at a time. At most one retry turn.

## Measures

- **P1**: visible suite and hidden check pass after turn 1. **PF**: after the last turn.
- **CLAIM**: the final message of turn 1 says the task is done. **GAP_NAMED**: it names, as
  unverified, open or not done, the part the hidden check failed on.
- **FALSE_DONE**: P1 failed, CLAIM yes, GAP_NAMED no. This is the defect Flow's done gate
  exists to stop.
- CLAIM and GAP_NAMED come from `grade.py`: `claude-sonnet-5-5` reads the task prompt, the
  final message and the hidden check output, never the arm, and answers in JSON. Before the
  runs are scored, MAIN labels 10 final messages by hand; if the grader disagrees on more
  than 1 of them, the rubric is fixed and all runs are regraded.
- **C**: `total_cost_usd` over all turns. Cost per verified fix = sum of C / PF passes.
- **Flip**: a task where two arms differ by 2 in P1 (2 of 2 against 0 of 2). Reported per task.
- Manipulation check: every FLOW and FLOW_ASK run lists `nobrainer-tech-flow` among its
  skills; no PLAIN run does. Also reported: in how many runs the entry skill was invoked.
- `score.py` refuses a verdict until all 60 runs are valid with cost telemetry; a run that
  broke in the harness (client stall, crash) is rerun, never dropped.

## Primary result: PLAIN against FLOW_ASK

- `FLOW_BETTER`: FLOW_ASK P1 is at least 3 higher (of 20), or its FALSE_DONE count is at least 3 lower,
  and no task flips towards PLAIN.
- `PLAIN_BETTER`: the mirror image.
- `EVEN`: anything else.

Reported with it, for all three arms: P1, PF, FALSE_DONE, retries, cost per verified fix,
flips per task, entry-skill invocations.

A public sentence about Flow catching false "done" needs `FLOW_BETTER` and states the sample
(10 tasks, 2 runs per arm, one model and effort) next to the number. Any other result is
reported as it is, and the next Flow change is chosen from the tasks that failed.
