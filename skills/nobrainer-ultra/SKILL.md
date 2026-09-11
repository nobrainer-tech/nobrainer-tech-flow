---
name: nobrainer-ultra
description: "Use when the owner says nb-ultra, nb-flow or nb-workflow; complete coding or non-coding tasks with brief clarification, concise progress, bounded execution and verification, or set up or repair that workflow."
---

# `nobrainer-tech-flow`

Skill: `nobrainer-ultra`; aliases are not product names.
Stages use skill names; never announce entry.

For non-trivial work read [routing](references/routing.md). Preserve host model/effort;
consult [model routing](references/model-routing.md) when selecting them.
Setup/upgrade/repair uses [setup](references/setup.md); corrections use
[correction hooks](references/correction-hooks.md); gated resumability uses
[long-run state](references/long-run-state.md).

## Automatic session care

On explicit Flow task entry, run Sessions [startup and health](../nobrainer-sessions/references/session-restart.md#automatic-start-and-observation):
name from verified creation time; assess context at START, AFTER_COMPACTION and
accepted milestones. No separate restart command.
Respect recorded authority, `off` and host restrictions; installation grants no consent.

## Choose the smallest workflow

### Quick path for small changes

For a clear low-risk answer, rewrite, calculation or one coherent, reversible edit,
deliver and check the result directly. Chat-only work needs no repository or tools.
For file edits inspect instructions, actual files and the nearest deterministic check;
use checkout, dirty-state and `git diff --check` only in a Git repository.
Skip requirements, ledger, delegation and review; retain explicit Flow startup care.
Escalate to the full Ultra lifecycle for ambiguity, architecture, public behavior,
workflow/routing changes or consequential side effects; quick path never bypasses
 an owner gate.

Delegate via native subagents; otherwise use MAIN. Visible conversations require explicit owner request. See [routing](references/routing.md).

Lifecycle: `DRIFT_CHECK -> BUDDY -> SCOPE -> AUTOPILOT -> VERIFY -> RECEIVE_AUDIT -> LEARN`.

For resumable or delegated work use `SESSION_HEALTH_GATE` and `RUNTIME_RELEASE`
from the long-run reference.
Finish when accepted; audit active workers. Use `OWNER_DECISION_REQUIRED` only
when unfinished work needs an owner decision.

## `DRIFT_CHECK`: establish current truth

Inspect the actual inputs, instructions and required capabilities; for project work include dirty state, callers, tests and existing plan/spec. Preserve unrelated work. Prior summaries, wiki and worker reports are context, not proof; query wiki only for a decision or lesson that can change this task.
Research current, external, niche, uncertain, high-stakes or attributed facts. For large documents or data and repositories, inspect structure first, then read selected contracts in full and relevant ranges; respect context budget and name unread required surface.

`PROBLEM_GATE`: start with the literal failure and local evidence; do not infer that a documented command produced the failure. If the invocation is unknown, name reproduction from the repository root first; simulation-only request forbids execution, not naming that next diagnostic action. Only then propose path, dependency or configuration changes. Check related wiki decisions. Use current primary-source research only when the remedy depends on external, niche, uncertain or high-stakes facts; inaccessible research means stop at `RESEARCH_BLOCKED`.

## `BUDDY`: clarify once

Use one focused requirements round only when evidence cannot resolve scope,
architecture, safety or acceptance. Code, schema, tests or conventions settle it;
do not make them owner questions. Ask only questions whose answers change the result;
if scope is already clear, proceed immediately. Establish:

- observable outcome, audience and quality bar;
- target-workflow proof;
- exclusions and consequential side effects;
- owner-gated actions;
- unresolved choices that materially affect the design.

Use `nobrainer-decide` for consequential choices among real alternatives.
Use `nobrainer-spec-driven-development` only when a maintained contract pays for architecture,
public behavior, migration, rollback, dependent phases or resumability.

## Scope the minimum sufficient change

Before non-trivial writes, keep this contract in the canonical plan; show only useful fields.

```text
Outcome:
Non-goals:
Expected files (PUBLIC_SURFACE):
Proof:
Untouched:
Minimum solution:
Test decision: EXISTING | NEW_REQUIRED | NOT_NEEDED — reason
Done clean:
```

`Outcome` is the portable goal; `Proof` plus `Done clean` are the definition of done.
Update scope before expanding; require matching files, passing proof and no surprises.
`PUBLIC_SURFACE`: map affected README/docs/templates/assets/flow, or record `NOT_NEEDED`.
For public contract, routing or workflow changes, update existing affected diagrams;
fresh SVG + README Mermaid readback applies when the project maintains those formats.
Do not create diagrams merely to satisfy a workflow gate.
When the owner requests goal/DoD, show every field above and state the detailed-ledger decision.
For work that passes the detailed-ledger gate, persist the goal in an existing
Markdown tracker or task-local Markdown `GOAL_FILE`; it is canonical across clears,
compactions and sessions. A host-native goal is optional: use it only when available
and authorized under that tool's rules. Require goal readback only from stores actually
used; the file alone is sufficient and supersedes stale transcript text.
Default to at most 160 words: outcome, scope, Progress, proof and next action.
Do not add a repetitive skill/mode preamble or invent unseen schemas.
Mark uninspected paths/methods as pending.

New dependencies, abstractions, workers, skills and tests need an acceptance reason.
Shared abstractions require two callers or explicit contract.

Use a short plan ordered by outcomes. One canonical TODO owner may be the host
plan, repository tracker or current response.

## Show human progress

For ordinary single-session work, show a compact update:

```text
Progress
- [x] Scope and acceptance are clear
- [>] Inspecting the current caller and tests
- [ ] Implement and verify
Next: open the named caller and its existing test
```

Update after scope is frozen, at transitions, blockers, new evidence and closeout.
Run tools without announcing the next command when
the host permits; otherwise emit its shortest useful scope or evidence sentence.
Never repeat the plan, unchanged state or already reported proof. Preserve exact
commands, errors, numbers and negations; expand when brevity risks ambiguity.
Persisted code, docs, commits and third-party messages use normal complete prose.
The checklist views the canonical TODO; accept evidence, not worker reports.
A stale summary never authorizes a successor.
Use a detailed ledger only when at least one condition is true:

- work crosses sessions or must resume safely after context loss;
- dependencies, multiple writers or a delegated queue control readiness;
- a consequential external effect requires auditable gates and recovery;
- the owner explicitly requests a durable execution record.

Otherwise the detailed ledger is unnecessary ceremony; a multi-component task
that still fits one coherent session does not pass this gate. When the gate passes,
use [references/long-run-state.md](references/long-run-state.md) and keep the
owner-facing Progress checklist concise.

## Readiness and method routing

Respect the host instruction hierarchy; explicit user instructions override skill
guidelines. For a skill-caused pause, link its exact `SKILL.md`, quote the clause
and explain applicability; distinguish requirements from interpretation.

Proceed when required inputs, authority and proof are available; unknown write ownership,
stale input or ambiguous irreversible effects block the affected action. Missing optional
goals, telemetry or subagents does not block safe work; use ordinary files or MAIN.

Choose the least complex capable method; route non-trivial implementation through `nobrainer-build`.
When another skill owns a stage, load its canonical body and required references before
planning. Loading method context is not task execution; a routing-table line or remembered summary is insufficient. Load specialists only:

- `nobrainer-research` for decision-relevant external uncertainty;
- `nobrainer-writing` for material user-facing prose;
- `nobrainer-security` for trust boundaries;
- `nobrainer-browser` for rendered behavior or trace evidence;
- `nobrainer-rca` after repeated or causally unclear failure;
- `nobrainer-review` when independent closeout adds material confidence;
- `nobrainer-team` for capability gaps; native subagents for bounded independent work;
  `nobrainer-dispatcher` for a real queue and `nobrainer-sessions` for durable visible sessions.

## `AUTOPILOT`: execute the bounded scope

Read [delivery](references/delivery.md) for non-trivial work and before BLOCKED: derive outcome/DoD, resolve authorized steps and continue independent work. `yolo` is a persistence alias only.

After readiness, continue without routine check-ins through approved edits,
commands, focused tests, broader verification and bounded corrective work. Stop
for a changed frozen input, scope-changing discovery, unrecoverable blocker or
real owner gate.

Autonomy does not expand authority. Merge, deploy, publish, spend, delete,
contact people, change credentials, migrate data, mutate production or weaken
safety controls remain explicit gates unless the owner already authorized that
exact action.

Default to at most two corrective attempts per observed failure, each supported by
new evidence. Then diagnose or report the blocker; do not restart the same loop.
Use a smaller owner-supplied budget. Stop adding work once acceptance passes.
A timeout, partial result, dead session, failed check or exhausted retry is not
completion.

## `VERIFY` and `RECEIVE_AUDIT`

Prove every acceptance item at its actual layer. Static validation, local
runtime, deployed runtime, production behavior, external delivery and user
usefulness are different evidence levels.

Audit native-worker output against its exact returned ID, assigned scope, current
artifact and tests; verify it has stopped writing. Durable sessions use
`nobrainer-sessions` `RECEIVE_AUDIT`. If Dispatcher owns a queue, reconcile the
audited result before releasing dependencies. A finished report is not proof.

Invoke `nobrainer-review` for a justified adversarial or release closeout.
A verified finding returns to `nobrainer-build`; changed work invalidates old
proof and must be re-tested and re-reviewed.
`VERIFY` fails closeout when an affected public surface lacks its update or readback.
## Correction hooks

Apply corrections immediately:

- `OWNER_DECISION_CHANGED`: supersede the old decision, move affected
  not-started `READY` rows to `STOPPED`, block dependants and invalidate
  only their evidence before re-planning.
- `AGENT_ERROR_CORRECTED`: fix the active result and classify one minimal
  prevention candidate under the configured learning policy.
- `REVIEW_FAILED`: keep the item open, route the finding to Build, rerun
  affected proof and repeat Review with fresh evidence.
- `CANDIDATE_REJECTED`: preserve the champion and close that experiment. Continue only
  if owner acceptance is still unmet and a bounded next attempt is justified.
- `REPEATED_DEFECT`: stop blind retries and route the frozen failure to RCA.
Detailed canonical-store rules live in the correction-hooks reference.
## `LEARN` and close

Persist only durable, sourced, authorized and non-secret knowledge.
Use `nobrainer-autoimprove` only with a frozen baseline, calibrated evaluator
outside candidate write scope and a fresh holdout; a null result is valid.
Final: delivered outcome, decisive proof, uncertainty and recovery if needed.
Do not dump internal forms or invent follow-up work after acceptance.
