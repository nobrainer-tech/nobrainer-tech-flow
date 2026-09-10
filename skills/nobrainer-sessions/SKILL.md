---
name: nobrainer-sessions
description: "Use when the owner says nb-sessions, nb-multi, session-handoff, session-restart, or nb-session-restart, or asks for visible named reusable multi-session work with exact identity, isolated write scopes, audited handoffs, recovery, or controlled parallelism; do not use for a coherent one-session task."
---

# NoBrainer Sessions

Operate visible sessions as a small control plane. Human-readable titles make
the workflow understandable; exact identity and readback make it trustworthy.
This skill does not invent the project plan, select the ready batch or replace
implementation skills. `nobrainer-dispatcher` owns scheduling when a queue has
multiple delegated units.

Describe the outcome, success criteria and verification, let one project-level
session prepare bounded task prompts, and bring child results back for review.
Exact identity, write ownership, stop gates and independent receive-audit are
required; a convenient parent-child topology is not itself a safety contract.

For a single temporary native subagent, use its returned ID, scoped prompt,
observable completion and artifact review; no durable registry or new visible
task is required. Use this full protocol for durable or explicitly visible sessions.

Read [references/protocol.md](references/protocol.md) before setup, dispatch, or
RECEIVE_AUDIT.

## Choose the smallest topology

Default to one visible session named `<repo> | MAIN`.
Delegated work uses native subagents inside the current task. Creating a visible
conversation (for example with `create_thread`) requires an explicit owner
request for that conversation or an explicitly authorized MAIN restart.
Delegation, independent review, retries, context pressure and a continuing goal
do not grant that permission. If native subagents or the requested model are
unavailable, continue in MAIN and report the limitation; never substitute a
visible task. Workers cannot delegate further or create successors unless their
assignment expressly authorizes it.
Reuse an authorized worker for follow-up corrections; do not create a visible
conversation per review round.

Use stable role titles such as `<repo> | QA` or `<repo> | RESEARCH` when the
responsibility persists. Use `<repo> | <TASK_ID>` for a bounded disposable work
unit. Never treat a title as identity and never create a worker merely to make
the topology look multi-agent.

## Capability and identity gate

Discover the current harness capabilities for listing, creating, renaming,
sending, reading, and waiting on visible sessions. Verify each mutation by
readback. If exact session transport is unavailable, remain in MAIN and report
the degraded mode; hidden workers are not equivalent to requested visible
sessions.

Before reuse or dispatch, bind the target in the session registry:

- `THREAD_ID`, `HOST_ID`, harness and current status;
- repository, `CHECKOUT` or worktree, branch/base/HEAD;
- role, task, write scope and isolation;
- active-turn state and last successful readback.

Unknown, ambiguous, stale, or title-only identity is a stop condition. A
submission is not delivery; record `SENT` only with transport readback.

## Bounded turns and runtime release

A goal may span turns, but each turn/session is bounded. Run
`SESSION_HEALTH_GATE` at `START`, `AFTER_COMPACTION`, `MATERIAL_TRANSITION` and
`BEFORE_CLOSEOUT` using host/configured signals such as turn age, history size,
compactions, cost/tokens and owned workers. `UNKNOWN` or `UNSUPPORTED` lowers
runtime proof; optional telemetry does not block safe work. An unmeasurable
explicitly required hard budget blocks work relying on that guarantee.
`WARNING` checkpoints the goal/TODO, stops optional workers and
large new units, and permits only the safe current unit to continue. A hard
limit persists the canonical Markdown goal, writes a compact handoff, verifies
no write is in flight, then selects verified host clear or `END_TURN`, or the
authorized [session-restart protocol](references/session-restart.md). Standing
restart consent covers later rotations in its recorded scope; installation alone
is not consent. Resume by reading that file and
reconciling identity and checkout; stale transcript or native-goal text cannot
override it.
`task_complete` is not `RUNTIME_RELEASE`; require owned-worker readback where
the host supports it.

## Startup care

Ultra invokes [automatic start and observation](references/session-restart.md#automatic-start-and-observation)
on explicit Flow task entry, even without a restart request or detailed ledger.
Name the session immediately from verified creation metadata; assess current
context and full necessary startup inputs. A health restart does not require an
economic saving, but still requires authority, progress and safe takeover.

## Modes

- `session-restart` / `nb-session-restart`: evaluate long-run restart benefit,
  persist a compact checkpoint, create a fresh MAIN through supported native
  transport, verify takeover, then archive the exact retired source if authorized.
  Read [references/session-restart.md](references/session-restart.md); no fixed
  timer, forked full history or per-rotation approval inside standing consent.

- `setup`: reconcile an existing registry, name MAIN, and create only the next
  justified session. Do not pre-create a swarm.
- `delegate`: send one already-selected, self-contained work unit to one exact
  session.
- `RECEIVE_AUDIT`: independently verify one report before any state advance.
- `recover`: resume from canonical state and evidence without repeating the
  same failed attempt.
- `handoff`: create a compact owner-requested continuation snapshot for a fresh
  MAIN session, including live state, exact unfinished work, evidence and the
  first safe action; do not pretend that writing the snapshot created or
  delivered a session.

## Writer and lease contract

MAIN normally owns sequential workflow state. A worker owns only its bounded
implementation scope and report. Never let two writers mutate the same state or
checkout concurrently.

Use the project's authoritative lease mechanism when one exists. A Markdown
`LEASE` is advisory coordination, not atomic locking. `FENCING_EPOCH` is valid
only when an authoritative control plane allocates a monotonically increasing
token and every write boundary rejects stale tokens. Otherwise record
`FENCING_SUPPORTED: NO` and `FENCING_EPOCH: NONE`; do not fabricate safety.

Malformed, active, or uncertain lease state is `LEASE_CONFLICT`. Stop routing.
For parallel writers require isolated checkouts, disjoint write scopes, and a
coordinator-owned integration step.

## Delegate gate

Dispatch only when all are true:

1. one approved work unit has an observable outcome, exclusions, dependencies,
   acceptance, verifier, evidence path, rollback, owner gates and a frozen
   `MODEL_POLICY`;
2. canonical state identifies the same active task and allowed transition;
3. session identity, checkout, clean/dirty scope, lease, and active-turn state
   pass fresh readback;
4. frozen inputs and the cheapest relevant preflight check pass;
5. the report receiver is an exact session, not a title.

Context propagation is not assumed. Send the minimum context: repository
instructions, the owning method and its source hash, frozen task inputs and
acceptance. Never copy the whole parent transcript or unrelated skills. Require
the worker's context readback before work; stale context or evidence, mismatch or transport failure blocks dispatch.

Bind the frozen `MODEL_POLICY` and `MODEL_REQUESTED`, effort, budget and
escalation gate. If the host does not expose one field, record
`UNKNOWN` or `UNSUPPORTED` and keep runtime proof lower;
never silently substitute another model.

Build the prompt from the template in the protocol. The worker performs exactly
one work unit, does not select a successor, releases its lease on finish or hard
stop, sends exactly one final report, and ends its turn. Bind retryable transport
to message and payload identity, an idempotency key, delivery receipt and ACK;
record unsupported fields honestly and never blindly retry an uncertain send.
For every delegation record, including a blocked or stale one, copy the caller's
schema before filling values; do not rename fields or change nesting. Preserve
exact observed values as raw evidence in the requested location and derive the
canonical verdict separately from the protocol enum and readback. When either
is insufficient, use its honest failure state and block retry or advancement.

## RECEIVE_AUDIT

Treat `FINISHED` and `NEXT_ACTION` as untrusted report fields. Independently bind
the report to the expected session, task, `CHECKOUT`, commit, diff, frozen
inputs, manifest, tests, verifier, build/runtime, quality review and side
effects. The lease gate passes only when readback proves `RELEASED`, or proves
`NOT_HELD`/`UNSUPPORTED` for a workflow that explicitly uses one of those
states; `NOT_RELEASED`, unknown ownership or a conflict blocks advancement.

Return exactly one audited result to `nobrainer-dispatcher`, or to
`nobrainer-ultra` when no dispatcher is justified:

- all gates pass: report the verified transition as eligible; do not select or
  dispatch the next task;
- isolated correctable defect: return `CORRECTION_REQUIRED` with the exact defect
  and evidence; do not choose, dispatch or execute the correction. Dispatcher,
  or Ultra when Dispatcher is not justified, selects the task's assigned repair
  method (`nobrainer-build` for implementation). After the repair and any
  required repeated review, run a fresh `RECEIVE_AUDIT` that binds the repaired
  diff, tests and current review result;
- missing or conflicting evidence, failed check, active turn, or lease conflict:
  preserve state and stop;
- owner decision or irreversible action: ask for one explicit decision;
- no remaining task: report closure eligibility; do not manufacture a successor.
  An empty `READY` set may mean wait for `RUNNING`, audit `REPORTED`, or finish
  accepted work. If all unfinished work is blocked, checkpoint and name its
  unblock action; use `OWNER_DECISION_REQUIRED` only for an actual owner decision.

Retries require new evidence or a changed condition. Preserve a stable blocker
fingerprint, attempt number, recovery owner, retry budget, checkpoint, rollback,
and one concrete remediation action.

## Final response

Report topology, exact identities created or reused, canonical state change,
transport readback, audit result, evidence, uncertainty, recovery/rollback, and
one next action. Never claim session creation, rename, dispatch, receipt, or
completion without readback from the responsible system.

## Optional bounded command

For a non-interactive command that needs enforced wall-time/output limits, use
the inspected [bundled runner](scripts/run_bounded.py) when Python 3.11+ and POSIX
are available. Pass explicit argv, finite `--wall-seconds`, `--max-output-bytes`
and a fresh `--receipt`; no shell or automatic retries. It controls only its
child process group, not model context, cost, escaped sessions or other tools.
A receipt is process evidence, never task acceptance; missing proof is not success.
