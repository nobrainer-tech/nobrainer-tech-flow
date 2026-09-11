---
name: nobrainer-dispatcher
description: "Use when the owner says nb-dispatcher or nobrainer-dispatcher, or when an approved plan has multiple queued work units that require ready-set selection, dependency-aware ordering, bounded parallel batches, retry scheduling, or routing audited results to the next queued unit; do not use for one coherent task, one bounded delegate, a standalone receive-audit, requirements, team design, or session transport."
---

# NoBrainer Dispatcher

Turn an approved detailed plan into a controlled sequence of work batches. Own
readiness, ordering, backpressure and scheduler state; never own requirements,
implementation, session identity or final acceptance evidence.

Keep the boundaries explicit:

- `nobrainer-ultra` owns intent, the canonical plan and lifecycle;
- `nobrainer-team` owns the minimum roles and capability sources;
- Dispatcher owns which already-defined work unit may run now;
- `nobrainer-sessions` owns exact session identity, transport, lease and
  receive-audit;
- the assigned method owns the work product;
- `nobrainer-review` owns the independent close gate when required.

A single coherent work unit stays in MAIN and marks Dispatcher `NOT_NEEDED`.
Use parallel batches for independent ready work under the
[team execution contract](../nobrainer-ultra/references/delivery.md#coordinated-team-execution):
fill available useful slots, capped at 15 live subagents across the task tree.
When the owner explicitly invokes Dispatcher only to inspect such a map,
Dispatcher owns that scheduler inspection and returns `NOT_NEEDED`; MAIN remains
the owner of the work unit and its product. Keep control ownership distinct from
work ownership in every report.

## Preconditions

Dispatch only from a visible canonical ledger whose executable rows
contain:

```text
TASK_ID | OUTCOME | METHOD | MODEL_POLICY | OWNER_OR_ROLE | DEPENDENCIES | WRITE_SCOPE |
ACCEPTANCE_AND_EVIDENCE | PARALLEL_GROUP | OWNER_GATE | STATUS
```

Also require the frozen plan/spec ref, current checkout and state fingerprint,
retry and attention budgets, stop conditions, integration owner and rollback.
If requirements, task boundaries, dependencies, acceptance or authority remain
undefined, return to `nobrainer-ultra`; Dispatcher must not repair a vague plan
by improvising worker prompts.

Before assigning any worker, require a completed `nobrainer-team` capability
and role stage. Use one canonical cross-skill transition:

`Team -> Dispatcher SCHEDULE -> Sessions setup/delegate -> Dispatcher DISPATCH`

Sessions alone owns identity preflight and prompt transport. Dispatcher selects
the batch before that call and records `READY -> SENT` only from Sessions'
successful transport readback. A role name or conversation title is not a
transport address.

Ultra freezes `MODEL_POLICY`; Dispatcher carries it with the work unit
and never chooses a provider model. Sessions binds the requested model, effort,
budget and escalation gate when the host exposes them, or records
`UNKNOWN`/`UNSUPPORTED` without a silent substitution.

## Modes

- `SCHEDULE`: validate the dependency graph and propose one safe ready batch.
- `DISPATCH`: consume Sessions' fresh identity, checkout, lease, active-turn and
  transport readback for the selected batch, then commit one `READY -> SENT`
  transition per delivered work unit. Sessions alone performs the send.
- `RECONCILE`: consume independently audited reports, update scheduler state and
  choose one next batch, correction, stop or close action.
- `RECOVER`: resume from the ledger and current evidence without repeating a
  blocker or trusting conversation memory.

Use one mode per state transition. Do not combine plan invention, dispatch and
acceptance into an opaque `continue until done` loop.

## Own one dispatch ledger

Keep scheduler state separate from the specification, canonical plan, session
registry, reports and wiki. MAIN or one named coordinator is the only writer.
Persist the ledger only when work spans sessions, can be interrupted or needs
auditable retries; otherwise keep it in the current plan.

```text
DISPATCH_RUN_ID:
PLAN_REF_AND_FINGERPRINT:
STATE_OWNER:
INTEGRATION_OWNER:
ATTENTION_BUDGET: max_active | urgent_events | digest_cadence |
  expected_wait | context_switch_limit
TASKS:
  TASK_ID | STATE | DEPENDENCIES | METHOD | MODEL_POLICY | SESSION_ID | WRITE_SCOPE |
  ATTEMPT_NO | BLOCKER_FINGERPRINT | REPORT_REF | EVIDENCE_REF
```

Allowed states are `PENDING`, `BLOCKED`, `READY`, `SENT`, `CLAIMED`, `RUNNING`,
`REPORTED`, `AUDITED`, `ACCEPTED`, `CORRECTION_REQUIRED` and `STOPPED`.
`SENT` proves transport readback only; it does not prove execution or lease
ownership. Advance one edge only after its evidence gate. A worker report cannot
write this ledger.

## Compute the ready set

For each `PENDING` task and, only in `RECOVER`, one eligible `BLOCKED` task:

1. Verify every predecessor is `ACCEPTED`, not merely `FINISHED` or reported.
2. Verify frozen inputs, plan fingerprint, owner gates and required capability.
3. Verify its method, outcome, write scope, acceptance and rollback are complete.
4. In `SCHEDULE`, exclude a task only when known assignment, checkout, lease or
   active-turn evidence proves a conflict; transport identity may still be
   unknown before Sessions preflight.
5. Exclude tasks sharing a writer, mutable state, checkout, migration boundary or
   integration surface with another candidate.
6. Exclude a repeated blocker unless new evidence or a changed condition exists.

`RECOVER` may re-evaluate a `BLOCKED` task only when the plan fingerprint and
task contract are still current, the attempt budget remains, and a cited new
fact changes the blocker condition. Run every gate above again. If all pass,
record `BLOCKED -> READY` and add the task to the ready set. Otherwise keep it
`BLOCKED` with its prior fingerprint and evidence. Never strand recoverable work
outside the ready-set algorithm or bypass the scheduler by sending it directly.

Unknown dependency state is `BLOCKED`, not ready. Detect cycles and stop with the
smallest cycle path; do not break a cycle by guessing an order.

## Select one bounded batch

From the ready set, prefer work that shortens the measured critical path or
unblocks the most dependent acceptance work. Use the smallest batch that earns
its coordination cost. Bound it by:

- the declared `max_active` and actual session capacity;
- disjoint write scopes and isolated checkouts for concurrent writers;
- API, model, test-environment and human attention limits;
- one integration owner and an explicit integration task after parallel work;
- the context-switch limit and expected wait.

Do not dispatch speculative future tasks merely because a worker is idle. Keep
sequential dependencies sequential. If elapsed-time benefit is unmeasurable or
integration dominates, run the work in MAIN.

Record why every selected task is safe in parallel and why every deferred ready
task waits. A `PARALLEL_GROUP` label alone is not proof.

## Complete dispatch through Sessions

For each selected work unit, Dispatcher emits the task contract below without
sending it. Ultra or MAIN then invokes `nobrainer-sessions` mode `delegate`
exactly once. Before Dispatcher records `READY -> SENT`, consume fresh session,
checkout, lease, active-turn and transport readback from Sessions; unknown
transport state keeps the task `READY` and stops dispatch. Bind:

- exact `TASK_ID`, session and host IDs, checkout, branch/base/HEAD and lease;
- one observable outcome, exclusions, allowed write scope and frozen inputs;
- frozen `MODEL_POLICY`, exact model/effort/budget and escalation gate;
- method/skill, dependencies, acceptance, tests, evidence and rollback;
- report receiver, retry budget, blocker behavior and explicit stop;
- the rule that the worker cannot choose, dispatch or start a successor.

Sessions sends at most one active work unit to one exact worker. Dispatcher
records `SENT` only after that transport readback; it never invokes a second
transport pass. If transport is unavailable before sending, MAIN may execute
only after recording `READY -> CLAIMED -> RUNNING` with MAIN ownership in the
canonical tracker. Remove the unit from the dispatchable set first. Multiple
coordinators require the existing authoritative conditional claim; without it,
stop dispatch rather than invent atomic ownership. Never fabricate a session
or delivered prompt. MAIN fallback applies only to proven pre-send
unavailability. If a send may have succeeded without a receipt, preserve the
UNKNOWN delivery observation, reserve capacity and write scope, and reconcile
before resending or taking over; READY does not authorize a second writer.

After dispatch, Sessions waits or monitors at the declared cadence. Batch routine
progress. Interrupt the owner only for safety, credentials, irreversible effects,
changed frozen input, exhausted retry, lease conflict or a genuine decision.

## Reconcile audited results

Never accept a raw worker report directly. Invoke `nobrainer-sessions`
`RECEIVE_AUDIT` to bind identity, checkout, diff, tests, verifier, runtime,
side effects and released lease. Then choose exactly one transition:

- audited success: mark the task `ACCEPTED`, release its dependants and compute
  one next ready batch;
- isolated correctable defect: mark `CORRECTION_REQUIRED`, route one bounded
  fix through the task's assigned method (`nobrainer-build` for implementation)
  and invalidate affected proof. After the repair, rerun affected tests and any
  required failed review, then run a fresh `RECEIVE_AUDIT` that binds the
  repaired diff, tests and review before marking the task `ACCEPTED`;
- observed unexplained failure or repeated fingerprint: invoke `nobrainer-rca`
  and stop blind retries;
- changed plan/input: move affected not-started `READY` rows to `STOPPED`, keep
  dependants `PENDING` or `BLOCKED`, invalidate the old plan/evidence and return
  to Ultra for a new fingerprint. If work is already sent or running, stop new
  routing and let Sessions request and verify a controlled stop;
- write collision, active lease or missing evidence: preserve state and stop
  without releasing successors;
- owner gate: request one exact decision;
- no remaining non-accepted task: return control to Ultra for final review,
  delivery and learning.

`NEXT_ACTION` from a worker is a recommendation, never scheduler authority. A
failed review invalidates affected evidence and routes back to implementation;
it cannot be relabelled as accepted. Tests, repeated review and receive-audit
are distinct gates; none substitutes for another.

## Recovery and closeout

Resume from the canonical plan, ledger, session registry and evidence refs. For
each retry record `ATTEMPT_NO`, stable `BLOCKER_FINGERPRINT`, prior evidence and
the new fact that justifies another attempt. Do not retry the same condition
after budget exhaustion.

Finish with:

```text
MODE: SCHEDULE | DISPATCH | RECONCILE | RECOVER
PLAN_REF_AND_FINGERPRINT:
READY_SET:
CRITICAL_PATH: <measured chain or UNKNOWN with reason>
UNBLOCKS: <selected task -> dependent acceptance work, or NONE>
DISPATCHED_BATCH: <task -> exact session, or NONE>
DEFERRED_READY_TASKS_AND_REASON:
PARALLEL_SAFETY: <task pair -> disjoint scope, checkout and mutable-state proof,
  or NOT_NEEDED>
STATE_TRANSITIONS:
AUDIT_REFS:
MODEL_POLICY_READBACK:
ATTENTION_AND_RETRY_BUDGET:
BLOCKERS_OR_OWNER_GATES:
INTEGRATION_OWNER: <exact owner or NOT_NEEDED>
NEXT_PROOF: <one acceptance or transport evidence target>
NEXT_ACTION: <one batch, correction, stop or return to Ultra>
ROLLBACK_OR_RECOVERY:
RESULT: NOT_NEEDED | DISPATCHED | ADVANCED | DEGRADED_MAIN | STOPPED | CLOSED
```

Do not claim speedup from worker count. Report elapsed critical-path evidence
when available and close the dispatcher when the canonical plan is accepted.
