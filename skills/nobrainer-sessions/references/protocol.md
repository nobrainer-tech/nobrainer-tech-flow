# NoBrainer Sessions protocol

Adapt names and paths to the project. Reuse an existing source of truth instead
of creating duplicate status files. Unknown values block dispatch; never ship
placeholders in a live prompt.

## Durable boundaries

Keep four concepts distinct even if a small project stores them in fewer files:

| Concept | Contains | State writer |
|---|---|---|
| master plan | outcomes, task graph, dependencies, acceptance, gates | owner or MAIN |
| execution state | current task, registry, attempt, lease, evidence pointers | MAIN |
| workflow protocol | stable roles, transitions, prompt/report formats | owner or MAIN |
| reports and evidence | task-bound reports, manifests, logs, test output | worker writes task evidence; MAIN indexes it |

Do not put current IDs, hashes, leases, or blocker history into the stable
protocol. Do not copy execution status into a wiki.

Use native subagents for bounded delegated work inside the current task. A
separate visible conversation is human-facing task state and requires an
explicit owner request or an explicitly authorized MAIN restart. Delegation,
review retries, context pressure and goal continuation do not authorize
`create_thread`; if native subagents are unavailable, continue in MAIN and
report the limitation. Workers never create successor conversations or
delegate further without express assignment authority.

## Session registry row

```text
TITLE: <repo> | <MAIN|ROLE|TASK_ID>
TITLE_BASE: <stable human task title without a started suffix>
STARTED_AT: <full timestamp and timezone or UNKNOWN>
DISPLAY_TITLE: <TITLE_BASE> | started DD-MM
TITLE_STATUS: VERIFIED | UNAVAILABLE | UNSUPPORTED | UNKNOWN
HARNESS: <client and version>
MODEL_POLICY: <STANDARD | EXTENDED | ROUTED and policy fingerprint>
THREAD_ID: <exact ID>
HOST_ID: <exact host ID or verified NONE>
STATUS: IDLE | ACTIVE | BLOCKED | CLOSED | UNKNOWN
REPOSITORY: <canonical repository identifier>
CHECKOUT: <absolute checkout/worktree path or harness-native identifier>
BRANCH: <branch or NONE>
BASE_COMMIT: <commit or NONE>
HEAD_COMMIT: <commit or NONE>
ROLE: MAIN | <bounded role>
TASK_ID: <task or NONE>
WRITE_SCOPE: <exact files/systems or READ_ONLY>
ISOLATION: SHARED_READ_ONLY | ISOLATED_WORKTREE | OTHER_VERIFIED
LEASE: FREE | HELD | RELEASED | CONFLICT | UNSUPPORTED
FENCING_SUPPORTED: YES | NO
FENCING_EPOCH: <monotonic token or NONE>
SESSION_HEALTH_GATE: PENDING | HEALTHY | WARNING | ROTATE_REQUIRED | UNKNOWN | UNSUPPORTED
CLEAR_MODE: HOST_CLEAR | END_TURN | MANUAL_REQUIRED | UNSUPPORTED
RUNTIME_RELEASE: PENDING | VERIFIED | NOT_RELEASED | UNKNOWN | UNSUPPORTED
GOAL_FILE: <canonical Markdown path/reference or NONE>
LAST_READBACK: <UTC timestamp and evidence pointer>
```

## Bounded-turn and release gate

An outcome/goal may cross turns, but no turn/session is an unlimited lease. At
`START`, `AFTER_COMPACTION`, `MATERIAL_TRANSITION` and `BEFORE_CLOSEOUT`, record:

```text
SESSION_HEALTH_GATE:
- EVENT: START | AFTER_COMPACTION | MATERIAL_TRANSITION | BEFORE_CLOSEOUT
- POLICY: <host/configured limits or NONE>
- SIGNALS: <turn age, history size, compactions, cost/tokens, owned workers>
- RESULT: HEALTHY | WARNING | ROTATE_REQUIRED | UNKNOWN | UNSUPPORTED
- ACTION: CONTINUE | CHECKPOINT_AND_RESTRICT_DISPATCH | CHECKPOINT_AND_END_TURN | OWNER_DECISION_REQUIRED
- CLEAR_MODE: HOST_CLEAR | END_TURN | MANUAL_REQUIRED | UNSUPPORTED
- ROTATION: STANDING_POLICY_AUTHORIZED | OWNER_APPROVAL_REQUIRED

RUNTIME_RELEASE:
- RESULT: VERIFIED | NOT_RELEASED | UNKNOWN | UNSUPPORTED
- OWNED_WORKER_READBACK: <host readback or NONE>
```

Signals are host-native or adapter-provided and must be read back; the
portable contract assumes no particular operating system, process mechanism or
transcript format. `UNKNOWN` means an expected signal was not readable;
`UNSUPPORTED` means the host cannot provide it. Neither result is
`HEALTHY`, and both lower runtime proof. `ROTATE_REQUIRED` means persist the
canonical Markdown goal, write a compact handoff and verify no writer remains.
`WARNING` means checkpoint goal/TODO, stop optional workers and large new units,
and continue only the safe current unit.
Use `HOST_CLEAR` only with capability and completion readback; otherwise use
`END_TURN`, `MANUAL_REQUIRED` or `UNSUPPORTED`. Resume reads the goal file from
disk and reconciles goal identity, checkout and evidence before work. Never
create a successor without current or standing authorization. MAIN may use
[session-restart](session-restart.md) for an authorized, verified fresh-session
transfer; workers never create successors. `task_complete` is not `RUNTIME_RELEASE`: `VERIFIED`
requires readback that task-owned workers are closed where that capability
exists. If no legal `READY` row remains, wait for `RUNNING`, audit `REPORTED`,
or finish accepted work. Only blocked unfinished work needs an unblock action;
`OWNER_DECISION_REQUIRED` requires an actual owner decision.

At explicit Flow task startup and authorized fresh-session transfer, keep
`TITLE_BASE` stable and give each
session the suffix ` | started DD-MM` from its own verified start timestamp. Use
the task/owner timezone, or recorded UTC when none is known. Remove an existing
suffix before formatting. Read back supported create/rename operations, but never
use a title to establish identity or block an otherwise safe transfer when the
host reports title mutation as unsupported. See [session restart](session-restart.md).

## Delegating prompt

```text
ROLE:
You are the worker for TASK_ID=<ID>. You own only <bounded scope>. You are not
MAIN. Do not select, send, or start a successor.

OUTCOME:
Produce <one observable result>. Success means <independent acceptance>.

EXCLUDED_SCOPE:
- Do not change <files, systems, decisions, production, credentials, publishing,
  destructive operations, or safety controls outside scope>.
- Do not expand scope without an owner or MAIN decision.

IDENTITY:
- REPOSITORY: <identifier>
- CHECKOUT: <exact checkout/worktree>
- THREAD_ID: <worker ID>
- HOST_ID: <worker host or verified NONE>
- TASK_ID: <ID>
- METHOD: <literal owning skill or project capability>
- MODEL_POLICY: <exact frozen policy>
- MODEL_REQUESTED: <exact host/provider model, HOST_SELECTED or UNKNOWN>
- WRITE_SCOPE: <scope>

CANONICAL_INPUTS:
- PLAN: <path or canonical tracker reference>
- EXECUTION_STATE: <path or canonical state reference>
- REPORT_PATH: <task-bound path>
- FROZEN_INPUTS: <hashes/versions or NONE>
- VERIFIER: <command or NONE>

CONTEXT_RECEIPT:
- CONTEXT_SOURCE_REF: <repository instructions plus owning method refs>
- CONTEXT_SHA256: <hash of the exact minimum context packet>
- CONTEXT_READBACK: PENDING

TRANSPORT:
- MESSAGE_ID: <provider receipt ID or UNSUPPORTED>
- PAYLOAD_SHA256: <hash of the exact sent payload>
- IDEMPOTENCY_KEY: <stable retry key or UNSUPPORTED>
- DELIVERY_RECEIPT: <provider readback or UNSUPPORTED>
- ACK_STATUS: PENDING | ACKNOWLEDGED | UNSUPPORTED

EXPECTED_STATE:
- ACTIVE_TASK: <ID>
- PREDECESSOR: <state>
- ALLOWED_SUCCESSOR: <state after MAIN audit>
- LEASE: <owner, status, acquisition evidence>
- FENCING_EPOCH: <token or NONE>

START_GATE:
1. Read repository instructions, the owning method and canonical inputs. Return
   `CONTEXT_READBACK` bound to `CONTEXT_SOURCE_REF` and `CONTEXT_SHA256` before work.
2. Verify identity, CHECKOUT, task, scope, current HEAD and expected state.
3. Run `SESSION_HEALTH_GATE` for `START`; record policy, signal values or
   `UNKNOWN`/`UNSUPPORTED` and the resulting proof level.
4. Verify frozen inputs, writer isolation and relevant preflight check. Stale context or evidence,
   a mismatch or unread required source stops the task without writing.
5. Immediately before the first write, acquire LEASE according to the project
   rule and record its owner, time and evidence. If it is held, conflicting,
   unsupported where required, or changed after preflight, stop without writing.
6. Record a start manifest after the lease check and before the first write.
7. Stop on any mismatch; do not repair canonical state yourself.

WORK_UNIT:
- <one bounded action>
- METHOD: <literal owning skill or project capability>
- MODEL_POLICY: <exact frozen policy>
- MODEL_REQUESTED: <exact host/provider model, HOST_SELECTED or UNKNOWN>
- ACCEPTANCE: <measurable condition>
- REQUIRED_EVIDENCE: <diff, tests, verifier, build/runtime, review>

CLOSE_GATE:
1. Record changed paths and final commit/state.
2. Run required tests/verifier/build/runtime and preserve raw output.
3. Review scope, quality, secrets, side effects and rollback.
4. Run `SESSION_HEALTH_GATE` for `BEFORE_CLOSEOUT`; `WARNING` checkpoints and
   restricts dispatch. `ROTATE_REQUIRED` requires a durable goal checkpoint,
   compact handoff and verified clear or `END_TURN`. This worker does not rotate
   MAIN; an authorized MAIN uses the separate session-restart protocol.
5. Read back `RUNTIME_RELEASE` separately from task completion; do not claim a
   clean runtime with `NOT_RELEASED`, `UNKNOWN` or unsupported worker evidence.
6. Write close-gate evidence and release LEASE if held.
7. Send exactly one final report to MAIN and end the turn.

ON_FAILURE:
Stop this task. Preserve evidence and checkpoint. Do not start a successor.
Release LEASE when safe. Recommend one bounded remediation.

HANDOFF:
- COORDINATOR_THREAD_ID: <exact MAIN ID>
- COORDINATOR_HOST_ID: <exact host or verified NONE>
- If transport has no receipt, set HANDOFF_STATUS: NOT_SENT. An uncertain send
  blocks automatic retry; never infer delivery from submission.

FINAL_REPORT:
RESULT: FINISHED | BLOCKED | FAILED | OWNER_DECISION_REQUIRED |
  INPUT_CHANGED | LEASE_CONFLICT
HANDOFF_STATUS: SENT | NOT_SENT
HANDOFF_MESSAGE_ID: <receipt ID or NONE>
MESSAGE_ID: <provider receipt ID or UNSUPPORTED>
PAYLOAD_SHA256: <hash of exact sent payload>
IDEMPOTENCY_KEY: <stable retry key or UNSUPPORTED>
DELIVERY_RECEIPT: <provider readback or UNSUPPORTED>
ACK_STATUS: ACKNOWLEDGED | UNSUPPORTED | NOT_ACKNOWLEDGED
CONTEXT_SOURCE_REF: <exact refs>
CONTEXT_SHA256: <hash>
CONTEXT_READBACK: <worker-confirmed refs and hash>
THREAD_ID: <worker ID>
HOST_ID: <worker host or verified NONE>
REPOSITORY: <identifier>
CHECKOUT: <checkout/worktree>
TASK_ID: <ID>
METHOD: <literal owning skill or project capability>
MODEL_POLICY: <exact frozen policy>
MODEL_REQUESTED: <exact requested model or UNKNOWN>
MODEL_ACTUAL: <exact readback or UNKNOWN>
MODEL_READBACK: VERIFIED | UNSUPPORTED | UNKNOWN
BASE_COMMIT: <commit or NONE>
HEAD_COMMIT: <commit or NONE>
WRITE_SCOPE: <scope>
CHANGES: <paths or NONE>
TESTS: <commands, result, raw evidence pointer>
VERIFIER: <command, result, evidence pointer>
BUILD_RUNTIME: <result or NOT_RUN with reason>
SESSION_HEALTH_GATE: <events, policy, result and evidence pointer>
CLEAR_MODE: HOST_CLEAR | END_TURN | MANUAL_REQUIRED | UNSUPPORTED
GOAL_FILE: <canonical Markdown path/reference or NONE>
RUNTIME_RELEASE: VERIFIED | NOT_RELEASED | UNKNOWN | UNSUPPORTED
OWNED_WORKER_READBACK: <evidence pointer or NONE>
QUALITY_REVIEW: <result/evidence or NOT_APPLICABLE>
START_MANIFEST: <path/reference>
CLOSE_EVIDENCE: <path/reference>
BLOCKER_FINGERPRINT: <stable value or NONE>
ATTEMPT_NO: <integer>
NEXT_ACTION: <one recommendation>
ROLLBACK: <exact procedure>
LEASE: RELEASED | NOT_HELD | UNSUPPORTED | NOT_RELEASED_WITH_REASON
FENCING_EPOCH: <token or NONE>
```

## RECEIVE_AUDIT checklist

MAIN verifies from independent readback:

1. expected session and completed turn;
2. registry identity, CHECKOUT, base and HEAD;
3. task, allowed transition, write scope and changed paths;
4. frozen inputs, exact context source/hash/readback, start manifest and close evidence;
5. reproducible test, verifier, build/runtime and quality evidence;
6. `SESSION_HEALTH_GATE` is recorded for required events; `UNKNOWN` or
   `UNSUPPORTED` lowers health proof but missing optional telemetry does not
   block safe work. Missing enforcement of an explicitly required hard budget
   blocks the dependent action. `WARNING` restricts dispatch, and a
   `ROTATE_REQUIRED` checkpoint ends the turn;
7. `RUNTIME_RELEASE` is independently read back; `NOT_RELEASED` or active
   owned workers blocks a clean-release claim;
8. no hidden writer, task, side effect, secret, or scope expansion;
9. lease passes: `RELEASED`, or independently verified `NOT_HELD` or
   `UNSUPPORTED`; `NOT_RELEASED_WITH_REASON` always blocks advancement; when
   fencing is supported, the fencing token must also be valid;
10. message and payload identity, idempotency key, delivery receipt and ACK, or
   honest `UNSUPPORTED`/`NOT_SENT`; uncertain delivery blocks retry and advance.

Only MAIN updates canonical execution state. A worker's `NEXT_ACTION` is a
recommendation, not a command.

## Retry and recovery record

```text
ATTEMPT_NO: <integer>
LAST_BLOCKER_FINGERPRINT: <stable fingerprint>
LAST_BLOCKER_EVIDENCE: <path/reference>
SESSION_HEALTH_GATE: <last event/result/evidence pointer>
RUNTIME_RELEASE: <result/evidence pointer>
NEW_EVIDENCE_REQUIRED: YES | NO
RECOVERY_OWNER: <owner/session>
RETRY_BUDGET: <integer>
CHECKPOINT: <path/reference or NONE>
ROLLBACK: <procedure>
ROLLBACK_READBACK: <evidence pointer>
USER_REMEDIATION: <one action or NONE>
```

Do not repeat an unchanged failure after the retry budget or without new
evidence. A timeout, partial output, dead session, or exhausted retry is not
success.
