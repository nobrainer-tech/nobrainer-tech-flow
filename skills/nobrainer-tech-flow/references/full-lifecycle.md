# Full lifecycle

Read this when the work crosses sessions, delegates, changes a public contract,
routing or workflow, or the user asks for the full contract. Ordinary
single-session work uses the entry skill alone.

For resumable or delegated work use `SESSION_HEALTH_GATE` and `RUNTIME_RELEASE`
from the [long-run reference](long-run-state.md). Finish when accepted; audit
active workers. At first project use, follow [project start](project-start.md)
for the existing tree/layers, goal direction and wiki boundary. For ideas, read
[idea to delivery](idea-to-delivery.md).

## Scope the minimum sufficient change

Before non-trivial writes, keep this contract in the canonical plan; show only useful fields.

```text
Outcome:
Non-goals:
Expected files (PUBLIC_SURFACE):
Proof:
Risks:
Untouched:
Minimum solution:
Test decision: EXISTING | NEW_REQUIRED | NOT_NEEDED — reason
Done clean:
```

`Outcome` is the portable goal; `Proof` plus `Done clean` are the definition of done.
`Risks` name what could invalidate the plan.
For substantial work, derive the next short-term goal from the supplied
long-term direction using [project start](project-start.md).
Update scope before expanding; require matching files, passing proof and no surprises.
`PUBLIC_SURFACE`: for public contract, routing or workflow changes, map
affected README/docs/templates/assets/flow, or record `NOT_NEEDED`, and update existing
affected diagrams; fresh SVG + README Mermaid readback applies when the project
maintains those formats. Do not create diagrams merely to satisfy a workflow gate.
`VERIFY` fails closeout when an affected public surface lacks its update or readback.
On request, show every field above and the detailed-ledger decision.

## Detailed ledger

Update the checklist after scope is frozen, at transitions, blockers, new evidence
and closeout. The checklist views the canonical TODO; accept evidence, not worker reports.
For ordinary single-session work the entry skill's checklist is enough.
Use a detailed ledger only when any condition holds:

- work crosses sessions or must resume safely after context loss;
- the user keeps adding requests mid-run in one long conversation;
- dependencies, multiple writers or a delegated queue control readiness;
- a consequential external effect requires auditable gates and recovery;
- the user explicitly requests a durable execution record.

Otherwise a multi-component task that fits one coherent session does not pass this gate.
When it passes, use [long-run state](long-run-state.md) and keep the
user-facing Progress checklist concise.
For work that passes the detailed-ledger gate, persist the goal in an existing
Markdown tracker or a task-local Markdown `GOAL_FILE`. That file is canonical across clears,
compactions and sessions. Require goal readback only from stores actually
used; the file alone is sufficient and supersedes stale transcript text.
Default to at most 160 words: outcome, scope, Progress, proof and next action.
Mark uninspected paths/methods as pending.

## Readiness

Proceed when required inputs, authority and proof are available; unknown write ownership,
stale input or ambiguous irreversible effects block the affected action.
Read [delivery](delivery.md) before BLOCKED: derive outcome/DoD, resolve
authorized steps and continue independent work. `yolo` is a persistence alias only.

## Receive audit and corrections

Audit native-worker output against its exact returned ID, assigned scope, current
artifact and tests; verify it has stopped writing. Durable sessions use
`nobrainer-sessions` `RECEIVE_AUDIT`. If Dispatcher owns a queue, reconcile the
audited result before releasing dependencies.

- `OWNER_DECISION_CHANGED`: supersede the old decision at once, move affected
  not-started `READY` rows to `STOPPED`, block dependants and invalidate
  only their evidence before re-planning.
- `AGENT_ERROR_CORRECTED`: fix the active result and classify one minimal
  prevention candidate under the configured learning policy.
- `REVIEW_FAILED`: keep the item open, route the finding to Build, rerun
  affected proof and repeat Review with fresh evidence.
- `CANDIDATE_REJECTED`: preserve the champion and close that experiment. Continue only
  if user acceptance is still unmet and a bounded next attempt is justified.
- `REPEATED_DEFECT`: stop blind retries and route the frozen failure to RCA.

Detailed canonical-store rules live in [correction hooks](correction-hooks.md).
