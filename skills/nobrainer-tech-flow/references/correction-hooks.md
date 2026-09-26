# Correction and learning hooks

These are semantic lifecycle hooks. They work in any agent runtime because the
active agent evaluates the event and performs a scoped update; do not claim that
a client executed a native hook unless its runtime actually reported one.

Project setup records one `LEARNING_WRITE_POLICY`:

- `AUTO_SCOPED`: durable, sourced corrections may update the project-local wiki,
  `tasks/lessons.md` and nearest project instructions within their existing
  classification/write rules;
- `ASK`: prepare the exact learning diff and request one persistence decision;
- `OFF`: correct active state but do not persist learning.

This standing policy never authorizes global instructions, public disclosure,
secrets, commits, pushes or unrelated semantic rewrites.

## Events

### `OWNER_DECISION_CHANGED`

Trigger only when the owner explicitly replaces a requirement, preference,
constraint or decision.

1. Quote or point to the new decision and identify the superseded statement.
2. Update the one canonical owner: spec, decision record, plan or project
   instruction. Mark the old value `SUPERSEDED`; do not preserve two active
   truths.
3. Remove every affected not-started row from the ready set, mark it `STOPPED`,
   and keep its dependants `PENDING` or `BLOCKED`. Invalidate all evidence made
   under the old assumption. Set `REPLAN_REQUIRED` when the critical path,
   acceptance, permissions or architecture changes.
4. If affected work is already `SENT`, `CLAIMED` or `RUNNING`, stop further
   routing and use `nobrainer-sessions` to request and read back a controlled
   stop; never infer that cancellation succeeded.
5. Under `AUTO_SCOPED`, update the relevant project wiki page through
   `nobrainer-wiki` mode `ADD` when the decision is durable, sourced and
   correctly classified. Under `ASK`, prepare the exact diff; under `OFF`, keep
   it task-local. Replace or annotate stale knowledge instead of appending a
   contradiction.
6. Rebuild the affected path under a new plan fingerprint. Only then recompute
   readiness from all gates and resume AUTOPILOT. Ask again only if the new
   decision creates a real owner gate.

### `AGENT_ERROR_CORRECTED`

Trigger when the owner provides a correction or evidence shows that the agent's
previous action, claim, assumption or process was wrong.

1. Correct the current output or state first; an apology is not remediation.
2. Classify the failing scenario, error fingerprint, cause and smallest
   prevention rule as task-local state, a project-specific lesson, a repository
   instruction, durable wiki knowledge or behavior-improvement evidence.
3. Apply the configured policy before any persistent write:
   - under `AUTO_SCOPED`, persist at most one minimal, sourced rule to its one
     canonical project-local governed store; use `tasks/lessons.md` for a
     project-specific failure pattern, the nearest scoped `AGENTS.md` only when
     a reusable instruction was missing or misleading, or the wiki only for
     reusable durable knowledge;
   - under `ASK`, prepare the exact single-store diff and request one decision;
   - under `OFF`, keep the prevention candidate in active task state and do not
     create or modify `tasks/lessons.md`, `AGENTS.md` or a wiki.
   Preserve managed blocks and avoid a biography of past mistakes.
4. Route repeatable skill or prompt behavior to `nobrainer-autoimprove` with the
   failing scenario as development evidence and a separate holdout. A
   deterministic code defect instead receives a regression test through
   `nobrainer-build`.
5. When persistence is allowed by step 3, capture a durable fact or explicit
   reusable preference in the wiki only when its destination and confidentiality
   permit it. Never write a secret, raw sensitive transcript or an inferred
   permanent personality trait.

### `REVIEW_FAILED`

Trigger when `nobrainer-review` returns a verified finding or required evidence
fails.

1. Keep the affected stage incomplete and attach the finding/evidence.
2. Add one bounded correction stage owned by `nobrainer-build`.
3. Run the regression and affected baseline checks, then return to
   `nobrainer-review` with fresh evidence.
4. After the repeated review, run a fresh `RECEIVE_AUDIT` that binds the repaired
   diff, current tests and review result before acceptance.
5. Do not reuse the invalidated review, test or release result.

### `REPEATED_DEFECT`

Trigger when the same normalized failure reappears after a claimed fix.

Stop blind retry. Compare fingerprints and prior prevention evidence, invoke
`nobrainer-rca`, and require new evidence before another implementation attempt.
Use `nobrainer-autoimprove` only when the defect belongs to a skill, prompt or
workflow control rather than product code.

## Persistence gate

Every write must have one canonical owner, a source, scope, confidentiality,
verification and rollback. Keep these concerns separate:

- active requirement or decision -> spec/decision record;
- live work and invalidation -> canonical plan/state;
- repository behavior rule -> nearest `AGENTS.md`;
- project-specific failure pattern -> `tasks/lessons.md`;
- reusable sourced knowledge -> `nobrainer-wiki`;
- measurable agent-behavior gap -> `nobrainer-autoimprove`.

Do not write the same mutable statement into all stores. Link to its canonical
owner and store only the local consequence needed by each consumer.
