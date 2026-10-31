---
name: nobrainer-tech-flow
description: "Use when you want to set up, start, resume or complete a coding or non-coding task: scope the outcome, use native workers only where they help, and verify delivery. Aliases: NBFlow, NBF, nobrainer-tech-flow."
---

# nobrainer-tech-flow

Skill: `nobrainer-tech-flow`. `NBFlow` and `NBF` are natural-language
shortcuts; explicit skill loading remains client-dependent.
Use [communication](references/communication.md): plain technical English between agents; natural user-language replies.
Here "the user" owns the task; references call that person the owner and the main agent MAIN.

For non-trivial work read [routing](references/routing.md). Preserve host model/effort;
consult [model routing](references/model-routing.md) when selecting them.
Setup/upgrade/repair uses [setup](references/setup.md); corrections use
[correction hooks](references/correction-hooks.md); gated resumability uses
[long-run state](references/long-run-state.md).
Repository work follows the [task worktree lifecycle](references/worktrees.md).

## Automatic session care

For resumable, long or delegated work with `nobrainer-sessions` installed, run Sessions [startup and health](../nobrainer-sessions/references/session-restart.md#automatic-start-and-observation); otherwise stay in the main agent.
Restart or archive needs separate consent from the user and verified takeover.

## Current instructions

At first use per local calendar day, check the installed Flow version against
the latest stable published release using
[daily update](references/daily-update.md). Inform the user when an update
exists. Apply a verified upgrade within recorded standing authorization;
otherwise prepare the exact upgrade and ask before its consequential writes.
No active client or scheduler means no background daily guarantee.

## Work to done

Read intent from the whole conversation. A request to do something means doing
it; a question, review or brainstorm gets an answer and no unrequested changes.

- Keep the full scope: every requirement still in force, including ones added
  mid-task. Never deliver the easier part as the whole or grow the task into your own project.
- When the next needed step is known and authorized, take it. Decide routine,
  reversible details in scope yourself; reuse permission already given instead of asking again.
- Separate ambiguity from a blocker. Name a safe assumption when it shapes the
  result and continue. Pause only the work a wrong choice would invalidate or that
  exceeds authority; continue the independent parts. Silence is never consent.
- Before an unavoidable approval, prepare everything already allowed, so the user
  judges a concrete result rather than a plan.
- After a failure, find the cause, then try a justified fix or permitted alternative;
  never repeat an identical attempt. A real denial or missing access stays a limit.

## Choose the smallest workflow

### Quick path for small changes

For a clear low-risk answer, rewrite, calculation or one coherent, reversible edit,
deliver and check directly. Chat-only work needs no repository or tools.
For file edits inspect instructions, actual files and the nearest deterministic check;
use checkout, dirty state and `git diff --check` only in a Git repository.
Skip ledger, delegation, review and startup care. Escalate to the full Flow lifecycle
for ambiguity, architecture, public behavior, routing or consequential
side effects; quick path never bypasses an approval gate.

Default to one main-agent loop with skills. Delegate only units that qualify under
[team execution](references/delivery.md#coordinated-team-execution).
The main agent integrates and verifies. Use [Auto Fine Tune](../nobrainer-auto-fine-tune/SKILL.md)
for first-setup capability checks; benchmark only when calibration pays.
Unavailable native workers leave work in the main agent; visible conversations require an explicit user request
or an authorized main-agent restart; isolation, reuse or handoff alone never authorize one.

Lifecycle: `DRIFT_CHECK -> BUDDY -> SCOPE -> AUTOPILOT -> VERIFY -> RECEIVE_AUDIT -> LEARN`.

For resumable or delegated work use `SESSION_HEALTH_GATE` and `RUNTIME_RELEASE`
from the long-run reference.
Finish when accepted; audit active workers. Use `OWNER_DECISION_REQUIRED` only
when unfinished work needs a decision from the user.

## `DRIFT_CHECK`: establish current truth

Inspect the actual inputs, instructions and required capabilities; for project work include dirty state, callers, tests and existing plan/spec. Preserve unrelated work. Prior summaries, wiki and worker reports are context, not proof; query wiki only for a decision or lesson that can change this task.
Research current, external, niche, uncertain, high-stakes or attributed facts. For large documents or data and repositories, inspect structure first. Then read selected contracts in full and the relevant ranges. Respect the context budget and name unread required surface.

At first project use, follow [project start](references/project-start.md) for
the existing tree/layers, goal direction and wiki boundary.

`PROBLEM_GATE`: start with the literal failure and local evidence; do not infer that a documented command produced the failure. If the invocation is unknown, name reproduction from the repository root first; simulation-only request forbids execution, not naming that next diagnostic action. Only then propose path, dependency or configuration changes. Check related wiki decisions. Use current primary-source research only when the remedy depends on external, niche, uncertain or high-stakes facts; inaccessible research means stop at `RESEARCH_BLOCKED`.

## `BUDDY`: clarify once

Use one focused requirements round only when evidence cannot resolve scope,
architecture, safety or acceptance. Code, schema, tests or conventions settle it;
do not make them questions for the user. Ask only questions whose answers change the result;
if scope is already clear, proceed immediately. Establish:

- observable outcome, audience and quality bar;
- target-workflow proof;
- exclusions and consequential side effects;
- actions that need approval from the user;
- unresolved choices that materially affect the design.

Use `nobrainer-decide` for consequential choices.
For ideas, read [idea to delivery](references/idea-to-delivery.md).
Use `nobrainer-spec-driven-development` when requested or architecture, interfaces, migration, rollback, dependencies or resumability justify it.

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
Before substantial work, show the user what done means and set it as the host-native goal where supported.
For substantial work, derive the next short-term goal from the supplied
long-term direction using [project start](references/project-start.md).
Update scope before expanding; require matching files, passing proof and no surprises.
`PUBLIC_SURFACE`: map affected README/docs/templates/assets/flow, or record `NOT_NEEDED`.
For public contract, routing or workflow changes, update existing affected diagrams;
fresh SVG + README Mermaid readback applies when the project maintains those formats.
Do not create diagrams merely to satisfy a workflow gate.
On request, show every field above and the detailed-ledger decision.
For work that passes the detailed-ledger gate, persist the goal in an existing
Markdown tracker or a task-local Markdown `GOAL_FILE`. That file is canonical across clears,
compactions and sessions. Require goal readback only from stores actually
used; the file alone is sufficient and supersedes stale transcript text.
Default to at most 160 words: outcome, scope, Progress, proof and next action.
Do not add a repetitive skill/mode preamble or invent unseen schemas.
Mark uninspected paths/methods as pending.

New dependencies, abstractions, workers, skills and tests need an acceptance reason.
Shared abstractions require two callers or explicit contract.

Use a short plan ordered by outcomes. One canonical TODO owner stays visible: the
host's plan or todo tool, else the Progress checklist.

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
Use a detailed ledger only when any condition holds:

- work crosses sessions or must resume safely after context loss;
- the user keeps adding requests mid-run in one long conversation;
- dependencies, multiple writers or a delegated queue control readiness;
- a consequential external effect requires auditable gates and recovery;
- the user explicitly requests a durable execution record.

Otherwise a multi-component task that fits one coherent session does not pass this gate.
When it passes, use [references/long-run-state.md](references/long-run-state.md) and keep the
user-facing Progress checklist concise.

## Readiness and method routing

Respect the host instruction hierarchy; explicit user instructions override skill
guidelines. For a skill-caused pause, link its exact `SKILL.md`, quote the clause
and explain applicability; distinguish requirements from interpretation.

Proceed when required inputs, authority and proof are available; unknown write ownership,
stale input or ambiguous irreversible effects block the affected action. Missing optional
goals, telemetry or subagents does not block safe work; use ordinary files or the main agent.

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
  `nobrainer-dispatcher` for a real queue and `nobrainer-sessions` for durable visible sessions;
- `nobrainer-auto-fine-tune` at first setup for capability discovery and a
  scoped personalization proposal.

## `AUTOPILOT`: execute the bounded scope

Read [delivery](references/delivery.md) for non-trivial work and before BLOCKED: derive outcome/DoD, resolve authorized steps and continue independent work. `yolo` is a persistence alias only.

Approved plans and autopilot use the
[approved-plan loop](references/autopilot.md); completion requires whole-goal proof.

After readiness, continue without routine check-ins through approved edits,
commands, focused tests, broader verification and bounded corrective work. Stop
for a changed frozen input, scope-changing discovery, unrecoverable blocker or
real approval gate.

Autonomy does not expand authority. Merge, deploy, publish, spend, delete,
contact people, change credentials, migrate data, mutate production or weaken
safety controls remain explicit gates unless the user already authorized that
exact action.

Corrective-attempt budget (also Build and RCA): two attempts per observed failure,
each with new evidence, or the user's smaller budget; then diagnose or report the blocker.
Timeouts, partial results, dead sessions, failed checks and exhausted retries never prove completion.

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
Before done, list each place the task touched where docs and code disagree; agents follow stale docs.
## Correction hooks

Apply corrections immediately:

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
Detailed canonical-store rules live in the correction-hooks reference.
## `LEARN` and close

Persist only durable, sourced, authorized and non-secret knowledge.
Use `nobrainer-autoimprove` only with a frozen baseline, calibrated evaluator
outside candidate write scope and a fresh holdout; a null result is valid.

Finish check: compare the result with the whole agreed scope. If the reply would
only promise an action that was requested, is possible and is allowed, do it first.
Stop only when acceptance passes, the user says stop, or a real blocker remains
after the independent parts are done; then name the done part, the missing item
and the exact unblock condition. Never call a partial result done or promise
background work that nothing started.
End every non-trivial task with this handoff block. Keep all three headings, even when empty.
```text
Delivered: <the observable outcome>
Checked: <command or check> -> <observed result>
Not checked: <item> - <reason>, or None
```
A listed gap means done with gaps, not done: the MCP `DONE_WITH_GAPS` verdict.
Add recovery or a user decision only when one exists. Do not dump internal forms or invent follow-up work.
