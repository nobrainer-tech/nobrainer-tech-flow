# OpenAI review test cases

Recorded with `npm run transcripts -- --in-memory` (1.0.0+flow.2.7.0, MCP 2025-11-25, official
TypeScript SDK client; InMemoryTransport with buildServer, no HTTP listener).
Tokens are shortened to `<token>`; all other output is exact. The five positive
cases cover all six tools. Paste the prompts and expected results into the portal review form.

## Summary

- PASS QUICK path with AC01 test/local and AC02 file/static and a DRIFT_CHECK step
- PASS blocked card with 1-6 verbatim rules and a source
- PASS FAILED then REJECTED COUNTS_MISMATCH
- PASS NOT_DONE with AC02 missing and no receipt
- PASS DONE_WITH_GAPS and the handoff lists AC01 proof and AC02 not checked
- PASS legacy Coding maps to terminal-coding with a nonempty shortlist
- PASS shortlist of 1-3 with snapshot date and source

## P1. Start a contract

Prompt: "Use NoBrainer Tech Flow. I need the date parser bug fixed: parse('2026-02-30') should raise an error. Done means the new unit test passes and the change is documented in CHANGELOG.md."

Expected tools: start_flow_task

Expected result: Path QUICK, items AC01 (test, local) and AC02 (file, static), first step DRIFT_CHECK, a token

Call `start_flow_task`

```json
{
 "outcome": "parse('2026-02-30') raises an error for library users",
 "dod": [
  {
   "text": "new unit test for 2026-02-30 passes",
   "proof": "test"
  },
  {
   "text": "CHANGELOG.md documents the fix",
   "proof": "file"
  }
 ]
}
```

Result

```json
{
 "path": "QUICK",
 "flow_version": "2.7.0",
 "contract": "28ca7a48",
 "items": [
  {
   "id": "AC01",
   "proof": "test",
   "level": "local"
  },
  {
   "id": "AC02",
   "proof": "file",
   "level": "static"
  }
 ],
 "modules": [],
 "next": {
  "stage": "DRIFT_CHECK",
  "rules": [
   "Inspect the actual inputs, instructions and required capabilities; for project work include dirty state, callers, tests and existing plan/spec.",
   "Prior summaries, wiki and worker reports are context, not proof"
  ],
  "source": "skills/nobrainer-tech-flow/SKILL.md#drift_check-establish-current-truth"
 },
 "token": "nbf1.<token>"
}
```

Check: PASS - QUICK path with AC01 test/local and AC02 file/static and a DRIFT_CHECK step

## P2. Guidance for a blocker

Prompt: "With NoBrainer Tech Flow: I can't run the tests because the CI runner is down. What should I do?"

Expected tools: get_flow_step (event blocked)

Expected result: Up to six rules from the Flow delivery reference: identify the failed operation, try a permitted alternative, never evade a denial, continue independent items, and the four blocker categories

Call `get_flow_step`

```json
{
 "event": "blocked"
}
```

Result

```json
{
 "card": "event:blocked",
 "flow_version": "2.7.0",
 "rules": [
  "Before saying BLOCKED, identify the exact failed operation and the acceptance item it prevents.",
  "If the preferred method is technically unavailable, try a relevant permitted alternative within the same scope.",
  "Never evade an access denial, approval rejection, sandbox or an explicit channel restriction through another method.",
  "Continue independent acceptance items.",
  "A failed test is a repair task.",
  "Distinguish OWNER_ACTION, EXTERNAL_UNAVAILABLE, POLICY_DENIED and TECHNICAL_FAILURE."
 ],
 "source": "skills/nobrainer-tech-flow/references/delivery.md#resolve-an-obstacle-before-escalating-it",
 "next": "AUTOPILOT"
}
```

Check: PASS - blocked card with 1-6 verbatim rules and a source

## P3. Evidence: a failing run and an inconsistent claim

Prompt: "Here is the pytest output (it ends with 1 failed, 4 passed). The tests pass, right?"

Expected tools: check_flow_evidence

Expected result: AC01 FAILED; a record claiming failed: 0 for the same output is REJECTED with COUNTS_MISMATCH

Call `check_flow_evidence`

```json
{
 "token": "nbf1.<token>",
 "evidence": [
  {
   "item": "AC01",
   "kind": "test",
   "cmd": "pytest -q",
   "exit": 1,
   "out": "FAILED tests/test_dates.py::test_feb_30 - DID NOT RAISE ValueError\n========================= 1 failed, 4 passed in 0.21s ========================="
  },
  {
   "item": "AC01",
   "kind": "test",
   "cmd": "pytest -q",
   "exit": 1,
   "out": "FAILED tests/test_dates.py::test_feb_30 - DID NOT RAISE ValueError\n========================= 1 failed, 4 passed in 0.21s =========================",
   "failed": 0
  }
 ]
}
```

Result

```json
{
 "results": [
  {
   "item": "AC01",
   "verdict": "FAILED",
   "digest": "a3515266"
  },
  {
   "item": "AC01",
   "verdict": "REJECTED",
   "code": "COUNTS_MISMATCH",
   "why": "AC01: claimed counts differ from the output (4 passed, 1 failed)."
  }
 ],
 "open": [
  "AC01",
  "AC02"
 ],
 "token": "nbf1.<token>"
}
```

Check: PASS - FAILED then REJECTED COUNTS_MISMATCH

## P4. Done gate and a gap-aware handoff

Prompt: "I fixed it and the tests pass now. Is the task done? I have no access to the changelog, so mark AC02 as not checked and write the handoff."

Expected tools: check_flow_evidence, check_flow_done, draft_flow_handoff

Expected result: NOT_DONE with AC02 missing; then DONE_WITH_GAPS and a handoff that lists AC01 proof and AC02 under Not checked

Call `check_flow_evidence`

```json
{
 "token": "nbf1.<token>",
 "evidence": [
  {
   "item": "AC01",
   "kind": "test",
   "cmd": "pytest -q",
   "exit": 0,
   "out": "tests/test_dates.py .....\n============================== 5 passed in 0.18s ===============================",
   "passed": 5,
   "failed": 0
  }
 ]
}
```

Result

```json
{
 "results": [
  {
   "item": "AC01",
   "verdict": "ACCEPTED",
   "level": "local",
   "digest": "13848f53"
  }
 ],
 "open": [
  "AC02"
 ],
 "token": "nbf1.<token>"
}
```

Call `check_flow_done`

```json
{
 "token": "nbf1.<token>"
}
```

Result

```json
{
 "verdict": "NOT_DONE",
 "missing": [
  {
   "item": "AC02",
   "need": "file evidence, level static"
  }
 ],
 "stale": [],
 "unchecked": []
}
```

Check: PASS - NOT_DONE with AC02 missing and no receipt

Call `check_flow_done`

```json
{
 "token": "nbf1.<token>",
 "unchecked": [
  {
   "item": "AC02",
   "reason": "no access to the repository changelog"
  }
 ]
}
```

Result

```json
{
 "verdict": "DONE_WITH_GAPS",
 "missing": [],
 "stale": [],
 "unchecked": [
  "AC02"
 ],
 "receipt": "nbr1.<token>",
 "next": "draft_flow_handoff"
}
```

Call `draft_flow_handoff`

```json
{
 "receipt": "nbr1.<token>"
}
```

Result

```json
{
 "verdict": "DONE_WITH_GAPS",
 "markdown": "## Delivered\n<one sentence: the observable outcome>\n\n## Proof\n- AC01 test, local, accepted (digest 13848f53): <command and result>\n\n## Not checked\n- AC02: <reason>\n\n## Decisions left to you\n<owner decisions, or 'None'>\n\n## Next action\n<one action, or 'None'>\n\nContract 28ca7a48, Flow 2.7.0. Evidence was reported by the agent; the server checked consistency, not truth."
}
```

Check: PASS - DONE_WITH_GAPS and the handoff lists AC01 proof and AC02 not checked

## P5. Model advice from the benchmark

Prompt: "With NoBrainer Tech Flow: I use Codex and Claude Code. Recommend a model using the legacy task Coding."

Expected tools: recommend_flow_model

Expected result: The case-insensitive legacy Coding alias returns task terminal-coding with a nonempty top-3 shortlist, quality, cost and time from the pinned benchmark snapshot, its date, expiry and the source URL

Call `recommend_flow_model`

```json
{
 "task": "Coding",
 "have": [
  "codex",
  "claude-code"
 ]
}
```

Result

```json
{
 "task": "terminal-coding",
 "priority": "balanced",
 "role": "worker",
 "expired": false,
 "expires": "2026-11-06",
 "cohort": "terminal-bench",
 "scale": "Task success, %",
 "shortlist": [
  {
   "model": "anthropic/claude-sonnet-5-5",
   "effort": "max",
   "quality": 61.8,
   "range": [
    58.9,
    64.8
   ],
   "cost_usd": 22.2,
   "cost_per_success_usd": 35.9,
   "cost_kind": "observed",
   "seconds": 7432,
   "time_kind": "observed",
   "harness": "claude-code"
  },
  {
   "model": "openai/gpt-6.1-sol",
   "effort": "max",
   "quality": 58.2,
   "range": [
    55.1,
    61.3
   ],
   "cost_usd": 1.92,
   "cost_per_success_usd": 3.3,
   "cost_kind": "observed",
   "seconds": 3177,
   "time_kind": "observed",
   "harness": "codex",
   "eligible": false
  },
  {
   "model": "openai/gpt-6-luna",
   "effort": "max",
   "quality": 16.4,
   "range": [
    13.6,
    19.1
   ],
   "cost_usd": 0.219,
   "cost_per_success_usd": 1.34,
   "cost_kind": "observed",
   "seconds": 2284,
   "time_kind": "observed",
   "harness": "codex",
   "eligible": false
  }
 ],
 "why": "Equal ordinal ranks of quality lower bound, cost and time within the normal quality band. Comparable harness and evidence kinds after plan order; a policy heuristic.",
 "note": "Cost and time are per-task reference figures, not invoices.",
 "snapshot": "2026-10-23",
 "snapshot_sha": "8dab56e2",
 "source": "https://nobrainer.tech/ai/benchmark/"
}
```

Check: PASS - legacy Coding maps to terminal-coding with a nonempty shortlist

Check: PASS - shortlist of 1-3 with snapshot date and source

## Negative cases (the model should not call Flow tools)

These are model behaviours, so they are checked in the client, not by the server. Every tool is read-only
(`readOnlyHint: true`, `openWorldHint: false`), so no tool can deploy or change anything even if called.

| # | Prompt | Why the plugin should not act | Expected behaviour |
|---|---|---|---|
| N1 | "What is the capital of Australia?" | A simple fact; no task contract is needed | Direct answer, no Flow tool call |
| N2 | "Write a four-line poem about autumn." | Creative chat with no proof to check | Direct answer, no Flow tool call |
| N3 | "Deploy my app to production now." | The plugin does not deploy or run commands | No Flow tool call that claims an effect; the model says the plugin does not deploy |

