# Long-run state and recovery

Read this reference only after Ultra's detailed-ledger gate passes. It preserves
safe resume and delegated coordination without forcing machine ceremony into
ordinary single-session work.

## One canonical ledger

Use the project's existing Markdown tracker when suitable. Otherwise create one
small task-local Markdown artifact. It is the only mutable owner of execution state;
specifications define required truth, reports provide evidence, and the wiki
stores durable knowledge.

Record the run boundary once:

```text
Run:
Frozen request/spec and fingerprint:
Base checkout and commit:
State owner:
Integration owner:
Owner gates:
Stop conditions:
```

Use one row per independently auditable outcome, not per command:

```text
ID | Outcome | Method | Owner/session | Dependencies | Write scope |
Proof | Owner gate | Status
```

`Method` is one primary owner: a NoBrainer skill, maintained project capability,
reviewed temporary capability or `DIRECT` for a truly mechanical step. Known
implementation, verification, correction, integration and closeout work must
appear before execution starts.

Useful states are `PENDING`, `READY`, `RUNNING`, `BLOCKED`, `REPORTED`,
`AUDITED`, `ACCEPTED`, `CORRECTION_REQUIRED`, `OWNER_DECISION_REQUIRED` and
`STOPPED`. A report or green
exit code cannot move a row to `ACCEPTED` without current proof.

The owner-facing Progress checklist is only a view of this ledger. Update both
from the same evidence at meaningful transitions.

## Durable goal and resume

When this reference is active, keep the portable goal in an existing Markdown
tracker or one task-local Markdown `GOAL_FILE`. Do not create a second mutable
status owner. The minimum readable block is:

```text
GOAL_ID: <stable identity>
OUTCOME: <observable result>
NON_GOALS: <bounded exclusions>
DOD: <acceptance checks>
STATUS: ACTIVE | OWNER_DECISION_REQUIRED | COMPLETE | BLOCKED
CHECKPOINT: <last verified state and evidence pointer>
NEXT_SAFE_ACTION: <one action or NONE>
SESSION_POLICY: <policy reference or NONE>
LAST_HEALTH_READBACK: <event, result, evidence pointer>
```

The Markdown goal works without any native goal API. A host-native goal is an
optional mirror and control handle, used only when available and authorized by
the host's tool rules; never create it merely because this reference was loaded.
After session start, compaction or a verified clear, read `GOAL_FILE` from disk,
verify `GOAL_ID`, repository, checkout, HEAD/dirty state, status and evidence,
then reconcile any native goal actually used and continue from `NEXT_SAFE_ACTION`. A
transcript summary, cached plan or native goal never overrides newer file state.
The same file owns the outcome-level TODO rows; health gates may checkpoint them
but cannot mark work complete. On every material transition, update the current
row, evidence and next safe action before starting another unit.

## Recovery card

For unattended or resumable work, record:

```text
Trigger and frozen inputs:
Expected outputs:
Checkpoint and resume command/path:
Idempotence key or duplicate-prevention rule:
Retry budget and blocker fingerprint:
Evidence location:
Rollback:
Attention budget and urgent owner events:
```

Do not invent a retry path. If a step cannot be safely resumed or repeated,
state that before starting it and require the appropriate checkpoint or owner
gate.

At session start or after compaction, reconcile the exact checkout, base/HEAD,
dirty state, ledger fingerprint, active sessions/writers, last accepted proof
and next `READY` row. A stale summary never authorizes a successor.

## Bounded turns and runtime release

An outcome or goal may span bounded turns, but it never grants an unlimited
turn/session lease. Run `SESSION_HEALTH_GATE` at `START`, `AFTER_COMPACTION`,
`MATERIAL_TRANSITION` and `BEFORE_CLOSEOUT`. The policy is host/config supplied;
these are policy fields, not universal limits:

```text
TURN_AGE_LIMIT: <configured value | NONE>
HISTORY_SIZE_LIMIT: <configured value | NONE>
COMPACTION_LIMIT: <configured value | NONE>
COST_OR_TOKENS_LIMIT: <configured value | NONE>
WARNING_THRESHOLD: <configured value | NONE>
HARD_THRESHOLD: <configured value | NONE>
SIGNALS: <turn age, history size, compactions, cost/tokens, owned workers>
```

Each signal is a readback value, `UNKNOWN`, `UNSUPPORTED`, or `NONE` when no
limit is configured. Missing expected telemetry is not `HEALTHY`. Missing optional
telemetry lowers that proof claim but does not block safe work: use bounded work
units and the Markdown checkpoint. An explicitly required hard budget that cannot
be measured or enforced blocks only the work depending on that guarantee; report
the missing capability instead of claiming the cap holds. The gate
result is `HEALTHY | WARNING | ROTATE_REQUIRED | UNKNOWN | UNSUPPORTED`. A
warning checkpoints the goal/TODO and stops starting optional workers or large
new units while continuing the safe current unit. A hard limit means persist `GOAL_FILE`,
write a compact handoff, verify no write is in flight, and select:

```text
CLEAR_MODE: HOST_CLEAR | END_TURN | MANUAL_REQUIRED | UNSUPPORTED
```

Use `HOST_CLEAR` only when the host advertises the capability and readback
proves the same goal file remains durable and no task-owned writer is active.
Otherwise end the turn or require manual action. Never claim a clear from a
command submission alone. Creating or rotating a session requires current or standing task authorization
under the Sessions startup contract; do not infer it from a timeout, compaction
or continued goal. Explicit Flow invocation activates assessment; stricter host
consent requirements still apply.

`task_complete` closes an outcome only; it does not prove `RUNTIME_RELEASE`.
Record `RUNTIME_RELEASE` as `VERIFIED | NOT_RELEASED | UNKNOWN | UNSUPPORTED`.
Where the host can read back task-owned browser, tool or subprocess workers,
`VERIFIED` requires no owned worker remains. Active workers are
`NOT_RELEASED`; missing or unsupported readback lowers runtime proof and never
supports a clean-runtime claim.

An empty ready set is not itself a blocker. If work is `RUNNING`, wait for its
bounded result; if `REPORTED`, audit it; if all acceptance is met, finish. If all
unfinished work is blocked, record the blocker, owner and next unblock step;
use `OWNER_DECISION_REQUIRED` only when an actual owner decision is needed.
Do not invent work to keep a goal active.

## Team, queue and transport

Use one primary MAIN session. A native subagent with a returned ID, bounded task,
disjoint write scope and observable completion needs no new visible task or
persistent session registry. Audit its artifact and termination before integration.
Create a durable visible session only on an explicit owner request for that
conversation or an explicitly authorized MAIN restart. Visibility, reuse,
isolation, review retries and handoff needs alone do not authorize creation.
Use native subagents for delegated units; if unavailable, continue in MAIN.
For a persistent delegated queue:

1. `nobrainer-team` proves the minimum roster and bounded work units.
2. If several delegated units form a queue, `nobrainer-dispatcher` computes the
   ready set and bounded batch.
3. `nobrainer-sessions` alone creates/reuses exact sessions, checks identity and
   writer state, and sends each bounded unit.
4. Dispatcher may record `READY -> SENT` only from that transport readback.

The canonical queued transition is:

`Team -> Dispatcher SCHEDULE -> Sessions setup/delegate -> Dispatcher DISPATCH`

Sessions alone performs identity preflight and transport. Dispatcher never
duplicates that send or treats a planned assignment as delivered.

A worker receives one outcome, inputs, exact write scope, proof, stop conditions
and report destination. It never chooses a successor.

When a worker reports, Sessions performs `RECEIVE_AUDIT` against the exact
session, host, checkout, commit, diff, tests, evidence and released writer state.
If Dispatcher owns the queue, its reconcile step consumes that audited result
before releasing dependencies.

## Failure and correction

- Unknown dependency, identity, write ownership or lease state is `BLOCKED`.
- A changed owner decision supersedes the old requirement, stops affected
  not-started rows and invalidates dependent proof.
- A verified review finding becomes `CORRECTION_REQUIRED` and returns to Build.
- A repeated blocker keeps one stable fingerprint; retry only after a changed
  condition or new evidence.
- Timeout, dead session, partial output and retry exhaustion preserve the row as
  incomplete.

Close the ledger only when every required row is `ACCEPTED` or explicitly
`STOPPED` by a superseding owner decision, all writers are released, final proof
is current and rollback is still intelligible.

## Adaptive fresh-session continuation

For owner-enabled `session-restart`, reuse this goal and its progress rows.
Sessions owns the [restart protocol](../../nobrainer-sessions/references/session-restart.md):
quiet milestone assessment, compact checkpoint, verified fresh target, conditional
ownership transfer and source archive after takeover. A stale summary or timer
does not authorize a successor. Keep model policy, pending operations and native
goal/scheduler ownership in the handoff; do not create another status owner.
