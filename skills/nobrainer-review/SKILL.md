---
name: nobrainer-review
description: "Use when the owner says nb-review, deep-audit, deep-code-review, or deep-autoreview; explicitly requests an evidence-gated CLOSEOUT, adversarial BUG_HUNT or RELEASE_GATE; or needs final findings filtered to verified actionable defects. Use nobrainer-build for ordinary implementation and correction work."
---

# NoBrainer Review

Review the exact requested change, prove real defects against current code, and
filter out speculative AI noise. This skill owns the final NoBrainer evidence
gate. Ordinary implementation and correction work belongs to
`nobrainer-build` and the project's maintained engineering capabilities. This
skill does not silently implement fixes or expand the product scope.
Use `nobrainer-skill-doctor` for a portfolio-wide audit of instruction and skill
systems; this skill remains the owner of the exact change's final evidence gate.

## Choose one mode

- `CLOSEOUT`: default for an implementation diff before handoff or merge.
- `BUG_HUNT`: adversarial search for reachable defects in an exact module, diff
  or commit.
- `RELEASE_GATE`: acceptance, migration, security, build/runtime and rollback
  evidence for a consequential release.

Do not turn a small diff into a release ceremony. Escalate the mode only when
the changed boundary, risk or owner request justifies it.

## Start gate

Before reviewing:

1. Resolve repository root, current checkout/commit, dirty state and nearest
   instructions.
2. Freeze the scope as exact files, diff, commit, branch/PR base or component.
   Do not review unrelated existing changes.
3. Read the goal/spec/acceptance and relevant tests. If none exists, derive only
   the observable behavior implied by the request and code.
4. Identify high-risk boundaries: authentication, authorization, money, data
   loss, migrations, concurrency, external contracts, user-visible state,
   secrets and irreversible operations.
5. Default to read-only. A review request does not authorize fixes, commits,
   pushes, merges or deployments.

If the base, scope or required runtime is inaccessible, state the exact gap. A
partial review cannot return `CLEAN` for the unavailable surface.

## Pre-read predictions and name/path audit

Before reading implementation details, record two or three falsifiable defect
hypotheses from the acceptance, changed boundary and risk. Include the trigger
and expected impact, but do not report a hypothesis as a finding. At the end,
mark each `HIT`, `MISS` or `UNTESTED` with its evidence. This counters
confirmation bias without inventing bugs.

Before the verdict, run an explicit `NAME_PATH_AUDIT` for every new or renamed
symbol, import, export, configuration key and migration reference. Use a literal
`rg` or project-native checker and retain the command/result or evidence path.
If the scope has none, record `NOT_APPLICABLE`; a green test does not replace
this identity check.

## Pass 1: acceptance and backward trace

Read current files from disk, not remembered implementation context. For each
changed behavior:

- trace from the promised outcome backward through output, state transition,
  caller, input validation and source data;
- inspect the full changed function plus its callers/consumers, not only added
  lines;
- verify renamed/moved symbols, imports, exports, configuration and migrations
  against actual references with the recorded `NAME_PATH_AUDIT`;
- compare public types/contracts and all affected call sites;
- run concrete values through risky conditions, boundaries and error paths;
- compare implemented behavior with acceptance, including negative cases and
  exclusions.

An exit code, generated file, mocked test or worker report is evidence at its
own layer. It does not prove runtime, production or user usefulness unless that
layer was exercised.

## Pass 2: adversarial defect search

Assume at least one defect hypothesis is worth testing, while requiring proof
before reporting it. Check the classes relevant to the scope:

- inverted/missing conditions, empty/null/zero/large inputs and off-by-one;
- stale caller, broken import/export, incompatible schema or API contract;
- lost update, race, retry/idempotence and partial-failure behavior;
- authorization bypass, unsafe input/output, secret leakage and trust-boundary
  confusion;
- rollback gaps, destructive migration, hidden state or duplicate writers;
- error suppression, false success, timeout treated as completion;
- tests that assert a fixture or mock but miss the real integration path.

For `BUG_HUNT`, repeat with a different defect class or data-flow direction
after the first pass. Stop when the bounded scope has been covered and a second
independent pass produces no new verified candidate; never loop merely to invent
findings.

## Independent reviewer

Use a native subagent for delegated review. A separate visible conversation
requires an explicit owner request; `create_thread` is not a subagent fallback.
If native delegation is unavailable, perform the review in MAIN and report
the missing independence. A failed review does not authorize another sidebar
conversation, and a reviewer cannot recursively delegate without express
authority in its assignment.

Use a second model or native review command when change size, unfamiliar code,
security, money/data risk or independence justifies the latency. Keep it
read-only and give it the same frozen scope and acceptance. Prefer the current
client's maintained review capability; do not ship a custom multi-model harness
or spawn an automatic reviewer swarm.

Treat every external finding as an unverified candidate. Re-open the cited code,
trace reachability and reject anything that fails the gate below. Reviewer
agreement does not replace evidence; disagreement is a prompt to inspect, not a
vote.

Choose review perspectives from the actual changed boundary and risk: for example
testing, compatibility, context size or security. Do not automatically run every
available perspective or require maximum reasoning effort for each one. Record
which perspectives were selected and why; unchecked relevant risk remains visible.

## Optional pull-request monitoring

When the owner asks to monitor an open pull request, bind every snapshot and action
to the exact PR head SHA. Check CI, mergeability and published review feedback;
pending draft reviews are not published feedback and must not be marked handled.
After a new head appears, discard conclusions for the old SHA and inspect again.
Retry only a diagnosed transient failure, with a finite recorded budget and a new
fact that justifies each retry. Persistent, branch-caused or ambiguous failures
need diagnosis or a stop, not repeated reruns. A green snapshot is progress, not
merge authorization. Monitoring never grants permission to merge, publish, reply
to reviewers or perform another externally visible action.

## Finding gate

Report a finding only when all are present:

- severity and exact `file:line`;
- reachable input/state/sequence that triggers it;
- observable impact;
- why current guards/tests do not prevent it;
- smallest required fix at the correct ownership boundary;
- regression proof that would fail before and pass after.

Reject style preferences, speculative future risks, unreachable edge cases,
generic “consider refactoring”, dependency guesses without current primary
documentation, and broad rewrites unrelated to a proven defect. Do not pad the
report with low-value observations to look thorough.

## Fix-and-recheck loop

If the owner requested review only, stop after findings. If fixes are also in
scope:

1. route the smallest accepted fix through `nobrainer-build`;
2. run the focused regression plus affected baseline tests;
3. reread the final diff and recheck the original failure path;
4. rerun the relevant review pass once.

A changed fix invalidates earlier test/review evidence for that path. Do not
silently self-approve a consequential release; preserve the owner gate.

## Final output

Lead with actionable findings ordered by severity. For each, use the finding
gate fields and keep the location tight. Then report:

```text
MODE: CLOSEOUT | BUG_HUNT | RELEASE_GATE
SCOPE:
ACCEPTANCE_CHECKED:
PREDICTIONS: <HIT | MISS | UNTESTED with evidence>
NAME_PATH_AUDIT: PASS | NOT_APPLICABLE | PARTIAL | BLOCKED; <command/evidence>
TESTS_AND_RUNTIME:
INDEPENDENT_REVIEW: USED | NOT_JUSTIFIED | UNAVAILABLE
REJECTED_CANDIDATES:
UNCHECKED_SURFACE:
ROLLBACK_OR_FIX_PATH:
RESULT: FINDINGS | CLEAN | PARTIAL | BLOCKED
```

Return `CLEAN` only when the complete frozen scope was inspected, required
evidence passed and no candidate survived verification. Otherwise say `PARTIAL`
or `BLOCKED` and name the missing proof.

## Review convergence

Follow the [delivery contract](../nobrainer-ultra/references/delivery.md#keep-review-proportional-to-progress)
for slice-sized review and correction. Repeated amendments do not reset the
review budget. Keep concrete safety and acceptance blockers open; proceed with
authorized independent work instead of restarting a whole-plan perfection loop.
